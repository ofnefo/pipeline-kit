"""Render a loudness-normalised master with FFmpeg only (EBU R128 two-pass loudnorm + optional look-ahead limiter).

  python scripts/master_audio.py MIX.wav --output projects/<slug>/70-master/<name>-master-v001.wav
  python scripts/master_audio.py MIX.wav --output out.wav --profile video --bit-depth 16 --sample-rate 44100
  python scripts/master_audio.py MIX.wav --output out.wav --lufs -14 --true-peak -1 --no-limiter

Pass 1 measures integrated loudness / true peak / LRA (loudnorm print_format=json). When the gain needed to reach
the target would push the true peak over the ceiling, a look-ahead limiter (alimiter, latency-compensated, no
auto-level) is placed before loudnorm so loudnorm can stay in *linear* mode (constant gain, no dynamic AGC); the
chain is re-measured and pass 2 renders with the measured values. The result is measured again and checked
against the target (|I - target| <= 0.5 LU, TP <= ceiling). Without the limiter loudnorm may fall back to its
dynamic mode; the report says which mode was used. Unless --no-limiter, the chain always ends with a final
true-peak stage (4x oversampled alimiter at ceiling - 0.5 dB, then back to the delivery rate) AFTER every gain
stage, so loudnorm's makeup gain can no longer push the true peak over the ceiling (v004 bug, 2026-09-28).

This is a technical loudness/peak master, not a creative mastering chain (no EQ, no multiband, no reference
matching). Stdlib + FFmpeg (existing binary, no new
dependencies). Never overwrites; writes <output>.json (before/after report) and, inside projects/<slug>/,
appends the record to projects/<slug>/renders.jsonl.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_tools import require_binary  # noqa: E402
from music_paths import projects_root  # noqa: E402

ROOT = Path(os.environ.get("PIPELINE_KIT_MUSIC_ROOT", Path(__file__).resolve().parents[1])).resolve()
PROFILES = {
    # name: (integrated LUFS, true-peak dBTP, LRA target)
    "streaming": (-14.0, -1.0, 11.0),  # Spotify/YouTube/Yandex Music reference level
    "apple": (-16.0, -1.0, 11.0),      # Apple Music Sound Check
    "video": (-16.0, -1.0, 11.0),      # online video / social delivery
    "speech": (-16.0, -1.5, 9.0),      # voice-over, podcasts
    "broadcast": (-23.0, -1.0, 15.0),  # EBU R128
    "club": (-9.0, -0.3, 8.0),         # loud club/DJ premaster; the limiter does real work here
}
CHECK_LU, MARGIN_DB = 0.5, 0.5


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_ffmpeg(args: list[str]) -> str:
    completed = subprocess.run([require_binary("ffmpeg"), "-hide_banner", "-nostats", *args], capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip()[-1500:] or "ffmpeg failed")
    return completed.stderr


def last_json(text: str) -> dict:
    blocks = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", text, re.S)
    if not blocks:
        raise RuntimeError("loudnorm JSON not found in FFmpeg output")
    return json.loads(blocks[-1])


def num(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -math.inf


def measure(source: Path, prechain: str, target: tuple[float, float, float]) -> dict:
    i, tp, lra = target
    chain = (prechain + "," if prechain else "") + f"loudnorm=I={i}:TP={tp}:LRA={lra}:print_format=json"
    data = last_json(run_ffmpeg(["-i", str(source), "-af", chain, "-f", "null", "-"]))
    return {"integrated_lufs": num(data["input_i"]), "true_peak_dbtp": num(data["input_tp"]),
            "lra_lu": num(data["input_lra"]), "threshold_lufs": num(data["input_thresh"]), "_raw": data}


def probe_audio(source: Path) -> dict:
    ffprobe = require_binary("ffprobe")
    completed = subprocess.run([ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries",
                                "stream=codec_name,sample_rate,channels,bits_per_raw_sample,bits_per_sample:format=duration",
                                "-of", "json", str(source)], capture_output=True, text=True, encoding="utf-8")
    data = json.loads(completed.stdout or "{}")
    stream = (data.get("streams") or [{}])[0]
    return {"codec": stream.get("codec_name"), "sample_rate": int(stream.get("sample_rate") or 0),
            "channels": stream.get("channels"), "duration_s": round(float((data.get("format") or {}).get("duration") or 0), 3)}


def public(measured: dict) -> dict:
    return {k: (None if isinstance(v, float) and math.isinf(v) else round(v, 2) if isinstance(v, float) else v)
            for k, v in measured.items() if not k.startswith("_")}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True, help=".wav or .flac")
    parser.add_argument("--profile", default="streaming", choices=sorted(PROFILES))
    parser.add_argument("--lufs", type=float, help="override integrated loudness target")
    parser.add_argument("--true-peak", type=float, help="override true-peak ceiling (dBTP)")
    parser.add_argument("--lra", type=float, help="override loudness-range target (LU)")
    parser.add_argument("--no-limiter", action="store_true", help="loudnorm only (may fall back to dynamic mode)")
    parser.add_argument("--attack-ms", type=float, default=5.0)
    parser.add_argument("--release-ms", type=float, default=80.0)
    parser.add_argument("--sample-rate", type=int, default=0, help="output rate; 0 = keep the source rate")
    parser.add_argument("--bit-depth", type=int, default=24, choices=(16, 24, 32))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--note", default="", help="free text recorded in the report/renders.jsonl")
    args = parser.parse_args()

    source, output = args.source.resolve(), args.output.resolve()
    if not source.is_file():
        raise SystemExit(f"Source missing: {source}")
    if output.suffix.lower() not in (".wav", ".flac"):
        raise SystemExit("--output must be .wav or .flac")
    if output == source or (output.exists() and not args.overwrite):
        raise SystemExit(f"Refusing to overwrite {output}; choose a new version path")
    base = PROFILES[args.profile]
    target = (args.lufs if args.lufs is not None else base[0], args.true_peak if args.true_peak is not None else base[1],
              args.lra if args.lra is not None else base[2])
    started = time.perf_counter()
    info = probe_audio(source)
    rate = args.sample_rate or info["sample_rate"] or 48000

    before = measure(source, "", target)
    if math.isinf(before["integrated_lufs"]):
        raise SystemExit("Source is silent (integrated loudness -inf)")
    gain = target[0] - before["integrated_lufs"]
    predicted_tp = before["true_peak_dbtp"] + gain
    prechain, limiter = "", {"enabled": not args.no_limiter, "applied": False, "iterations": []}
    pass1 = before
    if not args.no_limiter and predicted_tp > target[1] - 0.1:
        # Drive gain -> limiter at (ceiling - MARGIN_DB). Limiting costs loudness, so raise the drive until the
        # limited signal sits at the target loudness; loudnorm then only trims a small residual in linear mode.
        limit = min(1.0, 10 ** ((target[1] - MARGIN_DB) / 20))
        drive = gain
        for _ in range(8):
            prechain = (f"volume={drive:.3f}dB,alimiter=limit={limit:.6f}:attack={args.attack_ms}"
                        f":release={args.release_ms}:level=false:latency=true")
            pass1 = measure(source, prechain, target)
            residual = target[0] - pass1["integrated_lufs"]
            predicted = pass1["true_peak_dbtp"] + residual
            limiter["iterations"].append({"drive_db": round(drive, 2), "loudness_lufs": round(pass1["integrated_lufs"], 2),
                                          "true_peak_dbtp": round(pass1["true_peak_dbtp"], 2),
                                          "predicted_tp_after_trim": round(predicted, 2)})
            if predicted <= target[1] - 0.1 and abs(residual) <= 0.3:
                break
            if predicted > target[1] - 0.1 and abs(residual) <= 0.3:
                # inter-sample overs above the sample-peak limiter: lower its ceiling by the excess
                limit = max(0.0625, limit * 10 ** (-(predicted - (target[1] - 0.1) + 0.05) / 20))
            drive += residual
            if drive > gain + 30:
                break
        ceiling = 20 * math.log10(limit)
        limiter.update(applied=True, ceiling_dbfs=round(ceiling, 2), drive_db=round(drive, 2),
                       peak_gain_reduction_db_approx=round(drive + before["true_peak_dbtp"] - ceiling, 2),
                       converged=predicted <= target[1] - 0.1 and abs(residual) <= 0.3)
    raw = pass1["_raw"]
    makeup = target[0] - pass1["integrated_lufs"]
    # loudnorm only stays linear when measured LRA > 0 and <= its LRA target: widen the target to the measured
    # range (constant gain never changes LRA); for LRA == 0 (test tones, drones) apply the measured gain directly.
    lra_used = min(50.0, max(target[2], math.ceil((pass1["lra_lu"] + 0.5) * 10) / 10))
    if pass1["lra_lu"] > 0:
        gain_stage = "loudnorm-linear"
        level = (f"loudnorm=I={target[0]}:TP={target[1]}:LRA={lra_used}:measured_I={raw['input_i']}"
                 f":measured_TP={raw['input_tp']}:measured_LRA={raw['input_lra']}:measured_thresh={raw['input_thresh']}"
                 f":offset={raw['target_offset']}:linear=true:print_format=json")
    else:
        gain_stage, level = "volume (measured gain; loudnorm needs LRA > 0 for linear mode)", f"volume={makeup:.3f}dB"
    # loudnorm can add gain after the first limiter.  Limit the final signal at
    # 4x the delivery rate, then downsample; the margin absorbs residual
    # inter-sample overs introduced by reconstruction/downsampling.
    # Nothing that changes gain may follow it; dither (16-bit) rides on the last resample.
    oversample = 4
    final_limit_db = target[1] - MARGIN_DB
    dither = ":dither_method=triangular_hp" if args.bit_depth == 16 else ""
    final_limiter = (f"aresample={rate * oversample},"
                     f"alimiter=limit={10 ** (final_limit_db / 20):.8f}:attack={args.attack_ms}"
                     f":release={args.release_ms}:level=false:latency=true,"
                     f"aresample={rate}{dither}") if not args.no_limiter else ""
    resample = "" if final_limiter else f"aresample={rate}{dither}"
    chain = ",".join(part for part in (prechain, level, resample, final_limiter) if part)
    codec = {16: "pcm_s16le", 24: "pcm_s24le", 32: "pcm_f32le"}[args.bit_depth] if output.suffix.lower() == ".wav" else "flac"
    extra = ["-sample_fmt", "s16" if args.bit_depth == 16 else "s32"] if codec == "flac" else []
    if codec == "flac" and args.bit_depth == 24:
        extra += ["-bits_per_raw_sample", "24"]
    output.parent.mkdir(parents=True, exist_ok=True)
    render_log = run_ffmpeg(["-y" if args.overwrite else "-n", "-i", str(source), "-af", chain, "-ar", str(rate),
                             "-c:a", codec, *extra, "-map_metadata", "-1", str(output)])
    pass2 = last_json(render_log) if gain_stage == "loudnorm-linear" else {"normalization_type": "linear (volume)"}
    after = measure(output, "", target)
    checks = {
        "integrated_within_0_5_lu": abs(after["integrated_lufs"] - target[0]) <= CHECK_LU,
        "true_peak_under_ceiling": after["true_peak_dbtp"] <= target[1] + 0.05,
        "linear_normalization": str(pass2.get("normalization_type", "")).lower().startswith("linear"),
        "duration_preserved": abs(probe_audio(output)["duration_s"] - info["duration_s"]) <= 0.05,
    }
    record = {
        "schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(), "engine": "ffmpeg loudnorm 2-pass",
        "tool": "scripts/master_audio.py", "profile": args.profile,
        "target": {"integrated_lufs": target[0], "true_peak_dbtp": target[1], "lra_lu": target[2]},
        "source": str(source), "source_sha256": sha256(source), "source_format": info,
        "output": str(output), "output_sha256": sha256(output), "output_format": probe_audio(output),
        "bit_depth": args.bit_depth, "dither": "triangular_hp" if args.bit_depth == 16 else None,
        "before": public(before), "after_limiter_pre_gain": public(pass1) if prechain else None, "after": public(after),
        "makeup_gain_db": round(makeup, 2), "limiter": limiter, "gain_stage": gain_stage,
        "final_true_peak_limiter": {"enabled": not args.no_limiter, "oversample": oversample if not args.no_limiter else None,
                                    "ceiling_dbfs": round(final_limit_db, 2) if not args.no_limiter else None},
        "loudnorm_lra_target_used": lra_used if gain_stage == "loudnorm-linear" else None,
        "loudnorm_normalization_type": pass2.get("normalization_type"), "filter_chain": chain,
        "checks": checks, "status": "pass" if all(checks.values()) else "check",
        "seconds": round(time.perf_counter() - started, 2), "note": args.note,
        "ffmpeg": require_binary("ffmpeg"),
        "scope": "technical loudness/true-peak master; creative mastering (EQ, multiband, reference match) not included",
    }
    output.with_suffix(".json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        projects = projects_root(ROOT)
        relative = output.relative_to(projects)
        ledger = projects / relative.parts[0] / "renders.jsonl"
        if ledger.parent.is_dir() and len(relative.parts) > 1:
            with ledger.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            record["renders_log"] = str(ledger)
    except ValueError:
        pass
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0 if record["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
