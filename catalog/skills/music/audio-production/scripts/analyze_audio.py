"""Measure one audio file without modifying it: BPM/key hypotheses, LUFS, sample and true peak, silence,
beat grid, transient cue candidates, loop seam, spectral statistics and a waveform envelope (JSON report).

Needs numpy, librosa, soundfile, pyloudnorm; FFmpeg/FFprobe on PATH (or FFMPEG / FFPROBE env vars) for true
peak and probe data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("NUMBA_CACHE_DIR", str(Path(tempfile.gettempdir()) / "audio-analysis-numba-cache"))

librosa = np = pyln = sf = None  # heavy dependencies are imported in main() so --help works without them

PITCHES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
MAJOR = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)  # Krumhansl-Kessler
MINOR = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def db(value: float) -> float:
    return float(20 * np.log10(max(value, 1e-12)))


def key_candidates(chroma: np.ndarray) -> list[dict]:
    profile = chroma.mean(axis=1)
    profile = (profile - profile.mean()) / (profile.std() + 1e-9)
    scores = []
    for root in range(12):
        for mode, template in (("major", np.array(MAJOR)), ("minor", np.array(MINOR))):
            candidate = np.roll((template - template.mean()) / template.std(), root)
            scores.append({"key": f"{PITCHES[root]} {mode}", "score": float(np.dot(profile, candidate) / 12)})
    return sorted(scores, key=lambda item: item["score"], reverse=True)[:3]


def find_binary(name: str) -> str | None:
    configured = os.environ.get(name.upper())
    candidates = [configured, shutil.which(name)]
    return next((str(path) for path in candidates if path and Path(path).is_file()), None)


def probe(source: Path) -> dict | None:
    executable = find_binary("ffprobe")
    if not executable:
        return None
    completed = subprocess.run(
        [executable, "-v", "error", "-select_streams", "a:0", "-show_format", "-show_streams", "-of", "json", str(source)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    if completed.returncode:
        return {"error": completed.stderr.strip(), "returncode": completed.returncode}
    return json.loads(completed.stdout)


def true_peak(source: Path) -> dict:
    executable = find_binary("ffmpeg")
    if not executable:
        return {"dbtp": None, "method": "ffmpeg ebur128 peak=true", "error": "ffmpeg not found"}
    completed = subprocess.run(
        [executable, "-hide_banner", "-nostats", "-i", str(source), "-filter_complex", "ebur128=peak=true", "-f", "null", os.devnull],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    matches = re.findall(r"True peak:\s*\n\s*Peak:\s*(-?inf|[-+]?\d+(?:\.\d+)?)\s*dBFS", completed.stderr, flags=re.IGNORECASE)
    if not matches:
        return {"dbtp": None, "method": "ffmpeg ebur128 peak=true", "error": "true-peak summary not parsed"}
    value = matches[-1]
    return {"dbtp": -math.inf if value.lower() == "-inf" else float(value), "method": "ffmpeg ebur128 peak=true"}


def waveform_envelope(mono: np.ndarray, sample_rate: int, points: int) -> dict:
    points = max(16, min(points, len(mono)))
    edges = np.linspace(0, len(mono), points + 1, dtype=int)
    minima, maxima, rms = [], [], []
    for start, end in zip(edges[:-1], edges[1:]):
        window = mono[start:max(start + 1, end)]
        minima.append(round(float(np.min(window)), 6))
        maxima.append(round(float(np.max(window)), 6))
        rms.append(round(float(np.sqrt(np.mean(window * window))), 6))
    return {"points": points, "seconds_per_point": len(mono) / sample_rate / points, "min": minima, "max": maxima, "rms": rms}


def silent_ranges(mono: np.ndarray, sample_rate: int, top_db: float) -> tuple[float, list[dict]]:
    active_intervals = librosa.effects.split(mono, top_db=top_db)
    active = sum(end - start for start, end in active_intervals)
    silent: list[dict] = []
    cursor = 0
    for start, end in active_intervals:
        if start > cursor:
            silent.append({"start": cursor / sample_rate, "end": start / sample_rate, "duration": (start - cursor) / sample_rate})
        cursor = end
    if cursor < len(mono):
        silent.append({"start": cursor / sample_rate, "end": len(mono) / sample_rate, "duration": (len(mono) - cursor) / sample_rate})
    return active / max(1, len(mono)), silent


def cue_candidates(onset_envelope: np.ndarray, sample_rate: int, beat_times: np.ndarray, limit: int) -> list[dict]:
    frames = librosa.onset.onset_detect(onset_envelope=onset_envelope, sr=sample_rate, units="frames", backtrack=False)
    if not len(frames):
        return []
    strengths = onset_envelope[np.minimum(frames, len(onset_envelope) - 1)]
    strongest = np.argsort(strengths)[::-1][: max(1, limit)]
    maximum = max(float(np.max(strengths)), 1e-12)
    cues = []
    for index in strongest:
        time = float(librosa.frames_to_time(frames[index], sr=sample_rate))
        nearest = int(np.argmin(np.abs(beat_times - time))) if len(beat_times) else None
        cues.append({
            "time": time, "kind": "transient_candidate", "strength": float(strengths[index] / maximum),
            "nearest_beat_index": nearest, "nearest_beat_time": float(beat_times[nearest]) if nearest is not None else None,
        })
    return sorted(cues, key=lambda item: item["time"])


def spectral_summary(mono: np.ndarray, sample_rate: int) -> dict:
    spectrum = np.abs(librosa.stft(mono))
    return {
        "centroid_hz_mean": float(np.mean(librosa.feature.spectral_centroid(S=spectrum, sr=sample_rate))),
        "bandwidth_hz_mean": float(np.mean(librosa.feature.spectral_bandwidth(S=spectrum, sr=sample_rate))),
        "rolloff_85_hz_mean": float(np.mean(librosa.feature.spectral_rolloff(S=spectrum, sr=sample_rate, roll_percent=0.85))),
        "flatness_mean": float(np.mean(librosa.feature.spectral_flatness(S=spectrum))),
        "contrast_db_mean": float(np.mean(librosa.feature.spectral_contrast(S=spectrum, sr=sample_rate))),
        "zero_crossing_rate_mean": float(np.mean(librosa.feature.zero_crossing_rate(mono))),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure one audio file without modifying it.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--waveform-points", type=int, default=256)
    parser.add_argument("--max-cues", type=int, default=24)
    parser.add_argument("--silence-top-db", type=float, default=50.0)
    args = parser.parse_args()
    global librosa, np, pyln, sf
    import librosa
    import numpy as np
    import pyloudnorm as pyln
    import soundfile as sf

    source = args.source.resolve()
    audio, sample_rate = sf.read(source, dtype="float32", always_2d=True)
    mono = audio.mean(axis=1)
    onset_envelope = librosa.onset.onset_strength(y=mono, sr=sample_rate)
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset_envelope, sr=sample_rate)
    beat_times = librosa.frames_to_time(beats, sr=sample_rate)
    chroma = librosa.feature.chroma_cqt(y=mono, sr=sample_rate)
    loudness = float(pyln.Meter(sample_rate).integrated_loudness(audio))
    active_ratio, silence = silent_ranges(mono, sample_rate, args.silence_top_db)
    seam = min(sample_rate // 2, len(mono) // 4)
    seam_rms = float(np.sqrt(np.mean((mono[:seam] - mono[-seam:]) ** 2))) if seam else None
    report = {
        "schema_version": 2, "generated_at": datetime.now(timezone.utc).isoformat(), "source": str(source),
        "sha256": sha256(source), "probe": probe(source), "duration": len(audio) / sample_rate,
        "sample_rate": sample_rate, "channels": audio.shape[1], "subtype": sf.info(source).subtype,
        "tempo_bpm": float(np.asarray(tempo).reshape(-1)[0]), "beat_count": int(len(beats)),
        "beat_grid_seconds": [round(float(value), 6) for value in beat_times],
        "cue_points": cue_candidates(onset_envelope, sample_rate, beat_times, args.max_cues),
        "key_candidates": key_candidates(chroma), "integrated_lufs": loudness,
        "sample_peak_dbfs": db(float(np.max(np.abs(audio)))), "true_peak": true_peak(source),
        "active_ratio": active_ratio, "silence_top_db": args.silence_top_db, "silent_ranges": silence,
        "loop_seam_rms": seam_rms, "spectral": spectral_summary(mono, sample_rate),
        "waveform": waveform_envelope(mono, sample_rate, args.waveform_points),
        "notes": [
            "Tempo, grid, cue points and key are estimates; verify halftime, mode, tuning and phrasing by ear.",
            "Cue points are strong transient candidates, not inferred song sections.",
            "True peak is measured by FFmpeg ebur128 with peak=true; sample peak is reported separately.",
        ],
    }
    output = (args.output or source.with_suffix(source.suffix + ".analysis.json")).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
