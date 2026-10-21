#!/usr/bin/env python3
"""Create a labeled contact sheet for rapid visual asset review."""

from __future__ import annotations

import argparse
from math import ceil
import os
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError


EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp", ".gif", ".psd"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--thumb-width", type=int, default=360)
    parser.add_argument("--thumb-height", type=int, default=240)
    parser.add_argument("--background", default="#202228")
    parser.add_argument("--checkerboard", action="store_true", help="Show transparency over checkerboard")
    parser.add_argument("--font", type=Path, help="Optional TrueType/OpenType font for labels")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def discover(paths: list[Path], recursive: bool) -> list[Path]:
    files: set[Path] = set()
    for raw in paths:
        path = raw.resolve()
        if path.is_file() and path.suffix.lower() in EXTENSIONS:
            files.add(path)
        elif path.is_dir():
            iterator = path.rglob("*") if recursive else path.glob("*")
            files.update(item.resolve() for item in iterator if item.is_file() and item.suffix.lower() in EXTENSIONS)
    return sorted(files, key=lambda value: str(value).casefold())


def font(size: int, explicit: Path | None = None) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates: list[Path] = []
    if explicit:
        candidates.append(explicit)
    windows_root = os.environ.get("WINDIR")
    if windows_root:
        candidates.extend(Path(windows_root, "Fonts", name) for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"))
    candidates.extend(
        [
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/Library/Fonts/Arial.ttf"),
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def checkerboard(width: int, height: int, cell: int = 16) -> Image.Image:
    board = Image.new("RGBA", (width, height), "#D8D8D8")
    draw = ImageDraw.Draw(board)
    for y in range(0, height, cell):
        for x in range(0, width, cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill="#F2F2F2")
    return board


def shorten(draw: ImageDraw.ImageDraw, value: str, maximum_width: int, typeface: ImageFont.ImageFont) -> str:
    if draw.textlength(value, font=typeface) <= maximum_width:
        return value
    suffix = "…"
    text = value
    while text and draw.textlength(text + suffix, font=typeface) > maximum_width:
        text = text[:-1]
    return text + suffix


def main() -> int:
    args = parse_args()
    if args.columns < 1 or args.thumb_width < 32 or args.thumb_height < 32:
        raise ValueError("columns and thumbnail dimensions must be positive")
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f"Output exists; pass --overwrite: {args.output}")
    files = discover(args.paths, args.recursive)
    if not files:
        raise FileNotFoundError("No supported raster files found")

    padding = 18
    caption_height = 64
    cell_width = args.thumb_width + padding * 2
    cell_height = args.thumb_height + caption_height + padding * 2
    rows = ceil(len(files) / args.columns)
    sheet = Image.new("RGB", (cell_width * args.columns, cell_height * rows), ImageColor.getrgb(args.background))
    draw = ImageDraw.Draw(sheet)
    label_font = font(18, args.font)
    meta_font = font(14, args.font)

    for index, path in enumerate(files):
        column = index % args.columns
        row = index // args.columns
        origin_x = column * cell_width + padding
        origin_y = row * cell_height + padding
        try:
            with Image.open(path) as opened:
                source = ImageOps.exif_transpose(opened).convert("RGBA")
                original_size = source.size
                source.thumbnail((args.thumb_width, args.thumb_height), Image.Resampling.LANCZOS)
                frame = checkerboard(args.thumb_width, args.thumb_height) if args.checkerboard else Image.new("RGBA", (args.thumb_width, args.thumb_height), "#FFFFFF")
                paste_x = (args.thumb_width - source.width) // 2
                paste_y = (args.thumb_height - source.height) // 2
                frame.alpha_composite(source, (paste_x, paste_y))
                sheet.paste(frame.convert("RGB"), (origin_x, origin_y))
                title = shorten(draw, path.name, args.thumb_width, label_font)
                draw.text((origin_x, origin_y + args.thumb_height + 10), title, fill="#FFFFFF", font=label_font)
                meta = f"{original_size[0]}×{original_size[1]} · {opened.mode} · {path.suffix.lower()[1:]}"
                draw.text((origin_x, origin_y + args.thumb_height + 36), meta, fill="#B8BCC7", font=meta_font)
        except (UnidentifiedImageError, OSError) as error:
            draw.rectangle((origin_x, origin_y, origin_x + args.thumb_width, origin_y + args.thumb_height), fill="#642F38")
            draw.text((origin_x + 12, origin_y + 12), "Cannot preview", fill="#FFFFFF", font=label_font)
            draw.text((origin_x, origin_y + args.thumb_height + 10), shorten(draw, path.name, args.thumb_width, label_font), fill="#FFFFFF", font=label_font)
            draw.text((origin_x, origin_y + args.thumb_height + 36), shorten(draw, str(error), args.thumb_width, meta_font), fill="#FFBAC6", font=meta_font)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output, quality=92)
    print(str(args.output.resolve()).encode("ascii", "backslashreplace").decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
