#!/usr/bin/env python3
"""Inventory raster and vector design assets into a machine-readable report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageOps, UnidentifiedImageError


RASTER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp", ".gif", ".psd"}
VECTOR_EXTENSIONS = {".ai", ".eps", ".svg", ".pdf"}
FONT_EXTENSIONS = {".otf", ".ttf", ".woff", ".woff2"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Files or folders to inspect")
    parser.add_argument("--output", type=Path, help="Write JSON report to this path")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing JSON report")
    parser.add_argument("--recursive", action="store_true", help="Recurse into directories")
    parser.add_argument(
        "--relative-to",
        type=Path,
        help="Store paths relative to this directory so saved reports survive workspace moves",
    )
    parser.add_argument("--min-long-edge", type=int, default=1200, help="Warn below this raster long edge")
    return parser.parse_args()


def discover(paths: list[Path], recursive: bool) -> list[Path]:
    files: set[Path] = set()
    for raw in paths:
        path = raw.resolve()
        if path.is_file():
            files.add(path)
        elif path.is_dir():
            iterator = path.rglob("*") if recursive else path.glob("*")
            files.update(item.resolve() for item in iterator if item.is_file())
        else:
            raise FileNotFoundError(raw)
    return sorted(files, key=lambda value: str(value).casefold())


def alpha_summary(image: Image.Image) -> dict | None:
    if "A" not in image.getbands() and "transparency" not in image.info:
        return None
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    extrema = alpha.getextrema()
    histogram = alpha.histogram()
    pixels = max(1, image.width * image.height)
    return {
        "minimum": extrema[0],
        "maximum": extrema[1],
        "transparent_fraction": round(histogram[0] / pixels, 6),
        "partial_fraction": round(sum(histogram[1:255]) / pixels, 6),
        "opaque_fraction": round(histogram[255] / pixels, 6),
    }


def inspect_raster(path: Path, min_long_edge: int) -> dict:
    warnings: list[str] = []
    try:
        with Image.open(path) as opened:
            image = ImageOps.exif_transpose(opened)
            width, height = image.size
            dpi = image.info.get("dpi")
            dpi_pair = None
            if dpi and len(dpi) >= 2:
                dpi_pair = [round(float(dpi[0]), 3), round(float(dpi[1]), 3)]
            if max(width, height) < min_long_edge:
                warnings.append(f"raster long edge below {min_long_edge}px")
            if width * height < 1_000_000:
                warnings.append("raster below 1 megapixel")
            if path.suffix.lower() in {".jpg", ".jpeg"} and image.mode == "CMYK":
                warnings.append("CMYK JPEG: verify profile and conversion in authoring app")
            if "icc_profile" not in image.info:
                warnings.append("no embedded ICC profile detected")
            return {
                "kind": "raster",
                "width": width,
                "height": height,
                "megapixels": round(width * height / 1_000_000, 3),
                "mode": image.mode,
                "bands": list(image.getbands()),
                "dpi": dpi_pair,
                "has_icc_profile": bool(image.info.get("icc_profile")),
                "alpha": alpha_summary(image),
                "frames": getattr(opened, "n_frames", 1),
                "warnings": warnings,
            }
    except (UnidentifiedImageError, OSError) as error:
        return {"kind": "raster", "error": str(error), "warnings": ["could not decode raster"]}


def report_path(path: Path, relative_to: Path | None) -> tuple[str, bool]:
    if relative_to is None:
        return str(path), False
    try:
        return path.relative_to(relative_to).as_posix(), True
    except ValueError:
        return str(path), False


def inspect_file(path: Path, min_long_edge: int, relative_to: Path | None = None) -> dict:
    extension = path.suffix.lower()
    display_path, is_relative = report_path(path, relative_to)
    record = {
        "path": display_path,
        "path_is_relative": is_relative,
        "name": path.name,
        "extension": extension,
        "bytes": path.stat().st_size,
    }
    if extension in RASTER_EXTENSIONS:
        record.update(inspect_raster(path, min_long_edge))
    elif extension in VECTOR_EXTENSIONS:
        record.update({"kind": "vector_or_document", "warnings": ["inspect visually in native/PDF application"]})
    elif extension in FONT_EXTENSIONS:
        record.update({"kind": "font", "warnings": []})
    else:
        record.update({"kind": "other", "warnings": []})
    return record


def main() -> int:
    args = parse_args()
    if args.output and args.output.exists() and not args.overwrite:
        raise FileExistsError(f"Output exists; pass --overwrite: {args.output}")
    files = discover(args.paths, args.recursive)
    relative_to = args.relative_to.resolve() if args.relative_to else None
    if relative_to and not relative_to.is_dir():
        raise NotADirectoryError(relative_to)
    records = [inspect_file(path, args.min_long_edge, relative_to) for path in files]
    summary: dict[str, int] = {}
    for record in records:
        kind = str(record["kind"])
        summary[kind] = summary.get(kind, 0) + 1
    report = {
        "path_mode": "relative" if relative_to else "absolute",
        "files": records,
        "summary": summary,
        "count": len(records),
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
