"""Shared FFmpeg audio helpers for editorial.py and montage.py (CPU only).

- Delivery loudness presets and a two-pass `loudnorm` (pass 1 measures, pass 2 applies linear gain).
- Integrated loudness / true-peak measurement and a tolerance check for QC.
- Role-based stem mixing with sidechain ducking (ported from _shared/kinetic.mix and _shared/mv30/edit.py).
Nothing here writes outside the paths the caller passes; callers own versioned output folders.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

# Integrated loudness (LUFS), max true peak (dBTP), loudness range target and integrated tolerance (LU).
PRESETS = {
    "social": {"I": -14.0, "TP": -1.0, "LRA": 11.0, "tolerance": 1.0},     # web/social platforms
    "broadcast": {"I": -23.0, "TP": -1.0, "LRA": 20.0, "tolerance": 0.5},  # EBU R128 file delivery
}
TRUE_PEAK_SLACK = 0.1  # dB of meter disagreement allowed between loudnorm passes
AAC_TP_MARGIN = 0.5  # dB below the true-peak target for AAC outputs
DUCK_DEFAULTS = {"threshold": 0.025, "ratio": 5.0, "attack": 15.0, "release": 300.0}
DUCK_LIMITS = {"threshold": (0.000976563, 1.0), "ratio": (1.0, 20.0), "attack": (0.01, 2000.0), "release": (0.01, 9000.0)}


def run(command: list, cwd: Path | None = None) -> subprocess.CompletedProcess:
    completed = subprocess.run([str(x) for x in command], capture_output=True, text=True, encoding="utf-8",
                               errors="replace", stdin=subprocess.DEVNULL, cwd=cwd,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout or "ffmpeg failed").strip()[-3000:])
    return completed


def preset(name: str) -> dict:
    if name not in PRESETS:
        raise ValueError(f"Unknown loudness preset {name!r}; use one of {', '.join(PRESETS)}")
    return dict(PRESETS[name], name=name)


def checked_duck(values: dict | None) -> dict:
    """Merge user ducking parameters over defaults and range-check them (sidechaincompress limits)."""
    duck = {**DUCK_DEFAULTS, **(values or {})}
    for key, (low, high) in DUCK_LIMITS.items():
        value = duck[key]
        if not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"Ducking {key} must be within {low}..{high}")
    return {k: float(duck[k]) for k in DUCK_LIMITS}


def duck_filter(target: str, key: str, out: str, duck: dict) -> str:
    """`target` is compressed by `key` (the key label is consumed; asplit it first if it is also mixed)."""
    d = checked_duck(duck)
    return (f"[{target}][{key}]sidechaincompress=threshold={d['threshold']:g}:ratio={d['ratio']:g}:"
            f"attack={d['attack']:g}:release={d['release']:g}[{out}]")


def parse_loudnorm(stderr: str) -> dict:
    start, end = stderr.rfind("{"), stderr.rfind("}")
    if start < 0 or end < start:
        raise RuntimeError("loudnorm printed no JSON summary")
    return json.loads(stderr[start:end + 1])


def _number(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def measure(ffmpeg, source: Path, target: dict | None = None, pre: str = "") -> dict:
    """Pass 1: EBU R128 integrated loudness, true peak and LRA of the first audio stream (after optional `pre` filters)."""
    t = target or PRESETS["social"]
    completed = run([ffmpeg, "-hide_banner", "-nostdin", "-i", source, "-map", "0:a:0", "-af",
                     (pre + "," if pre else "") + f"loudnorm=I={t['I']}:TP={t['TP']}:LRA={t['LRA']}:print_format=json",
                     "-f", "null", "-"])
    raw = parse_loudnorm(completed.stderr)
    return {"integrated_lufs": _number(raw.get("input_i")), "true_peak_dbtp": _number(raw.get("input_tp")),
            "lra_lu": _number(raw.get("input_lra")), "threshold_lufs": _number(raw.get("input_thresh")),
            "target_offset": _number(raw.get("target_offset")), "raw": raw}


def check(measured: dict, target: dict, tolerance: float | None = None) -> list[str]:
    """Errors when integrated loudness is outside target +- tolerance or true peak exceeds the ceiling."""
    tol = target["tolerance"] if tolerance is None else tolerance
    if not math.isfinite(tol) or tol <= 0:
        raise ValueError("Loudness tolerance must be positive")
    errors = []
    i, tp = measured.get("integrated_lufs"), measured.get("true_peak_dbtp")
    if i is None:
        errors.append("Integrated loudness not measurable (silent or no audio)")
    elif abs(i - target["I"]) > tol:
        errors.append(f"Integrated loudness {i:.1f} LUFS outside {target['I']:g} +- {tol:g} LU")
    if tp is None:
        errors.append("True peak not measurable")
    elif tp > target["TP"] + TRUE_PEAK_SLACK:
        errors.append(f"True peak {tp:.1f} dBTP above {target['TP']:g} dBTP")
    return errors


def normalize_filter(measured: dict, target: dict) -> str:
    """Pass 2 filter from a pass-1 measurement (linear gain where loudnorm can keep it linear)."""
    raw = measured["raw"]
    return (f"loudnorm=I={target['I']}:TP={target['TP']}:LRA={target['LRA']}:measured_I={raw['input_i']}:"
            f"measured_TP={raw['input_tp']}:measured_LRA={raw['input_lra']}:measured_thresh={raw['input_thresh']}:"
            f"offset={raw['target_offset']}:linear=true:print_format=json,aresample=48000")


def two_pass(ffmpeg, source: Path, output: Path, target: dict, *, video: bool) -> dict:
    """Normalize `source` into the new path `output` (never overwrites). Video is stream-copied untouched."""
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    first = measure(ffmpeg, source, target)
    if first["integrated_lufs"] is None or first["true_peak_dbtp"] is None:
        raise ValueError("Source audio is silent or unmeasurable; nothing to normalize")
    # loudnorm stays linear only if the gain keeps true peak under the ceiling; otherwise it silently falls back
    # to dynamic mode and misses the target. Then pre-gain + peak limiter first and measure that chain (deterministic).
    # Lossy AAC re-encode overshoots true peak by a few tenths of a dB: aim lower for video outputs.
    aim = dict(target, TP=round(target["TP"] - (AAC_TP_MARGIN if video else 0.0), 2))
    gain = target["I"] - first["integrated_lufs"]
    pre, mode, chain_measure = "", "linear", first
    if first["true_peak_dbtp"] + gain > aim["TP"] - TRUE_PEAK_SLACK:
        limit = 10 ** ((aim["TP"] - 1.5) / 20)  # sample-peak limiter with headroom for inter-sample peaks
        pre = f"volume={gain:.2f}dB,alimiter=limit={limit:.4f}:level=0:attack=1:release=50"
        mode, chain_measure = "pre-gain+limiter, then linear", measure(ffmpeg, source, aim, pre)
    audio_filter = (pre + "," if pre else "") + normalize_filter(chain_measure, aim)
    command = [ffmpeg, "-hide_banner", "-nostdin", "-n", "-i", source]
    if video:
        command += ["-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy", "-af", audio_filter,
                    "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", output]
    else:
        command += ["-map", "0:a:0", "-af", audio_filter, "-c:a", "pcm_s24le", output]
    run(command)
    second = measure(ffmpeg, output, target)
    return {"before": first, "after": second, "mode": mode, "command": [str(x) for x in command]}


def mix_graph(tracks: list[dict], total: float, duck: dict | None = None,
              duration_of=None) -> tuple[list[str], str]:
    """Role mix graph: per-track trim/gain/fades/delay padded to `total`, roles summed, optional duck, limiter.

    tracks: [{"src", "start", "in", "dur", "gain_db", "fade_in", "fade_out", "role"}], inputs indexed 0..n-1.
    duck: {"key": role, "target": role, threshold/ratio/attack/release}. Returns (filters, output label).
    """
    if not tracks:
        raise ValueError("Audio mix needs at least one track")
    if not math.isfinite(total) or total <= 0:
        raise ValueError("Mix duration must be positive")
    filters, roles = [], {}
    for j, s in enumerate(tracks):
        gain = float(s.get("gain_db", 0))
        if not -60 <= gain <= 12:
            raise ValueError("Track gain must be between -60 and 12 dB")
        trim = f"atrim=start={float(s.get('in', 0)):g}" + (f":duration={float(s['dur']):g}" if s.get("dur") else "")
        chain = f"[{j}:a]aresample=48000,aformat=channel_layouts=stereo,{trim},asetpts=PTS-STARTPTS,volume={gain:g}dB"
        if s.get("fade_in"):
            chain += f",afade=t=in:d={float(s['fade_in']):g}"
        if s.get("fade_out"):
            length = s.get("dur") or ((duration_of(s["src"]) - float(s.get("in", 0))) if duration_of else None)
            if length:
                chain += f",afade=t=out:st={max(0.0, length - float(s['fade_out'])):.3f}:d={float(s['fade_out']):g}"
        chain += (f",adelay={int(round(float(s.get('start', 0)) * 1000))}:all=1,"
                  f"apad=whole_dur={total:.3f},atrim=duration={total:.3f}[a{j}]")
        filters.append(chain)
        roles.setdefault(s.get("role", "sfx"), []).append(f"a{j}")
    groups = {}
    for role, labels in roles.items():
        if len(labels) == 1:
            groups[role] = labels[0]
        else:
            filters.append("".join(f"[{x}]" for x in labels) + f"amix=inputs={len(labels)}:normalize=0[g_{role}]")
            groups[role] = f"g_{role}"
    if duck and duck.get("key") in groups and duck.get("target") in groups and duck["key"] != duck["target"]:
        key, target = groups[duck["key"]], groups[duck["target"]]
        filters.append(f"[{key}]asplit=2[k_mix][k_sc]")
        filters.append(duck_filter(target, "k_sc", "ducked", {k: v for k, v in duck.items() if k in DUCK_LIMITS}))
        groups[duck["key"]], groups[duck["target"]] = "k_mix", "ducked"
    elif duck:
        raise ValueError("Ducking needs distinct key and target roles that exist in the mix")
    labels = list(groups.values())
    if len(labels) == 1:
        filters.append(f"[{labels[0]}]alimiter=limit=0.95:level=0[amix]")
    else:
        filters.append("".join(f"[{x}]" for x in labels) + f"amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.95:level=0[amix]")
    return filters, "amix"
