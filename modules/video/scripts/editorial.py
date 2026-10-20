"""Versioned CPU editorial tools. Run via the media-tools Python environment.

Scope: CFR cuts, optional source audio/music and deterministic effects.
All paths belong to the named project; sources/masters are never overwritten.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import subprocess
import sys
import uuid
from fractions import Fraction
from pathlib import Path

import montage_audio as ma
import video_pipeline as vp


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def owned(project: Path, value: str) -> Path:
    path = Path(value).expanduser()
    path = (path if path.is_absolute() else project / path).resolve()
    if not path.is_relative_to(project.resolve()) or not path.is_file():
        raise ValueError(f"Expected an existing file inside project: {value}")
    return path


def rel(project: Path, path: Path) -> str:
    return path.relative_to(project).as_posix()


def output_folder(project: Path, stage: str, name: str) -> Path:
    parent = (project / stage).resolve()
    if not parent.is_relative_to(project.resolve()):
        raise ValueError("Stage directory escapes the project")
    folder = parent / f"{name}-{uuid.uuid4().hex[:12]}"
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def media_info(source: Path) -> dict:
    info = vp.probe(source)
    video = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    if video is None:
        raise ValueError("Video stream required")
    return video


def cfr_info(source: Path) -> tuple[Fraction, int]:
    """Check every presentation timestamp, not just nominal/average rates."""
    video = media_info(source)
    rate = Fraction(video.get("avg_frame_rate", "0/1"))
    if rate <= 0:
        raise ValueError("Invalid frame rate")
    result = vp.run([vp.find_binary("ffprobe"), "-v", "error", "-select_streams", "v:0",
                     "-show_frames", "-show_entries", "frame=best_effort_timestamp_time",
                     "-of", "json", source], capture=True)
    frames = json.loads(result.stdout)["frames"]
    stamps = [float(f["best_effort_timestamp_time"]) for f in frames]
    if not stamps:
        raise ValueError("No decoded frames")
    step = 1 / float(rate)
    tolerance = max(0.000002, float(Fraction(video["time_base"])) * 1.1)
    if any(abs((b - a) - step) > tolerance for a, b in zip(stamps, stamps[1:])):
        raise ValueError("VFR or discontinuous timestamps: create an explicit CFR conform before editorial operations")
    return rate, len(stamps)


def register(project: Path, folder: Path, operation: str, payload: dict, *, manifest_name="manifest.json") -> dict:
    manifest = folder / manifest_name
    record = {"schema_version": 1, "created_at": vp.utc_now(), "operation": operation, **payload}
    record["artifacts"] = [{"path": rel(project, p), "sha256": vp.sha256(p)}
                           for p in sorted(folder.iterdir()) if p.is_file()]
    write_json(manifest, record)
    vp.append_render(project, {"operation": operation, "output": str(manifest),
                               "output_sha256": vp.sha256(manifest)})
    return {"ok": True, "output": str(manifest), **payload}


def scenes(args: argparse.Namespace) -> dict:
    from scenedetect import AdaptiveDetector, detect
    import scenedetect

    project = vp.checked_project(args.project)
    source = owned(project, args.input)
    if not math.isfinite(args.threshold) or args.threshold <= 0 or args.min_scene_frames < 1:
        raise ValueError("Threshold must be positive and finite; min scene frames >= 1")
    rate, count = cfr_info(source)
    digest = vp.sha256(source)
    detected = detect(str(source), AdaptiveDetector(adaptive_threshold=args.threshold,
                      min_scene_len=args.min_scene_frames), start_in_scene=True)
    cuts = sorted({0, count, *(end.get_frames() for _, end in detected if 0 < end.get_frames() < count)})
    folder = output_folder(project, "40-selects", "scenes")
    items, cards, commands = [], [], []
    for index, (start, end) in enumerate(zip(cuts, cuts[1:]), 1):
        middle = (start + end - 1) // 2
        thumbnail = folder / f"scene-{index:04d}.jpg"
        command = [vp.find_binary("ffmpeg"), "-v", "error", "-nostdin", "-n", "-i", source,
                   "-map", "0:v:0", "-vf", f"select=eq(n\\,{middle}),scale=480:-2,setsar=1",
                   "-frames:v", "1", "-q:v", "3", thumbnail]
        vp.run(command, capture=True)
        if not thumbnail.is_file():
            raise RuntimeError(f"No thumbnail for frame {middle}")
        commands.append([str(x) for x in command])
        item = {"id": f"{digest[:16]}:{start}:{end}", "in_frame": start, "out_frame": end,
                "start_seconds": float(Fraction(start, 1) / rate),
                "end_seconds": float(Fraction(end, 1) / rate), "thumbnail": rel(project, thumbnail)}
        items.append(item)
        cards.append(f'<figure><img src="{thumbnail.name}" width="480"><figcaption>Scene {index}: '
                     f'{start}–{end} frames · {item["start_seconds"]:.3f}–{item["end_seconds"]:.3f}s'
                     '</figcaption></figure>')
    payload = {"schema_version": 1, "source": rel(project, source), "source_sha256": digest,
               "fps": str(rate), "frame_count": count, "range_convention": "in-inclusive-out-exclusive",
               "detector": {"name": "AdaptiveDetector", "version": scenedetect.__version__,
                            "threshold": args.threshold, "min_scene_frames": args.min_scene_frames},
               "scenes": items}
    write_json(folder / "scenes.json", payload)
    (folder / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>Scene review</title>'
        '<style>body{font:16px system-ui;background:#17191d;color:#eee;margin:32px}'
        'main{display:flex;flex-wrap:wrap;gap:20px}figure{margin:0}figcaption{padding:12px 0}</style>'
        f'<h1>{html.escape(source.name)}</h1><p>{count} frames · {rate} fps · out exclusive</p>'
        '<main>' + ''.join(cards) + '</main>', encoding="utf-8")
    return register(project, folder, "scenes", {"catalog": str(folder / "scenes.json"),
                    "review": str(folder / "index.html"), "scene_count": len(items),
                    "source_sha256": digest, "commands": commands})


def validate_plan(project: Path, plan: dict) -> list[dict]:
    if plan.get("schema_version") != 1 or plan.get("kind") not in ("cuts-only-silent", "cuts-with-audio"):
        raise ValueError("Only schema v1 cuts-only-silent/cuts-with-audio plans are supported")
    rate = Fraction(plan["fps"])
    if rate <= 0 or not plan.get("clips"):
        raise ValueError("Positive fps and nonempty clips required")
    checked, cache = [], {}
    for clip in plan["clips"]:
        source = owned(project, clip["source"])
        if source not in cache:
            cache[source] = (*cfr_info(source), vp.sha256(source))
        actual_rate, count, digest = cache[source]
        if digest != clip["source_sha256"]:
            raise ValueError(f"Source hash mismatch: {source}")
        start, end = clip["in_frame"], clip["out_frame"]
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= count:
            raise ValueError("Invalid clip frame range")
        if actual_rate != rate:
            raise ValueError("Mixed frame rates require an explicit conform")
        checked.append({**clip, "path": source})
    if sum(c["out_frame"] - c["in_frame"] for c in checked) != plan["total_frames"]:
        raise ValueError("Plan total_frames does not match clip ranges")
    music = plan.get("music")
    if music:
        path = owned(project, music["source"])
        if vp.sha256(path) != music["source_sha256"]:
            raise ValueError("Music source hash mismatch")
        if not any(s["codec_type"] == "audio" for s in vp.probe(path)["streams"]):
            raise ValueError("Music has no audio stream")
        if not math.isfinite(music["gain_db"]) or not -60 <= music["gain_db"] <= 6:
            raise ValueError("Music gain must be between -60 and 6 dB")
        if "duck" in music:
            if not plan.get("source_audio"):
                raise ValueError("Music ducking needs source audio (--audio source) as the voice key")
            ma.checked_duck(music["duck"])
    if "audio_xfade" in plan:
        xfade = plan["audio_xfade"]
        if plan.get("kind") != "cuts-with-audio" or len(checked) < 2:
            raise ValueError("Audio crossfades need an audio plan with at least two clips")
        if isinstance(xfade, bool) or not isinstance(xfade, (int, float)) or not math.isfinite(xfade) or not 0 < xfade <= 0.5:
            raise ValueError("Audio crossfade must be within (0, 0.5] seconds")
        fps = float(Fraction(plan["fps"]))
        if any((c["out_frame"] - c["in_frame"]) / fps <= xfade for c in checked):
            raise ValueError("Audio crossfade must be shorter than every clip")
    return checked


def edit_plan(args: argparse.Namespace) -> dict:
    import opentimelineio as otio

    project = vp.checked_project(args.project)
    catalog_path = owned(project, args.catalog)
    catalog = read_json(catalog_path)
    indexes = [int(s.strip()) for s in args.select.split(",")]
    if not indexes or any(i < 1 or i > len(catalog["scenes"]) for i in indexes):
        raise ValueError("Select uses 1-based scene numbers, e.g. 3,1,2")
    clips = [{"source": catalog["source"], "source_sha256": catalog["source_sha256"],
              "in_frame": catalog["scenes"][i-1]["in_frame"],
              "out_frame": catalog["scenes"][i-1]["out_frame"], "reason": args.reason} for i in indexes]
    plan = {"schema_version": 1, "kind": "cuts-only-silent" if args.audio == "silent" and not args.music else "cuts-with-audio", "fps": catalog["fps"],
            "source_audio": args.audio == "source",
            "total_frames": sum(c["out_frame"] - c["in_frame"] for c in clips), "clips": clips,
            "limitations": ["Hard cuts; no retiming or color management; music mixed at fixed gain, no automatic ducking"]}
    if args.music:
        music = owned(project, args.music)
        plan["music"] = {"source": rel(project, music), "source_sha256": vp.sha256(music), "gain_db": args.music_gain}
    if getattr(args, "duck", False):
        if not args.music:
            raise ValueError("--duck needs --music")
        plan["music"]["duck"] = ma.checked_duck({"threshold": args.duck_threshold, "ratio": args.duck_ratio,
                                                 "attack": args.duck_attack, "release": args.duck_release})
    if getattr(args, "audio_xfade", 0):
        plan["audio_xfade"] = args.audio_xfade
    ducked = bool(plan.get("music", {}).get("duck"))
    if ducked or "audio_xfade" in plan:
        plan["limitations"] = ["Hard video cuts; no retiming or color management; "
                               + ("music ducked under source audio (sidechaincompress)" if ducked
                                  else "music mixed at fixed gain, no automatic ducking")
                               + (f"; {plan['audio_xfade']:g} s audio crossfades at cuts" if "audio_xfade" in plan else "")]
    checked = validate_plan(project, plan)
    folder = output_folder(project, "50-edit", "edit-plan")
    timeline = otio.schema.Timeline(name=folder.name)
    track = otio.schema.Track(kind=otio.schema.TrackKind.Video)
    timeline.tracks.append(track)
    fps = float(Fraction(plan["fps"]))
    audio_track = otio.schema.Track(name="Source audio", kind=otio.schema.TrackKind.Audio)
    for clip in checked:
        track.append(otio.schema.Clip(name=clip["path"].name,
            media_reference=otio.schema.ExternalReference(target_url=clip["path"].as_uri()),
            source_range=otio.opentime.TimeRange(otio.opentime.RationalTime(clip["in_frame"], fps),
                otio.opentime.RationalTime(clip["out_frame"]-clip["in_frame"], fps))))
        if plan["source_audio"]:
            span = otio.opentime.TimeRange(otio.opentime.RationalTime(clip["in_frame"], fps),
                otio.opentime.RationalTime(clip["out_frame"]-clip["in_frame"], fps))
            if any(s["codec_type"] == "audio" for s in vp.probe(clip["path"])["streams"]):
                audio_track.append(otio.schema.Clip(name=clip["path"].name,
                    media_reference=otio.schema.ExternalReference(target_url=clip["path"].as_uri()), source_range=span))
            else:
                audio_track.append(otio.schema.Gap(duration=span.duration))
    if plan["source_audio"]:
        timeline.tracks.append(audio_track)
    if plan.get("music"):
        # Gain is explicit metadata; native OTIO does not standardize mixer gain.
        music_track = otio.schema.Track(name="Music", kind=otio.schema.TrackKind.Audio,
            metadata={"pipeline_gain_db": plan["music"]["gain_db"], "apply_gain_in_nle": True,
                      **({"pipeline_duck": plan["music"]["duck"]} if plan["music"].get("duck") else {})})
        music_path = owned(project, plan["music"]["source"])
        duration = float(vp.probe(music_path)["format"]["duration"])
        music_frames = min(plan["total_frames"], int(duration * fps))
        music_track.append(otio.schema.Clip(name=music_path.name,
            media_reference=otio.schema.ExternalReference(target_url=music_path.as_uri()),
            source_range=otio.opentime.TimeRange(otio.opentime.RationalTime(0, fps),otio.opentime.RationalTime(music_frames, fps))))
        if music_frames < plan["total_frames"]:
            music_track.append(otio.schema.Gap(duration=otio.opentime.RationalTime(plan["total_frames"]-music_frames, fps)))
        timeline.tracks.append(music_track)
    write_json(folder / "edit-plan.json", plan)
    otio.adapters.write_to_file(timeline, str(folder / "timeline.otio"))
    return register(project, folder, "edit-plan", {"plan": str(folder / "edit-plan.json"),
                     "otio": str(folder / "timeline.otio"), "catalog_sha256": vp.sha256(catalog_path),
                     "total_frames": plan["total_frames"], "kind": plan["kind"]})


def preview(args: argparse.Namespace) -> dict:
    project = vp.checked_project(args.project)
    plan_path = owned(project, args.plan)
    plan = read_json(plan_path)
    clips = validate_plan(project, plan)
    if args.width < 2 or args.height < 2 or args.width % 2 or args.height % 2:
        raise ValueError("Preview dimensions must be positive even integers")
    folder = output_folder(project, "50-edit", "preview")
    command = [vp.find_binary("ffmpeg"), "-v", "error", "-nostdin", "-n"]
    filters = []
    audio = plan["kind"] == "cuts-with-audio"
    fps = float(Fraction(plan["fps"]))
    xfade = plan.get("audio_xfade", 0) if audio else 0
    for i, clip in enumerate(clips):
        command += ["-i", clip["path"]]
        filters.append(f'[{i}:v:0]trim=start_frame={clip["in_frame"]}:end_frame={clip["out_frame"]},'
            f'setpts=PTS-STARTPTS,scale={args.width}:{args.height}:force_original_aspect_ratio=decrease,'
            f'pad={args.width}:{args.height}:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]')
        if audio:
            # With crossfades every clip but the last carries an xfade-long handle that acrossfade consumes.
            length = (clip["out_frame"]-clip["in_frame"])/fps + (xfade if i < len(clips) - 1 else 0)
            streams = vp.probe(clip["path"])["streams"]
            stream = next((s for s in streams if s["codec_type"] == "audio"), None)
            if plan.get("source_audio") and stream:
                video = next(s for s in streams if s["codec_type"] == "video")
                if abs(float(stream.get("start_time", 0))-float(video.get("start_time", 0))) > 1/fps:
                    raise ValueError("Offset audio/video starts require explicit conform")
                filters.append(f'[{i}:a:0]asetpts=PTS-STARTPTS,atrim=start={clip["in_frame"]/fps}:end={clip["in_frame"]/fps + length},'
                    f'asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={length}[a{i}]')
            else:
                filters.append(f'anullsrc=r=48000:cl=stereo,atrim=duration={length}[a{i}]')
    if audio:
        if xfade:
            filters.append(''.join(f'[v{i}]' for i in range(len(clips))) + f'concat=n={len(clips)}:v=1:a=0[out]')
            current = "a0"
            for i in range(1, len(clips)):
                label = "cutaudio" if i == len(clips) - 1 else f"ax{i}"
                filters.append(f'[{current}][a{i}]acrossfade=d={xfade:g}:c1=tri:c2=tri[{label}]')
                current = label
        else:
            filters.append(''.join(f'[v{i}][a{i}]' for i in range(len(clips))) + f'concat=n={len(clips)}:v=1:a=1[out][cutaudio]')
        if plan.get("music"):
            command += ["-i", owned(project, plan["music"]["source"])]
            filters.append(f'[{len(clips)}:a:0]asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,'
                f'volume={plan["music"]["gain_db"]}dB,apad,atrim=duration={plan["total_frames"]/fps}[music]')
            if plan["music"].get("duck"):
                filters.append('[cutaudio]asplit=2[cutmix][duckkey]')
                filters.append(ma.duck_filter("music", "duckkey", "musicducked", plan["music"]["duck"]))
                filters.append('[cutmix][musicducked]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=0:latency=1[aout]')
            else:
                filters.append('[cutaudio][music]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=0:latency=1[aout]')
        else:
            filters.append('[cutaudio]anull[aout]')
    else:
        filters.append(''.join(f'[v{i}]' for i in range(len(clips))) + f'concat=n={len(clips)}:v=1:a=0[out]')
    graph = folder / "filters.txt"
    graph.write_text(';\n'.join(filters), encoding="utf-8")
    output = folder / ("preview-av.mp4" if audio else "preview-silent.mp4")
    command += ["-filter_complex_script", graph, "-map", "[out]"]
    command += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"] if audio else ["-an"]
    command += ["-r", plan["fps"],
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", output]
    vp.run(command, capture=True)
    rate, count = cfr_info(output)
    if count != plan["total_frames"] or rate != Fraction(plan["fps"]):
        raise RuntimeError(f"Preview frame verification failed: {count} frames at {rate}")
    extra = {"audio_xfade": xfade} if xfade else {}
    if audio and plan.get("music", {}).get("duck"):
        extra["music_duck"] = plan["music"]["duck"]
    return register(project, folder, "preview", {"video": str(output), "plan_sha256": vp.sha256(plan_path),
                     "total_frames": count, "audio": "source/music" if audio else "intentionally absent", **extra,
                     "command": [str(x) for x in command]})


def qc(args: argparse.Namespace) -> dict:
    project = vp.checked_project(args.project)
    source = owned(project, args.input)
    if args.expected_frames is not None and args.expected_frames < 1:
        raise ValueError("expected-frames must be positive")
    folder = output_folder(project, "80-master", "qc")
    info = vp.probe(source)
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    command = [vp.find_binary("ffmpeg"), "-hide_banner", "-nostdin", "-xerror", "-i", source,
               "-map", "0:v:0", "-map", "0:a?", "-vf", "blackdetect=d=0.2:pix_th=0.1,freezedetect=n=-60dB:d=1"]
    if has_audio:
        command += ["-af", "silencedetect=n=-50dB:d=0.5,ebur128=peak=true"]
    command += ["-f", "null", "-"]
    completed = subprocess.run([str(x) for x in command], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    (folder / "ffmpeg.log").write_text(completed.stderr, encoding="utf-8")
    errors = []
    if completed.returncode:
        errors.append("Full decode/filter pass failed; see ffmpeg.log")
    if args.require_audio and not has_audio:
        errors.append("Required audio stream missing")
    loudness = "Measured in ffmpeg.log if audio exists; no delivery loudness target was supplied"
    if getattr(args, "loudness_preset", None):
        target = ma.preset(args.loudness_preset)
        tolerance = getattr(args, "loudness_tolerance", None)
        loudness = {"preset": target["name"], "target_lufs": target["I"], "max_true_peak_dbtp": target["TP"],
                    "tolerance_lu": target["tolerance"] if tolerance is None else tolerance}
        if not has_audio:
            loudness_errors = ["Loudness preset requires an audio stream"]
        else:
            try:
                measured = ma.measure(vp.find_binary("ffmpeg"), source, target)
                loudness["measured"] = {k: v for k, v in measured.items() if k != "raw"}
                loudness_errors = ma.check(measured, target, tolerance)
            except (RuntimeError, ValueError) as exc:
                loudness_errors = [f"Loudness measurement failed: {exc}"]
        loudness["errors"], loudness["pass"] = loudness_errors, not loudness_errors
        errors += loudness_errors
    count, rate = None, None
    if args.expected_frames is not None:
        try:
            rate, count = cfr_info(source)
            if count != args.expected_frames:
                errors.append(f"Frame count {count} != expected {args.expected_frames}")
        except (ValueError, RuntimeError) as exc:
            errors.append(str(exc))
    events = [line for line in completed.stderr.splitlines()
              if any(key in line for key in ("black_start:", "freeze_start:", "freeze_end:", "silence_start:", "silence_end:"))]
    payload = {"source": rel(project, source), "source_sha256": vp.sha256(source),
               "technical_pass": not errors, "errors": errors, "review_events": events,
               "audio_present": has_audio, "frame_count": count, "fps": str(rate) if rate else None,
               "probe": info, "command": [str(x) for x in command],
               "approval": "not-approved; visual/audio review required",
               "loudness": loudness}
    write_json(folder / "qc.json", payload)
    summary = {"report": str(folder / "qc.json"), "technical_pass": not errors, "errors": errors,
               "review_event_count": len(events)}
    if isinstance(loudness, dict):
        summary["loudness"] = loudness
    result = register(project, folder, "qc", summary)
    result["ok"] = not errors
    return result


def run_in(folder: Path, command: list) -> None:
    """Run FFmpeg inside `folder` so the subtitles filter gets a bare file name (no Windows drive-colon escaping)."""
    completed = subprocess.run([str(x) for x in command], cwd=folder, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", stdin=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout or "ffmpeg failed").strip()[-3000:])


def burn_subtitles(folder: Path, video: Path, ass: Path, output: Path, crf: int = 18) -> None:
    """Subtitles are burned last, onto the finished cut (video-use rule), audio copied untouched."""
    run_in(folder, [vp.find_binary("ffmpeg"), "-v", "error", "-nostdin", "-n", "-i", video.name,
                    "-vf", f"subtitles=f={ass.name}", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
                    "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", output.name])


def duration_of(path: Path) -> float:
    return float(vp.probe(path)["format"]["duration"])


AFADE = 0.03  # 30 ms fade in/out on every cut: no clicks at the joins (video-use)


def rough_render(args: argparse.Namespace) -> dict:
    """Render a rough-plan EDL: frame-accurate per-segment re-encode with identical parameters and 30 ms audio fades,
    lossless concat (-c copy) of the segments, transcript words remapped to the cut, subtitles burned last."""
    import rough_cut
    import shorts
    project = vp.checked_project(args.project)
    edl_path = owned(project, args.edl)
    edl = read_json(edl_path)
    source = rough_cut.validate_edl(project, edl)
    video = media_info(source)
    rate = Fraction(video.get("avg_frame_rate", "0/1"))
    if rate <= 0:
        raise ValueError("Invalid source frame rate")
    fps = float(rate)
    width, height = int(video["width"]), int(video["height"])
    has_audio = any(s["codec_type"] == "audio" for s in vp.probe(source)["streams"])
    ffmpeg = vp.find_binary("ffmpeg")
    folder = output_folder(project, "50-edit", "rough-cut")
    parts = folder / "segments"
    parts.mkdir()
    timeline, cursor, total_frames = [], 0.0, 0
    for seg in edl["segments"]:
        frames = max(1, round((float(seg["end"]) - float(seg["start"])) * fps))
        length = frames / fps
        part = parts / f"seg-{seg['index']:03d}.mp4"
        command = [ffmpeg, "-v", "error", "-nostdin", "-n", "-ss", f"{float(seg['start']):.3f}", "-i", source]
        if not has_audio:
            command += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        fade_out = max(length - AFADE, 0.0)
        command += ["-map", "0:v:0", "-map", "0:a:0" if has_audio else "1:a:0", "-frames:v", str(frames),
                    "-af", f"aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={length:.6f},"
                           f"afade=t=in:d={AFADE},afade=t=out:st={fade_out:.6f}:d={AFADE}",
                    "-r", str(rate), "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf), "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-video_track_timescale", "90000", part]
        vp.run(command, capture=True)
        timeline.append({"index": seg["index"], "source_start": seg["start"], "source_end": seg["end"],
                         "out_start": round(cursor, 3), "frames": frames})
        cursor += length
        total_frames += frames
    concat = folder / "concat.txt"
    concat.write_text("".join(f"file 'segments/seg-{s['index']:03d}.mp4'\n" for s in timeline), encoding="utf-8")
    rough = folder / "rough-cut.mp4"
    run_in(folder, [ffmpeg, "-v", "error", "-nostdin", "-n", "-f", "concat", "-safe", "0", "-i", concat.name,
                    "-c", "copy", "-movflags", "+faststart", rough.name])
    expected = total_frames / fps
    actual = duration_of(rough)
    if abs(actual - expected) > max(0.25, 0.02 * len(timeline)):
        raise RuntimeError(f"Rough cut duration {actual:.2f} s differs from the EDL {expected:.2f} s")
    payload = {"edl": rel(project, edl_path), "edl_sha256": vp.sha256(edl_path), "video": str(rough),
               "segments": len(timeline), "total_frames": total_frames, "duration": round(actual, 3), "timeline": timeline}
    if args.subtitles != "none":
        transcript = shorts.load_transcript(owned(project, edl["transcript"]))
        groups = []
        for seg, slot in zip(edl["segments"], timeline):
            end = float(seg["start"]) + slot["frames"] / fps
            for g in shorts.caption_groups(transcript["words"], transcript["segments"], float(seg["start"]), end,
                                           max_words=args.caption_words, max_chars=args.caption_chars):
                groups.append({"start": g["start"] + slot["out_start"], "end": g["end"] + slot["out_start"],
                               "text": g["text"]})
        srt, ass = folder / "rough-cut.srt", folder / "rough-cut.ass"
        shorts.write_subtitles(groups, srt, ass, width, height, args.font, margin_ratio=0.06, upper=False, size_ratio=0.05)
        payload.update(subtitles=str(srt), captions=len(groups))
        if args.subtitles == "burn":
            burned = folder / "rough-cut-subs.mp4"
            burn_subtitles(folder, rough, ass, burned, args.crf)
            payload["video_subtitled"] = str(burned)
    return register(project, folder, "rough-render", payload)


def assemble_narrated(project: Path, folder: Path, clips: list[Path], durations: list[float], narration: Path,
                      groups: list[dict], width: int, height: int, fps: int, font: str, crf: int = 18) -> dict:
    """Story assembly: every scene clip fitted to WxH at `fps` and stretched (last frame held) or trimmed to its
    voice-over segment, concatenated under the narration track; captions burned last. Returns output paths."""
    import shorts
    if len(clips) != len(durations) or not clips:
        raise ValueError("Need one duration per clip")
    command = [vp.find_binary("ffmpeg"), "-v", "error", "-nostdin", "-n"]
    filters = []
    for i, (clip, seconds) in enumerate(zip(clips, durations)):
        command += ["-i", clip]
        filters.append(f"[{i}:v:0]fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease,"
                       f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,setpts=PTS-STARTPTS,"
                       f"tpad=stop_mode=clone:stop_duration={seconds:.3f},trim=duration={seconds:.3f},"
                       f"setpts=PTS-STARTPTS[v{i}]")
    command += ["-i", narration]
    total = sum(durations)
    filters.append("".join(f"[v{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=0[vout]")
    filters.append(f"[{len(clips)}:a:0]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={total:.3f},"
                   f"afade=t=out:st={max(total - 0.3, 0):.3f}:d=0.3[aout]")
    graph = folder / "assemble-filters.txt"
    graph.write_text(";\n".join(filters), encoding="utf-8")
    video = folder / "story.mp4"
    command += ["-filter_complex_script", graph, "-map", "[vout]", "-map", "[aout]", "-r", str(fps),
                "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", video]
    vp.run(command, capture=True)
    result = {"video": video, "duration": round(duration_of(video), 3)}
    if groups:
        srt, ass = folder / "story.srt", folder / "story.ass"
        shorts.write_subtitles(groups, srt, ass, width, height, font, margin_ratio=0.12 if height > width else 0.06,
                               upper=False, size_ratio=0.04 if height > width else 0.05)
        burned = folder / "story-subs.mp4"
        burn_subtitles(folder, video, ass, burned, crf)
        result.update(subtitles=srt, video_subtitled=burned)
    return result


DELIVERY_LIMIT = 48 * 1024**2
FINAL_VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".mxf", ".avi"}


def delivery_outbox():
    raise RuntimeError('Messaging delivery is not bundled. Export and review files locally.')


def checked_final(project: Path, value: str, report_value: str, loudness_preset: str | None = None) -> dict:
    source = owned(project, value)
    if source.relative_to(project).parts[0] not in ("80-master", "90-delivery"):
        raise ValueError("Delivery requires a final in 80-master or 90-delivery")
    if source.suffix.lower() not in FINAL_VIDEO_SUFFIXES or source.stat().st_size == 0:
        raise ValueError("Expected a nonempty final video")
    report_path = owned(project, report_value)
    report = read_json(report_path)
    digest = vp.sha256(source)
    if (report.get("technical_pass") is not True or report.get("errors") != []
            or owned(project, report["source"]) != source or report.get("source_sha256") != digest):
        raise ValueError("Final requires a passing QC report matching its current path and SHA-256")
    if loudness_preset:
        loudness = report.get("loudness")
        if not isinstance(loudness, dict) or loudness.get("preset") != loudness_preset or loudness.get("pass") is not True:
            raise ValueError(f"Final requires a QC report that passed the {loudness_preset} loudness preset")
    return {"source": str(source), "sha256": digest, "bytes": source.stat().st_size,
            "qc": str(report_path), "qc_sha256": vp.sha256(report_path)}


def deliver(args: argparse.Namespace) -> dict:
    """Publish only the explicitly selected and approved, hash-bound final videos."""
    import shutil
    if not args.approved:
        raise ValueError("--approved is required after visual/audio review of all selected files")
    if not args.title.strip():
        raise ValueError("A nonempty result title is required")
    project = vp.checked_project(args.project)  # Path, not a project metadata dictionary
    selection_path = owned(project, args.selection)
    selection = read_json(selection_path)
    items = selection.get("files")
    if selection.get("schema_version") != 1 or not isinstance(items, list) or not 1 <= len(items) <= 30:
        raise ValueError("Selection schema v1 requires 1..30 files")
    records, seen_masters, seen_files = [], set(), set()
    for item in items:
        preset = getattr(args, "loudness_preset", None)
        master = checked_final(project, item["master"], item["qc"], preset)
        selected = master
        if item.get("delivery_copy"):
            selected = checked_final(project, item["delivery_copy"], item["delivery_qc"], preset)
            if Path(selected["source"]).relative_to(project).parts[0] != "90-delivery":
                raise ValueError("Compact copies must be in 90-delivery")
        if selected["bytes"] > DELIVERY_LIMIT:
            raise ValueError("Final exceeds 48 MiB: export and review a compact delivery_copy, run QC, then select it")
        if master["source"] in seen_masters or selected["source"] in seen_files:
            raise ValueError("Duplicate master or delivery file")
        seen_masters.add(master["source"])
        seen_files.add(selected["source"])
        records.append({"master": master, "selected": selected})
    # All gates pass before any publication. Freeze bytes and recheck QC hashes;
    # Outbox then takes its own immutable snapshot. Masters remain untouched.
    folder = output_folder(project, "90-delivery", "delivery")
    staged = []
    for index, record in enumerate(records, 1):
        source = Path(record["selected"]["source"])
        destination = folder / f"{index:02d}-{source.name}"
        with source.open("rb") as src, destination.open("xb") as dst:
            shutil.copyfileobj(src, dst)
        if vp.sha256(destination) != record["selected"]["sha256"]:
            raise ValueError("Selected file changed after QC validation; nothing enqueued")
        staged.append(destination)
        record["snapshot"] = str(destination)
    payload = {"project": args.project, "title": args.title.strip(), "approved": True,
               "selection": str(selection_path), "selection_sha256": vp.sha256(selection_path),
               "files": records, "state": "prepared", "created_at": vp.utc_now()}
    write_json(folder / "selection.json", payload)
    # No transport/drain call here. Public Outbox identity handles repeat enqueue.
    delivery = delivery_outbox().enqueue(staged, args.title.strip(), project=args.project, note=args.note)
    write_json(folder / "delivery-receipt.json", delivery)
    return register(project, folder, "deliver", {"state": "enqueued", "delivery": delivery,
                    "receipt": str(folder / "delivery-receipt.json"), "files": records,
                    "note": "Enqueued is not sent; only Outbox receipt status complete confirms delivery"})


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    for name, handler in (("scenes", scenes), ("edit-plan", edit_plan), ("preview", preview), ("qc", qc)):
        cmd = commands.add_parser(name)
        cmd.add_argument("--project", required=True)
        cmd.set_defaults(handler=handler)
        if name in ("scenes", "qc"):
            cmd.add_argument("--input", required=True)
        if name == "scenes":
            cmd.add_argument("--threshold", type=float, default=3.0)
            cmd.add_argument("--min-scene-frames", type=int, default=15)
        elif name == "edit-plan":
            cmd.add_argument("--catalog", required=True)
            cmd.add_argument("--select", required=True, help="1-based scene numbers in desired order: 3,1,2")
            cmd.add_argument("--reason", required=True)
            cmd.add_argument("--audio", choices=("silent", "source"), default="silent")
            cmd.add_argument("--music", help="Optional project-owned rendered audio component")
            cmd.add_argument("--music-gain", type=float, default=-12.0)
            cmd.add_argument("--duck", action="store_true", help="Duck music under source audio (sidechaincompress)")
            cmd.add_argument("--duck-threshold", type=float, default=ma.DUCK_DEFAULTS["threshold"])
            cmd.add_argument("--duck-ratio", type=float, default=ma.DUCK_DEFAULTS["ratio"])
            cmd.add_argument("--duck-attack", type=float, default=ma.DUCK_DEFAULTS["attack"], help="ms")
            cmd.add_argument("--duck-release", type=float, default=ma.DUCK_DEFAULTS["release"], help="ms")
            cmd.add_argument("--audio-xfade", type=float, default=0.0,
                             help="Seconds of audio crossfade at each cut (0 = hard cuts, max 0.5)")
        elif name == "preview":
            cmd.add_argument("--plan", required=True)
            cmd.add_argument("--width", type=int, default=1280)
            cmd.add_argument("--height", type=int, default=720)
        else:
            cmd.add_argument("--require-audio", action="store_true")
            cmd.add_argument("--expected-frames", type=int)
            cmd.add_argument("--loudness-preset", choices=tuple(ma.PRESETS),
                             help="Fail QC unless integrated LUFS/true peak meet this delivery preset")
            cmd.add_argument("--loudness-tolerance", type=float, help="LU around the target (default: preset)")
    cmd = commands.add_parser("rough-render", help="Render a rough-plan EDL (rough_cut.py): cuts, 30 ms fades, concat, subtitles last")
    cmd.add_argument("--project", required=True)
    cmd.add_argument("--edl", required=True, help="Project-owned edl.json from rough-plan")
    cmd.add_argument("--subtitles", choices=("burn", "file", "none"), default="burn")
    cmd.add_argument("--font", default="Arial")
    cmd.add_argument("--caption-words", type=int, default=7)
    cmd.add_argument("--caption-chars", type=int, default=42)
    cmd.add_argument("--crf", type=int, default=18)
    cmd.set_defaults(handler=rough_render)
    cmd = commands.add_parser("deliver", help="Explicitly enqueue approved final videos after QC")
    cmd.add_argument("--project", required=True)
    cmd.add_argument("--selection", required=True, help="Project-owned JSON listing master/qc and optional delivery_copy/delivery_qc")
    cmd.add_argument("--title", required=True)
    cmd.add_argument("--note", default="")
    cmd.add_argument("--approved", action="store_true", help="Confirm visual/audio approval of every selected master and copy")
    cmd.add_argument("--loudness-preset", choices=tuple(ma.PRESETS),
                     help="Also require every QC report to have passed this loudness preset")
    cmd.set_defaults(handler=deliver)
    return root


if __name__ == "__main__":
    try:
        args = parser().parse_args()
        result = args.handler(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("ok", True) else 1)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc), "type": type(exc).__name__}), file=sys.stderr)
        sys.exit(1)
