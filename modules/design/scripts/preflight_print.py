#!/usr/bin/env python3
"""Check a raster asset against final physical print dimensions and target PPI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError


MM_PER_INCH = 25.4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--width-mm", required=True, type=float, help="Final full-scale placed width")
    parser.add_argument("--height-mm", required=True, type=float, help="Final full-scale placed height")
    parser.add_argument("--target-ppi", type=float, default=100.0)
    parser.add_argument(
        "--aspect-tolerance-pct",
        type=float,
        default=1.0,
        help="Maximum pixel-to-physical aspect-ratio mismatch before blocking",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON report")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing JSON report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        raise FileNotFoundError(args.input)
    if min(args.width_mm, args.height_mm, args.target_ppi) <= 0 or args.aspect_tolerance_pct < 0:
        raise ValueError("physical dimensions and target PPI must be positive; aspect tolerance cannot be negative")
    if args.output and args.output.exists() and not args.overwrite:
        raise FileExistsError(f"Output exists; pass --overwrite: {args.output}")
    try:
        with Image.open(args.input) as opened:
            raw_pixel_width, raw_pixel_height = opened.size
            exif_orientation = opened.getexif().get(274)
            image = ImageOps.exif_transpose(opened)
            pixel_width, pixel_height = image.size
            mode = image.mode
            has_icc = bool(image.info.get("icc_profile"))
            has_alpha = "A" in image.getbands() or "transparency" in image.info
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError(f"Could not decode raster: {error}") from error

    width_inches = args.width_mm / MM_PER_INCH
    height_inches = args.height_mm / MM_PER_INCH
    ppi_x = pixel_width / width_inches
    ppi_y = pixel_height / height_inches
    limiting_ppi = min(ppi_x, ppi_y)
    required_width = round(width_inches * args.target_ppi)
    required_height = round(height_inches * args.target_ppi)
    scale_needed = max(required_width / pixel_width, required_height / pixel_height)
    pixel_aspect_ratio = pixel_width / pixel_height
    physical_aspect_ratio = args.width_mm / args.height_mm
    aspect_ratio_mismatch_pct = (max(pixel_aspect_ratio / physical_aspect_ratio, physical_aspect_ratio / pixel_aspect_ratio) - 1) * 100
    blocking_issues: list[str] = []
    conditions: list[str] = []
    if aspect_ratio_mismatch_pct > args.aspect_tolerance_pct:
        blocking_issues.append(
            f"aspect ratio differs by {aspect_ratio_mismatch_pct:.2f}% and requires an explicit crop or layout correction"
        )
    if limiting_ppi < args.target_ppi:
        message = f"effective PPI below target by {args.target_ppi - limiting_ppi:.1f}"
        if limiting_ppi < args.target_ppi * 0.5:
            blocking_issues.append(message)
        else:
            conditions.append(message)
    if scale_needed > 1.5:
        conditions.append(f"requires {scale_needed:.2f}× linear enlargement to meet target")
    if not has_icc:
        conditions.append("no embedded ICC profile detected")
    if mode not in {"RGB", "RGBA", "CMYK", "L", "LA"}:
        conditions.append(f"unusual raster mode: {mode}")
    orientation_applied = exif_orientation not in {None, 1}
    if orientation_applied:
        conditions.append(
            f"EXIF orientation {exif_orientation} was applied for analysis; flatten and verify orientation before handoff"
        )

    if blocking_issues:
        status = "BLOCKED"
    elif conditions:
        status = "PASS_WITH_CONDITIONS"
    else:
        status = "PASS"

    report = {
        "input": str(args.input.resolve()),
        "pixels": [pixel_width, pixel_height],
        "raw_pixels": [raw_pixel_width, raw_pixel_height],
        "exif_orientation": exif_orientation,
        "orientation_applied": orientation_applied,
        "final_mm": [args.width_mm, args.height_mm],
        "pixel_aspect_ratio": round(pixel_aspect_ratio, 6),
        "physical_aspect_ratio": round(physical_aspect_ratio, 6),
        "aspect_ratio_mismatch_pct": round(aspect_ratio_mismatch_pct, 3),
        "aspect_tolerance_pct": args.aspect_tolerance_pct,
        "effective_ppi": [round(ppi_x, 2), round(ppi_y, 2)],
        "limiting_ppi": round(limiting_ppi, 2),
        "target_ppi": args.target_ppi,
        "required_pixels": [required_width, required_height],
        "linear_scale_needed": round(scale_needed, 3),
        "mode": mode,
        "has_alpha": has_alpha,
        "has_icc_profile": has_icc,
        "status": status,
        "blocking_issues": blocking_issues,
        "conditions": conditions,
        "warnings": blocking_issues + conditions,
        "scope_note": "Raster-only technical screen; this result is not production approval. Verify crop/placement, fonts, links, profiles, spots, overprint, transparency, bleed, and PDF standard in the authoring application and with the vendor.",
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 1 if status == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
