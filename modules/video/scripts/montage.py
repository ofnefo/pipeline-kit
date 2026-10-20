"""Montage CLI (CPU / FFmpeg + libass only): ported from the per-project `_shared` scripts.

Commands (all paths are project-owned; every run writes a new versioned folder with manifest.json + renders.jsonl):
  mv-edit         EDIT.json -> master (cover-crop clips, xfades, punch-in zoom, ASS burn-in, stem mix, two-pass loudnorm)
  mv-captions     SPEC.json -> ASS word-pop captions, animated lower third, callouts and title cards
  ass-pin         pin bottom captions inside a time window to a fixed position (new ASS, source untouched)
  mv-compile      SPEC.json -> comparison reel: title cards + labelled tile grids (A/B, variants)
  audio-mix       MIX.json -> role-based stem mix with sidechain ducking and an optional loudness preset
  loudnorm        two-pass loudness normalisation of a video (video stream copied) or audio file to a preset
  kinetic-titles  SPEC.json -> animated title cards (ASS/libass) over a colour or a project video
Sources and masters are never overwritten. See docs/MONTAGE_CLI.md.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sys
from pathlib import Path

import editorial as ed
import montage_audio as ma
import video_pipeline as vp

VIDEO_SUFFIXES = (".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


# ---------------------------------------------------------------- shared helpers
def ffmpeg() -> Path:
    binary = vp.find_binary("ffmpeg")
    if not binary:
        raise FileNotFoundError("ffmpeg is not available")
    return binary


def number(value, name: str, low: float, high: float, *, low_open: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a number")
    if value > high or value < low or (low_open and value == low):
        raise ValueError(f"{name} must be within {'(' if low_open else '['}{low:g}, {high:g}]")
    return float(value)


def canvas(spec: dict, default=(1920, 1080)) -> tuple[int, int]:
    size = spec.get("size", list(default))
    if (not isinstance(size, list) or len(size) != 2 or any(type(v) is not int for v in size)
            or not all(16 <= v <= 8192 and v % 2 == 0 for v in size)):
        raise ValueError("size must be [even width, even height] within 16..8192")
    return size[0], size[1]


def rate(spec: dict, default=48) -> int:
    fps = spec.get("fps", default)
    if type(fps) is not int or not 1 <= fps <= 240:
        raise ValueError("fps must be an integer 1..240")
    return fps


def load_spec(project: Path, value: str) -> tuple[Path, dict]:
    path = ed.owned(project, value)
    spec = ed.read_json(path)
    if not isinstance(spec, dict):
        raise ValueError("Spec must be a JSON object")
    return path, spec


def owned_dir(project: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    path = (path if path.is_absolute() else project / path).resolve()
    if not path.is_relative_to(project.resolve()) or not path.is_dir():
        raise ValueError(f"Expected an existing directory inside project: {value}")
    return path


def inside(project: Path, value: str) -> Path:
    """Resolve a project path that may be missing (compile tiles); escaping the project is an error."""
    path = Path(value).expanduser()
    path = (path if path.is_absolute() else project / path).resolve()
    if not path.is_relative_to(project.resolve()):
        raise ValueError(f"Path escapes the project: {value}")
    return path


def safe_stem(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", path.stem).strip("-.") or "output"


def inputs_record(project: Path, paths) -> list[dict]:
    seen, out = set(), []
    for path in paths:
        if path not in seen:
            seen.add(path)
            out.append({"path": ed.rel(project, path), "sha256": vp.sha256(path)})
    return out


def duration(path: Path) -> float:
    return float(vp.probe(path)["format"]["duration"])


def has_audio(path: Path) -> bool:
    return any(s["codec_type"] == "audio" for s in vp.probe(path)["streams"])


def fontsdir_option(folder: Path, fonts: Path | None) -> str:
    if not fonts:
        return ""
    try:
        return ":fontsdir=" + os.path.relpath(fonts, folder).replace(os.sep, "/")
    except ValueError:  # other drive
        return ":fontsdir='" + str(fonts).replace(os.sep, "/").replace(":", "\\:") + "'"


def loudness_target(value) -> dict | None:
    """'social' | 'broadcast' | 'none' | {"I","TP","LRA"[,"tolerance"]} (the _shared edit.py form)."""
    if value in (None, "none"):
        return None
    if isinstance(value, str):
        return ma.preset(value)
    if isinstance(value, dict):
        target = {"name": "custom", "I": number(value.get("I"), "loudness.I", -40, -5),
                  "TP": number(value.get("TP", -1.0), "loudness.TP", -9, 0),
                  "LRA": number(value.get("LRA", 11.0), "loudness.LRA", 1, 50)}
        target["tolerance"] = number(value.get("tolerance", 1.0), "loudness.tolerance", 0, 5, low_open=True)
        return target
    raise ValueError("loudness must be a preset name, 'none' or an object")


def audio_tracks(project: Path, spec_tracks) -> tuple[list[dict], list[Path]]:
    if not isinstance(spec_tracks, list):
        raise ValueError("audio must be a list of tracks")
    tracks, paths = [], []
    for track in spec_tracks:
        path = ed.owned(project, track["src"])
        if not has_audio(path):
            raise ValueError(f"Audio track has no audio stream: {track['src']}")
        for key in ("start", "in", "fade_in", "fade_out"):
            number(track.get(key, 0), f"audio.{key}", 0, 86400)
        if track.get("dur") is not None:
            number(track["dur"], "audio.dur", 0, 86400, low_open=True)
        tracks.append({**track, "src": path})
        paths.append(path)
    return tracks, paths


def mix_and_normalize(project: Path, folder: Path, tracks: list[dict], total: float, duck, target) -> dict:
    """Mix stems into folder/mix.wav, then (optionally) two-pass loudnorm into folder/mix-<preset>.wav."""
    ff = ffmpeg()
    if duck is not None and not isinstance(duck, dict):
        raise ValueError("duck must be an object {key, target, threshold, ratio, attack, release}")
    filters, label = ma.mix_graph(tracks, total, duck, duration_of=duration)
    (folder / "mix-graph.txt").write_text(";\n".join(filters), encoding="utf-8")
    mixed = folder / "mix.wav"
    command = [ff, "-hide_banner", "-nostdin", "-n", *[x for t in tracks for x in ("-i", t["src"])],
               "-filter_complex_script", "mix-graph.txt", "-map", f"[{label}]", "-c:a", "pcm_s24le", "mix.wav"]
    ma.run(command, cwd=folder)
    result = {"mix": str(mixed), "mix_command": [str(x) for x in command], "duck": duck}
    if target is None:
        result.update(final_audio=mixed, loudness=None, loudness_errors=[])
        return result
    normalized = folder / f"mix-{target['name']}.wav"
    passes = ma.two_pass(ff, mixed, normalized, target, video=False)
    errors = ma.check(passes["after"], target)
    result.update(final_audio=normalized, loudness_errors=errors, loudness={
        "target": target, "before": {k: v for k, v in passes["before"].items() if k != "raw"},
        "after": {k: v for k, v in passes["after"].items() if k != "raw"}, "pass": not errors,
        "mode": passes["mode"], "command": passes["command"]})
    return result


# ---------------------------------------------------------------- mv-edit
def edit_video_graph(clips: list[dict], width: int, height: int, fps: int) -> tuple[list, list[str], str, float]:
    args, graph = [], []
    for i, c in enumerate(clips):
        speed, zoom = c["speed"], c["zoom"]
        args += ["-ss", f"{c['in']:g}", "-t", f"{c['dur'] * speed + 0.05:g}", "-i", c["src"]]
        punch = (f",crop=iw/{zoom:g}:ih/{zoom:g}:(iw-iw/{zoom:g})/2:(ih-ih/{zoom:g})*{c['zoom_y']:g},"
                 f"scale={width}:{height}:flags=lanczos" if zoom != 1.0 else "")
        graph.append(f"[{i}:v]setpts=(PTS-STARTPTS)/{speed:g},fps={fps},scale={width}:{height}:"
                     f"force_original_aspect_ratio=increase:flags=lanczos,crop={width}:{height}{punch},setsar=1,format=yuv420p,"
                     f"tpad=stop_mode=clone:stop_duration=1,trim=duration={c['dur']:g},setpts=PTS-STARTPTS,settb=1/{fps}[c{i}]")
    current, total = "c0", clips[0]["dur"]
    for i in range(1, len(clips)):
        x = clips[i - 1]["xfade"]
        if x > 0:
            graph.append(f"[{current}][c{i}]xfade=transition=fade:duration={x:g}:offset={total - x:.4f}[x{i}]")
            total += clips[i]["dur"] - x
        else:  # concat resets the timebase; xfade needs both inputs equal
            graph.append(f"[{current}][c{i}]concat=n=2:v=1:a=0,settb=1/{fps}[x{i}]")
            total += clips[i]["dur"]
        current = f"x{i}"
    return args, graph, current, total


def checked_clips(project: Path, raw) -> list[dict]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("clips must be a nonempty list")
    clips = []
    for k, c in enumerate(raw):
        path = ed.owned(project, c["src"])
        clip = {"src": path, "label": str(c.get("label", "")),
                "in": number(c.get("in", 0), "clip.in", 0, 86400),
                "dur": number(c.get("dur"), "clip.dur", 0, 3600, low_open=True),
                "speed": number(c.get("speed", 1.0), "clip.speed", 0, 8, low_open=True),
                "zoom": number(c.get("zoom", 1.0), "clip.zoom", 1, 8),
                "zoom_y": number(c.get("zoom_y", 0.5), "clip.zoom_y", 0, 1),
                "xfade": number(c.get("xfade", 0) or 0, "clip.xfade", 0, 10)}
        clips.append(clip)
    for a, b in zip(clips, clips[1:]):
        if a["xfade"] and a["xfade"] >= min(a["dur"], b["dur"]):
            raise ValueError("xfade must be shorter than both neighbouring clips")
    if clips[-1]["xfade"]:
        raise ValueError("The last clip cannot dissolve into a next clip")
    return clips


def mv_edit(args: argparse.Namespace) -> dict:
    project = vp.checked_project(args.project)
    edit_path, spec = load_spec(project, args.edit)
    width, height = canvas(spec, (3840, 2160))
    fps = rate(spec)
    crf = spec.get("crf", 16)
    if type(crf) is not int or not 0 <= crf <= 51:
        raise ValueError("crf must be an integer 0..51")
    if args.preview:
        width, height, crf = 960, 540, 23
    clips = checked_clips(project, spec.get("clips"))
    ass = ed.owned(project, spec["ass"]) if spec.get("ass") else None
    fonts = owned_dir(project, args.fonts_dir or spec.get("fonts_dir"))
    tracks, audio_paths = audio_tracks(project, spec.get("audio", []))
    target = loudness_target(args.loudness if args.loudness else spec.get("loudness", "social"))
    folder = ed.output_folder(project, "50-edit" if args.preview else "80-master",
                              "mv-edit-preview" if args.preview else "mv-edit")
    vargs, graph, current, total = edit_video_graph(clips, width, height, fps)
    if ass:
        shutil.copyfile(ass, folder / "captions.ass")
        graph.append(f"[{current}]ass=captions.ass{fontsdir_option(folder, fonts)}[vout]")
        current = "vout"
    audio = mix_and_normalize(project, folder, tracks, total, spec.get("duck"), target) if tracks else None
    (folder / "video-graph.txt").write_text(";\n".join(graph), encoding="utf-8")
    output = folder / f"{safe_stem(edit_path)}{'-preview' if args.preview else ''}.mp4"
    command = [ffmpeg(), "-hide_banner", "-nostdin", "-n", *vargs]
    if audio:
        command += ["-i", audio["final_audio"]]
    command += ["-filter_complex_script", "video-graph.txt", "-map", f"[{current}]"]
    command += ["-map", f"{len(clips)}:a", "-c:a", "aac", "-b:a", "320k"] if audio else ["-an"]
    command += ["-c:v", "libx264", "-preset", "veryfast" if args.preview else "slow", "-crf", str(crf), "-profile:v", "high",
                "-pix_fmt", "yuv420p", "-r", str(fps), "-t", f"{total:.3f}", "-movflags", "+faststart", output.name]
    ma.run(command, cwd=folder)
    actual = duration(output)
    errors = [] if abs(actual - total) <= 2 / fps + 0.05 else [f"Duration {actual:.3f}s != planned {total:.3f}s"]
    if audio:
        errors += audio["loudness_errors"]
    payload = {"video": str(output), "edit": ed.rel(project, edit_path), "edit_sha256": vp.sha256(edit_path),
               "preview": bool(args.preview), "size": [width, height], "fps": fps, "duration_planned": round(total, 3),
               "duration_actual": round(actual, 3), "inputs": inputs_record(project, [c["src"] for c in clips] + audio_paths
                                                                             + ([ass] if ass else [])),
               "fonts_dir": ed.rel(project, fonts) if fonts else None, "errors": errors,
               "audio": None if not audio else {"mix": audio["mix"], "final": str(audio["final_audio"]), "duck": audio["duck"],
                                                "loudness": audio["loudness"]},
               "command": [str(x) for x in command]}
    result = ed.register(project, folder, "mv-edit", payload)
    result["ok"] = not errors
    return result


# ---------------------------------------------------------------- mv-captions
YEL, WHITE, BLACK, DARK = "&H001ED2FF", "&H00FFFFFF", "&H00000000", "&H00141414"  # &HAABBGGRR
CAPTION_FONTS = {"black": "Gilroy Black", "bold": "Gilroy Bold", "regular": "Gilroy"}


def ts(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def ass_text(text: str) -> str:
    return str(text).replace("{", "(").replace("}", ")").replace("\r", "").replace("\n", "\\N")


def ass_head(width: int, height: int, styles: list[str]) -> str:
    return ("[Script Info]\nScriptType: v4.00+\n"
            f"PlayResX: {width}\nPlayResY: {height}\nWrapStyle: 2\nScaledBorderAndShadow: yes\nYCbCr Matrix: TV.709\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
            "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
            "MarginR, MarginV, Encoding\n" + "\n".join(styles) + "\n\n[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")


def caption_styles(f: dict) -> list[str]:
    return [f"Style: Cap,{f['black']},84,{WHITE},{WHITE},{BLACK},&H64000000,0,0,0,0,100,100,1,0,1,7,3,2,80,80,250,1",
            f"Style: LTTitle,{f['bold']},56,{WHITE},{WHITE},{BLACK},&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1",
            f"Style: LTTag,{f['black']},30,{BLACK},{BLACK},{BLACK},&H00000000,0,0,0,0,100,100,2,0,1,0,0,7,0,0,0,1",
            f"Style: Box,{f['regular']},10,{DARK},{DARK},{DARK},&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1",
            f"Style: Call,{f['black']},72,{WHITE},{WHITE},&H30141414,&H00000000,0,0,0,0,100,100,0,0,3,16,0,8,80,80,0,1",
            f"Style: Card,{f['black']},120,{WHITE},{WHITE},{BLACK},&H80000000,0,0,0,0,100,100,2,0,1,8,5,5,80,80,0,1",
            f"Style: CardSub,{f['bold']},46,{WHITE},{WHITE},{BLACK},&H80000000,0,0,0,0,100,100,1,0,1,4,3,5,80,80,0,1"]


def ev(layer: int, a: float, b: float, style: str, text: str) -> str:
    return f"Dialogue: {layer},{ts(a)},{ts(b)},{style},,0,0,0,,{text}"


def rect(w: int, h: int) -> str:
    return f"m 0 0 l {w} 0 l {w} {h} l 0 {h}"


def lower_third(lt: dict) -> list[str]:
    s, d = number(lt["start"], "lower_third.start", 0, 86400), number(lt["dur"], "lower_third.dur", 0.5, 600)
    e, title, tag = s + d, ass_text(lt["title"]), ass_text(lt.get("tag", ""))
    x, y, bh = 96, 840, 104
    tw = int(len(title) * 30.5 + 90)  # bold 56 px ~ 30 px per character
    ms = int(d * 1000)
    out = [ev(4, s, e, "Box", f"{{\\an7\\pos({x},{y})\\p1\\1c{YEL}\\org({x},{y + bh})\\fscy0\\t(0,220,\\fscy100)"
                              f"\\t({ms - 260},{ms},\\fscy0)}}{rect(14, bh)}")]
    full, zero = f"{x + 14},{y},{x + 14 + tw},{y + bh}", f"{x + 14},{y},{x + 14},{y + bh}"
    out.append(ev(3, s, e, "Box", f"{{\\an7\\pos({x + 14},{y})\\p1\\1c{DARK}\\1a&H18&\\clip({zero})\\t(120,520,0.6,\\clip({full}))"
                                  f"\\t({ms - 420},{ms - 120},\\clip({zero}))}}{rect(tw, bh)}"))
    out.append(ev(5, s + 0.28, e - 0.15, "LTTitle", f"{{\\an4\\move({x + 16},{y + bh // 2},{x + 54},{y + bh // 2},0,320)"
                                                    f"\\fad(220,180)\\bord0}}{title}"))
    if tag:
        pw = int(len(tag) * 21 + 44)
        out.append(ev(5, s + 0.42, e - 0.2, "Box", f"{{\\an1\\pos({x + 14},{y - 10})\\p1\\1c{YEL}\\org({x + 14},{y - 10})"
                                                   f"\\fscx60\\fscy60\\t(0,140,\\fscx108\\fscy108)\\t(140,240,\\fscx100\\fscy100)"
                                                   f"\\fad(80,160)}}{rect(pw, 50)}"))
        out.append(ev(6, s + 0.42, e - 0.2, "LTTag", f"{{\\an4\\pos({x + 36},{y - 35})\\fad(120,160)}}{tag}"))
    return out


def word_caps(words: list[dict], a: float, b: float | None, upper: bool, skip=()) -> list[str]:
    words = [w for w in words if w["s"] >= a - 0.01 and (b is None or w["e"] <= b + 0.01)
             and not any(x0 - 0.05 <= w["s"] < x1 for x0, x1 in skip)]
    chunks, cur = [], []
    for w in words:  # 2-3 words per chunk; break on punctuation, long gaps or > 16 characters
        if cur and (len(cur) >= 3 or w["s"] - cur[-1]["e"] > 0.35 or sum(len(x["w"]) for x in cur) + len(w["w"]) > 16):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if w["w"].rstrip()[-1:] in ".?!,:\u2014":
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    out = []
    for chunk in chunks:
        for i, w in enumerate(chunk):
            t0, t1 = w["s"], chunk[i + 1]["s"] if i + 1 < len(chunk) else w["e"] + 0.12
            parts = []
            for j, x in enumerate(chunk):
                text = ass_text(x["w"].strip().strip(".,?!:;\u00ab\u00bb\"\u2014"))
                text = text.upper() if upper else text
                parts.append(f"{{\\1c{YEL}\\fscx118\\fscy118\\t(0,110,\\fscx100\\fscy100)}}{text}{{\\1c{WHITE}}}" if j == i else text)
            out.append(ev(2, t0, t1, "Cap", f"{{\\an2{chr(92) + 'fad(60,0)' if i == 0 else ''}}}" + " ".join(parts)))
    return out


def callout(c: dict, width: int) -> list[str]:
    s = number(c["start"], "callout.start", 0, 86400)
    e = s + number(c["dur"], "callout.dur", 0.1, 600)
    out = []
    for k, line in enumerate(c["lines"]):
        out.append(ev(7, s + 0.25 * k, e, "Call", f"{{\\an8\\pos({width // 2},{110 + k * 118})\\1c{YEL if k else WHITE}"
                                                  f"\\fscx70\\fscy70\\alpha&HFF&\\t(0,160,\\fscx106\\fscy106\\alpha&H00&)"
                                                  f"\\t(160,260,\\fscx100\\fscy100)\\fad(0,200)}}{ass_text(line)}"))
    return out


def card(c: dict, width: int, height: int) -> list[str]:
    s = number(c["start"], "card.start", 0, 86400)
    e = s + number(c["dur"], "card.dur", 0.1, 600)
    out = [ev(8, s, e, "Card", f"{{\\an5\\pos({width // 2},{height // 2 - 40})\\fscx80\\fscy80\\t(0,300,0.5,\\fscx100\\fscy100)"
                               f"\\fad(250,300)}}{ass_text(c['title'])}")]
    if c.get("sub"):
        out.append(ev(8, s + 0.3, e, "CardSub", f"{{\\an5\\pos({width // 2},{height // 2 + 60})\\fad(250,300)}}{ass_text(c['sub'])}"))
    return out


def mv_captions(args: argparse.Namespace) -> dict:
    project = vp.checked_project(args.project)
    spec_path, spec = load_spec(project, args.spec)
    width, height = 1920, 1080  # libass scales PlayRes to any render canvas
    fonts = {**CAPTION_FONTS, **(spec.get("fonts") or {})}
    lines, used = [], []
    if spec.get("lower_third"):
        lines += lower_third(spec["lower_third"])
    if spec.get("words"):
        words_path = ed.owned(project, spec["words"])
        used.append(words_path)
        words = ed.read_json(words_path)
        if not isinstance(words, list) or not all(isinstance(w, dict) and {"w", "s", "e"} <= set(w) for w in words):
            raise ValueError("words must be a JSON list of {w, s, e}")
        skip = ([(c["start"], c["start"] + c["dur"]) for c in spec.get("callouts", [])]
                if spec.get("hide_caps_under_callouts", True) else [])
        lines += word_caps(words, spec.get("captions_from", 0), spec.get("captions_until"), spec.get("upper", True), skip)
    for c in spec.get("callouts", []):
        lines += callout(c, width)
    for c in spec.get("cards", []):
        lines += card(c, width, height)
    if not lines:
        raise ValueError("Spec produced no events (words, lower_third, callouts or cards required)")
    folder = ed.output_folder(project, "60-motion", "captions")
    output = folder / "captions.ass"
    with output.open("x", encoding="utf-8-sig", newline="\n") as stream:
        stream.write(ass_head(width, height, caption_styles(fonts)) + "\n".join(lines) + "\n")
    return ed.register(project, folder, "mv-captions", {
        "ass": str(output), "events": len(lines), "fonts": fonts, "spec": ed.rel(project, spec_path),
        "inputs": inputs_record(project, [spec_path, *used])})


# ---------------------------------------------------------------- ass-pin
def ass_pin(args: argparse.Namespace) -> dict:
    project = vp.checked_project(args.project)
    source = ed.owned(project, args.input)
    if source.suffix.lower() != ".ass":
        raise ValueError("Input must be an .ass file")
    start, end = number(args.start, "--from", 0, 86400), number(args.end, "--to", 0, 86400)
    if end <= start:
        raise ValueError("--to must be after --from")
    pattern = re.compile(rf"Dialogue: {args.layer},(\d+):(\d\d):(\d\d\.\d\d),")
    tag = "{\\" + args.align
    out, pinned = [], 0
    for line in source.read_bytes().decode("utf-8-sig").splitlines(keepends=True):
        m = pattern.match(line)
        if m and start <= int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) < end and tag in line:
            line = line.replace(tag, f"{tag}\\pos({args.x},{args.y})", 1)
            pinned += 1
        out.append(line)
    folder = ed.output_folder(project, "60-motion", "ass-pin")
    output = folder / f"{safe_stem(source)}-pinned.ass"
    with output.open("xb") as stream:
        stream.write(("\ufeff" + "".join(out)).encode("utf-8"))
    return ed.register(project, folder, "ass-pin", {
        "ass": str(output), "pinned_events": pinned, "window": [start, end], "pos": [args.x, args.y],
        "layer": args.layer, "align": args.align, "inputs": inputs_record(project, [source])})


# ---------------------------------------------------------------- mv-compile
def esc(text: str) -> str:
    return (str(text).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\u2019")
            .replace("%", "\\%").replace(",", "\\,"))


def ff_font(path: Path) -> str:
    return str(path).replace("\\", "/").replace(":", "\\:")


def compile_fonts(project: Path, fonts_dir: Path | None, spec: dict) -> tuple[Path, Path]:
    names = {"bold": "Gilroy-Bold.ttf", "black": "Gilroy-Black.ttf", **(spec.get("fonts") or {})}
    if fonts_dir:
        bold, black = fonts_dir / names["bold"], fonts_dir / names["black"]
        if not (bold.is_file() and black.is_file()):
            raise ValueError(f"Fonts {names['bold']} / {names['black']} missing in {fonts_dir}")
        return bold, black
    system = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    bold = system / "arialbd.ttf"
    if not bold.is_file():
        raise FileNotFoundError("No --fonts-dir given and Windows Arial Bold is missing")
    black = system / "ariblk.ttf"
    return bold, black if black.is_file() else bold


def render_segment(project: Path, seg: dict, width: int, height: int, fps: int, path: Path,
                   bold: Path, black: Path) -> tuple[list[Path] | None, list[str], str | None]:
    fb, fk = ff_font(bold), ff_font(black)
    d = number(seg.get("dur", 3.0), "segment.dur", 0.3, 600, low_open=True)
    ff = ffmpeg()
    note = None
    if "card" in seg:
        vf = (f"drawtext=fontfile='{fk}':text='{esc(seg['card'])}':fontcolor=white:fontsize={height // 12}:"
              f"x=(w-tw)/2:y=(h-th)/2-{height // 20},drawbox=x=(iw-{width // 6})/2:y=ih/2+{height // 40}:w={width // 6}:"
              f"h={max(4, height // 180)}:color=0xFFD21E:t=fill")
        if seg.get("sub"):
            vf += (f",drawtext=fontfile='{fb}':text='{esc(seg['sub'])}':fontcolor=0xDDDDDD:fontsize={height // 30}:"
                   f"x=(w-tw)/2:y=h/2+{height // 14}")
        vf += f",fade=t=in:d=0.25,fade=t=out:st={d - 0.25:g}:d=0.25"
        command = [ff, "-hide_banner", "-nostdin", "-n", "-f", "lavfi", "-i", f"color=c=0x101010:s={width}x{height}:r={fps}:d={d:g}",
                   "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-vf", vf, "-t", f"{d:g}", "-shortest"]
        used, missing = [], []
    else:
        resolved = [(t[0], inside(project, t[1]), t[2] if len(t) > 2 else 0) for t in seg["tiles"]]
        missing = [ed.rel(project, p) for _, p, _ in resolved if not p.is_file()]
        tiles = [t for t in resolved if t[1].is_file()]
        if not tiles:
            return None, missing, None
        n = len(tiles)
        cols = min(n, int(seg.get("cols", 2 if n <= 4 else 3)))
        rows = -(-n // cols)
        title_h = height // 14 if seg.get("title") else 0
        cw, ch = width // cols // 2 * 2, (height - title_h) // rows // 2 * 2
        zoom = number(seg.get("zoom", 1.0), "segment.zoom", 1, 8)
        zx, zy = seg.get("zoom_xy", [0.5, 0.5])
        inputs, graph = [], []
        for i, (label, tile, start) in enumerate(tiles):
            if tile.suffix.lower() in IMAGE_SUFFIXES:
                inputs += ["-loop", "1", "-t", f"{d + 0.1:g}", "-i", tile]
            else:
                inputs += ["-ss", f"{float(start):g}", "-t", f"{d + 0.1:g}", "-i", tile]
            crop = f"crop=iw/{zoom:g}:ih/{zoom:g}:(iw-iw/{zoom:g})*{zx}:(ih-ih/{zoom:g})*{zy}," if zoom != 1.0 else ""
            fit = (f"scale={cw}:{ch}:force_original_aspect_ratio=decrease:flags=lanczos,pad={cw}:{ch}:(ow-iw)/2:(oh-ih)/2:color=0x101010"
                   if seg.get("fit") == "contain" else
                   f"scale={cw}:{ch}:force_original_aspect_ratio=increase:flags=lanczos,crop={cw}:{ch}")
            text = (f"drawtext=fontfile='{fb}':text='{esc(label)}':fontcolor=0xFFD21E:fontsize={max(16, min(ch // 14, cw // 24))}:"
                    f"x=14:y=10:box=1:boxcolor=0x000000AA:boxborderw=8," if label else "")
            graph.append(f"[{i}:v]{crop}{fit},setsar=1,fps={fps},tpad=stop_mode=clone:stop_duration={d:g},trim=duration={d:g},"
                         f"setpts=PTS-STARTPTS,{text}format=yuv420p[t{i}]")
        layout = "|".join(f"{(i % cols) * cw}_{(i // cols) * ch + title_h}" for i in range(n))
        graph.append(f"color=c=0x101010:s={width}x{height}:r={fps}:d={d:g}[bg]")
        graph.append("".join(f"[t{i}]" for i in range(n)) + f"xstack=inputs={n}:layout={layout}:fill=0x101010[xs]"
                     if n > 1 else "[t0]copy[xs]")
        oy = 0 if n > 1 else title_h
        graph.append(f"[bg][xs]overlay=0:{oy}:shortest=1" + (
            f",drawtext=fontfile='{fk}':text='{esc(seg['title'])}':fontcolor=white:fontsize={title_h * 6 // 10}:x=24:y={title_h // 5}"
            if seg.get("title") else "") + "[v]")
        source = seg.get("audio_from")
        if source is not None and type(source) is int and 0 <= source < n and has_audio(tiles[source][1]):
            graph.append(f"[{source}:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={d:g}[a]")
            audio_map = "[a]"
        else:
            if source is not None:
                note = f"audio_from {source} has no usable audio; segment is silent"
            inputs += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
            audio_map = f"{n}:a"
        command = [ff, "-hide_banner", "-nostdin", "-n", *inputs, "-filter_complex", ";".join(graph),
                   "-map", "[v]", "-map", audio_map, "-t", f"{d:g}"]
        used = [t[1] for t in tiles]
    command += ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(fps),
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", path]
    ma.run(command)
    return used, missing, note


def mv_compile(args: argparse.Namespace) -> dict:
    project = vp.checked_project(args.project)
    spec_path, spec = load_spec(project, args.spec)
    width, height = canvas(spec)
    fps = rate(spec)
    crf = spec.get("crf", 20)
    if type(crf) is not int or not 0 <= crf <= 51:
        raise ValueError("crf must be an integer 0..51")
    segments = spec.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("segments must be a nonempty list")
    bold, black = compile_fonts(project, owned_dir(project, args.fonts_dir or spec.get("fonts_dir")), spec)
    folder = ed.output_folder(project, "50-edit", "compile")
    parts_dir = folder / "segments"
    parts_dir.mkdir()
    parts, used, missing, toc, notes, t = [], [], [], [], [], 0.0
    for k, seg in enumerate(segments):
        part = parts_dir / f"{k:03d}.mp4"
        u, miss, note = render_segment(project, seg, width, height, fps, part, bold, black)
        missing += miss
        if note:
            notes.append(f"segment {k}: {note}")
        if u is None:
            continue
        used += u
        parts.append(part)
        toc.append({"t": round(t, 2), "title": seg.get("card") or seg.get("title")})
        t += float(seg.get("dur", 3.0))
    if not parts:
        raise ValueError("No segment could be rendered (all tiles missing)")
    listing = parts_dir / "list.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    output = folder / f"{safe_stem(spec_path)}.mp4"
    command = [ffmpeg(), "-hide_banner", "-nostdin", "-n", "-f", "concat", "-safe", "0", "-i", listing,
               "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
               "-movflags", "+faststart", output]
    ma.run(command)
    return ed.register(project, folder, "mv-compile", {
        "video": str(output), "duration": round(t, 2), "size_mib": round(output.stat().st_size / 2 ** 20, 2), "toc": toc,
        "spec": ed.rel(project, spec_path), "inputs": inputs_record(project, [spec_path, *used]), "missing": missing,
        "notes": notes, "fonts": [str(bold), str(black)], "command": [str(x) for x in command]})


# ---------------------------------------------------------------- audio-mix / loudnorm
def audio_mix(args: argparse.Namespace) -> dict:
    project = vp.checked_project(args.project)
    spec_path, spec = load_spec(project, args.spec)
    tracks, paths = audio_tracks(project, spec.get("tracks"))
    if not tracks:
        raise ValueError("tracks must be a nonempty list")
    total = spec.get("duration")
    if total is None:
        total = max(float(t.get("start", 0)) + (float(t["dur"]) if t.get("dur") else duration(t["src"]) - float(t.get("in", 0)))
                    for t in tracks)
    total = number(total, "duration", 0, 86400, low_open=True)
    target = loudness_target(args.preset if args.preset else spec.get("loudness", "social"))
    folder = ed.output_folder(project, "70-color-sound", "audio-mix")
    audio = mix_and_normalize(project, folder, tracks, total, spec.get("duck"), target)
    errors = audio["loudness_errors"]
    result = ed.register(project, folder, "audio-mix", {
        "audio": str(audio["final_audio"]), "mix": audio["mix"], "duration": round(total, 3), "duck": audio["duck"],
        "loudness": audio["loudness"], "errors": errors, "spec": ed.rel(project, spec_path),
        "inputs": inputs_record(project, [spec_path, *paths]), "command": audio["mix_command"]})
    result["ok"] = not errors
    return result


def loudnorm(args: argparse.Namespace) -> dict:
    project = vp.checked_project(args.project)
    source = ed.owned(project, args.input)
    target = ma.preset(args.preset)
    info = vp.probe(source)
    streams = {s["codec_type"] for s in info["streams"]}
    if "audio" not in streams:
        raise ValueError("Input has no audio stream")
    video = "video" in streams and source.suffix.lower() in VIDEO_SUFFIXES
    folder = ed.output_folder(project, "80-master" if video else "70-color-sound", "loudnorm")
    output = folder / f"{safe_stem(source)}-{target['name']}{'.mp4' if video else '.wav'}"
    passes = ma.two_pass(ffmpeg(), source, output, target, video=video)
    errors = ma.check(passes["after"], target, args.tolerance)
    result = ed.register(project, folder, "loudnorm", {
        "normalized": str(output), "preset": target["name"], "target": target,
        "before": {k: v for k, v in passes["before"].items() if k != "raw"},
        "after": {k: v for k, v in passes["after"].items() if k != "raw"}, "pass": not errors, "errors": errors,
        "mode": passes["mode"], "video_stream": "copied" if video else None, "inputs": inputs_record(project, [source]),
        "command": passes["command"]})
    result["ok"] = not errors
    return result


# ---------------------------------------------------------------- kinetic-titles
def ass_colour(value: str, default: str = "&H00FFFFFF") -> str:
    if not value:
        return default
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", value)
    if not m:
        raise ValueError(f"Colour must be #RRGGBB: {value}")
    r, g, b = m[1][0:2], m[1][2:4], m[1][4:6]
    return f"&H00{b}{g}{r}".upper()


ENTER = ("pop", "rise", "fade", "slide")


def title_event(t: dict, width: int, height: int) -> str:
    start = number(t["start"], "title.start", 0, 86400)
    dur = number(t["dur"], "title.dur", 0.2, 600)
    enter = t.get("enter", "pop")
    if enter not in ENTER:
        raise ValueError(f"enter must be one of {', '.join(ENTER)}")
    x, y = t.get("pos", [width // 2, height // 2])
    x, y = int(number(x, "title.x", 0, width)), int(number(y, "title.y", 0, height))
    tags = "\\an5"
    if enter == "rise":
        tags += f"\\move({x},{y + height // 18},{x},{y},0,350)\\fad(200,250)"
    elif enter == "slide":
        tags += f"\\move({x - width // 10},{y},{x},{y},0,400)\\fad(150,250)"
    else:
        tags += f"\\pos({x},{y})"
        tags += ("\\fad(0,250)\\fscx60\\fscy60\\alpha&HFF&\\t(0,180,\\fscx108\\fscy108\\alpha&H00&)\\t(180,280,\\fscx100\\fscy100)"
                 if enter == "pop" else "\\fad(300,250)")
    if t.get("size"):
        tags += f"\\fs{int(number(t['size'], 'title.size', 8, 600))}"
    if t.get("color"):
        tags += f"\\1c{ass_colour(t['color'])}"
    return ev(int(t.get("layer", 1)), start, start + dur, "Title", f"{{{tags}}}{ass_text(t['text'])}")


def kinetic_titles(args: argparse.Namespace) -> dict:
    project = vp.checked_project(args.project)
    spec_path, spec = load_spec(project, args.spec)
    width, height = canvas(spec)
    fps = rate(spec, 30)
    titles = spec.get("titles")
    if not isinstance(titles, list) or not titles:
        raise ValueError("titles must be a nonempty list")
    total = spec.get("duration") or max(float(t["start"]) + float(t["dur"]) for t in titles) + 0.5
    total = number(total, "duration", 0.2, 3600)
    font = str(spec.get("font", "Arial"))
    size = int(number(spec.get("font_size", height // 10), "font_size", 8, 600))
    style = (f"Style: Title,{font},{size},{ass_colour(spec.get('color'), WHITE)},{WHITE},{ass_colour(spec.get('outline_color'), BLACK)},"
             f"&H80000000,-1,0,0,0,100,100,1,0,1,{max(0, int(spec.get('outline', size // 24)))},{max(0, int(spec.get('shadow', 2)))},"
             f"5,40,40,40,1")
    events = [title_event(t, width, height) for t in titles]
    background = spec.get("background", "#101010")
    bg_path = None
    if isinstance(background, dict):
        bg_path = ed.owned(project, background["video"])
    elif not re.fullmatch(r"#?[0-9a-fA-F]{6}", str(background)):
        raise ValueError("background must be #RRGGBB or {\"video\": <project path>}")
    fonts = owned_dir(project, args.fonts_dir or spec.get("fonts_dir"))
    folder = ed.output_folder(project, "60-motion", "kinetic-titles")
    with (folder / "titles.ass").open("x", encoding="utf-8-sig", newline="\n") as stream:
        stream.write(ass_head(width, height, [style]) + "\n".join(events) + "\n")
    burn = f"ass=titles.ass{fontsdir_option(folder, fonts)}"
    ff = ffmpeg()
    if bg_path:
        command = [ff, "-hide_banner", "-nostdin", "-n", "-t", f"{total + 0.1:g}", "-i", bg_path, "-filter_complex",
                   f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,crop={width}:{height},setsar=1,"
                   f"fps={fps},tpad=stop_mode=clone:stop_duration={total:g},trim=duration={total:g},setpts=PTS-STARTPTS,{burn}[v]",
                   "-map", "[v]"]
    else:
        command = [ff, "-hide_banner", "-nostdin", "-n", "-f", "lavfi", "-i",
                   f"color=c=0x{str(background).lstrip('#')}:s={width}x{height}:r={fps}:d={total:g}",
                   "-filter_complex", f"[0:v]{burn}[v]", "-map", "[v]"]
    output = folder / "titles.mp4"
    command += ["-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(fps),
                "-t", f"{total:g}", "-movflags", "+faststart", output.name]
    ma.run(command, cwd=folder)
    return ed.register(project, folder, "kinetic-titles", {
        "video": str(output), "ass": str(folder / "titles.ass"), "duration": round(total, 3), "titles": len(events),
        "font": font, "fonts_dir": ed.rel(project, fonts) if fonts else None, "spec": ed.rel(project, spec_path),
        "inputs": inputs_record(project, [spec_path, *([bg_path] if bg_path else [])]),
        "command": [str(x) for x in command]})


# ---------------------------------------------------------------- CLI
def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = root.add_subparsers(dest="command", required=True)

    def command(name: str, handler, help_text: str) -> argparse.ArgumentParser:
        cmd = commands.add_parser(name, help=help_text, description=help_text)
        cmd.add_argument("--project", required=True)
        cmd.set_defaults(handler=handler)
        return cmd

    cmd = command("mv-edit", mv_edit, "Render an EDIT.json master (80-master) or --preview draft (50-edit)")
    cmd.add_argument("--edit", required=True, help="Project-owned edit JSON (format: docs/MONTAGE_CLI.md)")
    cmd.add_argument("--preview", action="store_true", help="960x540 veryfast draft in 50-edit")
    cmd.add_argument("--fonts-dir", help="Project-owned fonts folder for the ASS burn-in")
    cmd.add_argument("--loudness", choices=(*ma.PRESETS, "none"), help="Override the edit's loudness preset")
    cmd = command("mv-captions", mv_captions, "Write word-pop captions / lower third / callouts / cards as ASS (60-motion)")
    cmd.add_argument("--spec", required=True)
    cmd = command("ass-pin", ass_pin, "Pin bottom captions starting in [--from, --to) to --x/--y (new ASS in 60-motion)")
    cmd.add_argument("--input", required=True, help="Project-owned .ass")
    cmd.add_argument("--from", dest="start", type=float, required=True)
    cmd.add_argument("--to", dest="end", type=float, required=True)
    cmd.add_argument("--x", type=int, required=True)
    cmd.add_argument("--y", type=int, required=True)
    cmd.add_argument("--layer", type=int, default=2)
    cmd.add_argument("--align", default="an2", choices=tuple(f"an{i}" for i in range(1, 10)))
    cmd = command("mv-compile", mv_compile, "Comparison reel: title cards + labelled tile grids (50-edit)")
    cmd.add_argument("--spec", required=True)
    cmd.add_argument("--fonts-dir", help="Project-owned folder with the bold/black TTFs (default: Windows Arial)")
    cmd = command("audio-mix", audio_mix, "Mix stems by role with sidechain ducking + two-pass loudnorm (70-color-sound)")
    cmd.add_argument("--spec", required=True)
    cmd.add_argument("--preset", choices=(*ma.PRESETS, "none"), help="Override the spec loudness (default social)")
    cmd = command("loudnorm", loudnorm, "Two-pass loudnorm to a delivery preset; video stream copied (80-master)")
    cmd.add_argument("--input", required=True)
    cmd.add_argument("--preset", required=True, choices=tuple(ma.PRESETS))
    cmd.add_argument("--tolerance", type=float, help="LU around the target for the verification (default: preset)")
    cmd = command("kinetic-titles", kinetic_titles, "Animated ASS title cards over a colour or project video (60-motion)")
    cmd.add_argument("--spec", required=True)
    cmd.add_argument("--fonts-dir", help="Project-owned fonts folder for libass")
    return root


COMMAND_NAMES = ("mv-edit", "mv-captions", "ass-pin", "mv-compile", "audio-mix", "loudnorm", "kinetic-titles")


if __name__ == "__main__":
    try:
        args = parser().parse_args()
        result = args.handler(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("ok", True) else 1)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc), "type": type(exc).__name__}), file=sys.stderr)
        sys.exit(1)
