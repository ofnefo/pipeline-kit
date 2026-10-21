#!/usr/bin/env python3
"""Compose deterministic image/text layers from a JSON spec and make a proof."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageFont, ImageOps


ANCHORS = {
    "top-left": (0.0, 0.0),
    "top-center": (0.5, 0.0),
    "top-right": (1.0, 0.0),
    "center-left": (0.0, 0.5),
    "center": (0.5, 0.5),
    "center-right": (1.0, 0.5),
    "bottom-left": (0.0, 1.0),
    "bottom-center": (0.5, 1.0),
    "bottom-right": (1.0, 1.0),
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--proof", type=Path)
    p.add_argument("--thumbnail", type=Path, help="Clean hierarchy thumbnail without guides")
    p.add_argument("--grayscale-proof", type=Path, help="Clean grayscale hierarchy proof")
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args()


def rgba(value: str) -> tuple[int, int, int, int]:
    color = ImageColor.getcolor(value, "RGBA")
    return tuple(color)


def anchored_xy(x: float, y: float, w: int, h: int, anchor: str) -> tuple[int, int]:
    ax, ay = ANCHORS.get(anchor, ANCHORS["top-left"])
    return round(x - w * ax), round(y - h * ay)


def fit_image(
    image: Image.Image,
    width: int,
    height: int,
    fit: str,
    centering: tuple[float, float] = (0.5, 0.5),
) -> Image.Image:
    if fit == "stretch":
        return image.resize((width, height), Image.Resampling.LANCZOS)
    if fit == "cover":
        return ImageOps.fit(image, (width, height), method=Image.Resampling.LANCZOS, centering=centering)
    if fit == "contain":
        copy = image.copy()
        copy.thumbnail((width, height), Image.Resampling.LANCZOS)
        return copy
    raise ValueError(f"Unknown fit: {fit}")


def fit_mask(
    mask: Image.Image,
    width: int,
    height: int,
    fit: str,
    centering: tuple[float, float] = (0.5, 0.5),
) -> Image.Image:
    fitted = fit_image(mask, width, height, fit, centering)
    if fitted.size == (width, height):
        return fitted
    canvas = Image.new("L", (width, height), 0)
    x = round((width - fitted.width) * centering[0])
    y = round((height - fitted.height) * centering[1])
    canvas.paste(fitted, (x, y))
    return canvas


def add_image(base: Image.Image, layer: dict, root: Path) -> None:
    path = (root / layer["path"]).resolve() if not Path(layer["path"]).is_absolute() else Path(layer["path"])
    image = Image.open(path).convert("RGBA")
    width = int(layer.get("width", image.width))
    height = int(layer.get("height", image.height))
    centering = (float(layer.get("focal_x", 0.5)), float(layer.get("focal_y", 0.5)))
    if not (0 <= centering[0] <= 1 and 0 <= centering[1] <= 1):
        raise ValueError("focal_x and focal_y must be between 0 and 1")
    image = fit_image(image, width, height, layer.get("fit", "contain"), centering)
    if layer.get("flip_x"):
        image = ImageOps.mirror(image)
    if layer.get("flip_y"):
        image = ImageOps.flip(image)
    rotation = float(layer.get("rotation", 0))
    if rotation:
        image = image.rotate(-rotation, resample=Image.Resampling.BICUBIC, expand=True)
    if layer.get("mask"):
        mask_path = Path(layer["mask"])
        if not mask_path.is_absolute():
            mask_path = (root / mask_path).resolve()
        mask = Image.open(mask_path).convert("L")
        mask = fit_mask(mask, image.width, image.height, layer.get("mask_fit", "cover"), centering)
        image.putalpha(ImageChops.multiply(image.getchannel("A"), mask))
    opacity = float(layer.get("opacity", 1.0))
    if opacity < 1:
        alpha = image.getchannel("A").point(lambda v: round(v * opacity))
        image.putalpha(alpha)
    x, y = anchored_xy(float(layer.get("x", 0)), float(layer.get("y", 0)), image.width, image.height, layer.get("anchor", "top-left"))
    base.alpha_composite(image, (x, y))


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    paragraphs: list[str] = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        if not words:
            paragraphs.append("")
            continue
        lines = [words[0]]
        for word in words[1:]:
            candidate = f"{lines[-1]} {word}"
            if draw.textlength(candidate, font=font) <= max_width:
                lines[-1] = candidate
            else:
                lines.append(word)
        paragraphs.append("\n".join(lines))
    return "\n".join(paragraphs)


def add_text(base: Image.Image, layer: dict, root: Path) -> None:
    draw = ImageDraw.Draw(base)
    font_path = Path(layer["font"])
    if not font_path.is_absolute():
        font_path = (root / font_path).resolve()
    font = ImageFont.truetype(str(font_path), int(layer["size"]))
    text = str(layer["text"])
    if layer.get("max_width"):
        text = wrap_text(draw, text, font, int(layer["max_width"]))
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=int(layer.get("spacing", 4)), align=layer.get("align", "left"), stroke_width=int(layer.get("stroke_width", 0)))
    width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = anchored_xy(float(layer.get("x", 0)), float(layer.get("y", 0)), width, height, layer.get("anchor", "top-left"))
    draw.multiline_text(
        (x - bbox[0], y - bbox[1]),
        text,
        font=font,
        fill=rgba(layer.get("color", "#FFFFFFFF")),
        spacing=int(layer.get("spacing", 4)),
        align=layer.get("align", "left"),
        stroke_width=int(layer.get("stroke_width", 0)),
        stroke_fill=rgba(layer.get("stroke_color", "#00000000")),
    )


def local_box(layer: dict) -> tuple[int, int, int, int]:
    width = int(layer["width"])
    height = int(layer["height"])
    x, y = anchored_xy(float(layer.get("x", 0)), float(layer.get("y", 0)), width, height, layer.get("anchor", "top-left"))
    return x, y, x + width, y + height


def add_shape(base: Image.Image, layer: dict, kind: str) -> None:
    draw = ImageDraw.Draw(base)
    fill = rgba(layer.get("fill", "#00000000"))
    outline = rgba(layer.get("outline", "#00000000"))
    width = int(layer.get("outline_width", 0))
    box = local_box(layer)
    if kind == "rectangle":
        radius = int(layer.get("radius", 0))
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline if width else None, width=width)
    elif kind == "ellipse":
        draw.ellipse(box, fill=fill, outline=outline if width else None, width=width)
    else:
        raise ValueError(f"Unknown shape: {kind}")


def add_line(base: Image.Image, layer: dict) -> None:
    draw = ImageDraw.Draw(base)
    points = [(round(float(point[0])), round(float(point[1]))) for point in layer["points"]]
    if len(points) < 2:
        raise ValueError("line layer needs at least two points")
    draw.line(points, fill=rgba(layer.get("color", "#FFFFFFFF")), width=int(layer.get("width", 1)), joint=layer.get("joint", "curve"))


def add_gradient(base: Image.Image, layer: dict) -> None:
    x, y, right, bottom = local_box(layer)
    width, height = right - x, bottom - y
    start = rgba(layer["start"])
    end = rgba(layer["end"])
    direction = layer.get("direction", "horizontal")
    length = width if direction == "horizontal" else height
    strip = Image.new("RGBA", (length, 1))
    pixels = []
    divisor = max(1, length - 1)
    for index in range(length):
        fraction = index / divisor
        pixels.append(tuple(round(start[channel] * (1 - fraction) + end[channel] * fraction) for channel in range(4)))
    strip.putdata(pixels)
    if direction == "horizontal":
        gradient = strip.resize((width, height))
    elif direction == "vertical":
        gradient = strip.transpose(Image.Transpose.ROTATE_90).resize((width, height))
    else:
        raise ValueError("gradient direction must be horizontal or vertical")
    opacity = float(layer.get("opacity", 1.0))
    if opacity < 1:
        gradient.putalpha(gradient.getchannel("A").point(lambda value: round(value * opacity)))
    base.alpha_composite(gradient, (x, y))


def make_proof(image: Image.Image, output: Path, safe_margin: float = 0.05) -> None:
    proof = image.convert("RGB")
    proof.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(proof)
    margin_x, margin_y = round(proof.width * safe_margin), round(proof.height * safe_margin)
    draw.rectangle((margin_x, margin_y, proof.width - margin_x, proof.height - margin_y), outline=(20, 206, 117), width=max(1, proof.width // 600))
    draw.line((proof.width / 3, 0, proof.width / 3, proof.height), fill=(255, 255, 255), width=1)
    draw.line((proof.width * 2 / 3, 0, proof.width * 2 / 3, proof.height), fill=(255, 255, 255), width=1)
    draw.line((0, proof.height / 3, proof.width, proof.height / 3), fill=(255, 255, 255), width=1)
    draw.line((0, proof.height * 2 / 3, proof.width, proof.height * 2 / 3), fill=(255, 255, 255), width=1)
    output.parent.mkdir(parents=True, exist_ok=True)
    proof.save(output, quality=92)


def make_clean_proof(image: Image.Image, output: Path, maximum: int = 800, grayscale: bool = False) -> None:
    proof = image.convert("RGB")
    proof.thumbnail((maximum, maximum), Image.Resampling.LANCZOS)
    if grayscale:
        proof = ImageOps.grayscale(proof)
    output.parent.mkdir(parents=True, exist_ok=True)
    proof.save(output, quality=92)


def main() -> int:
    args = parse_args()
    destinations = [args.output, args.proof, args.thumbnail, args.grayscale_proof]
    collisions = [path for path in destinations if path and path.exists()]
    if collisions and not args.overwrite:
        joined = ", ".join(str(path) for path in collisions)
        raise FileExistsError(f"Output exists; pass --overwrite: {joined}")
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    root = args.spec.parent
    canvas = spec["canvas"]
    base = Image.new("RGBA", (int(canvas["width"]), int(canvas["height"])), rgba(canvas.get("background", "#00000000")))
    for layer in spec.get("layers", []):
        if layer.get("visible", True) is False:
            continue
        kind = layer.get("type", "image")
        if kind == "image":
            add_image(base, layer, root)
        elif kind == "text":
            add_text(base, layer, root)
        elif kind in {"rectangle", "ellipse"}:
            add_shape(base, layer, kind)
        elif kind == "line":
            add_line(base, layer)
        elif kind == "gradient":
            add_gradient(base, layer)
        else:
            raise ValueError(f"Unknown layer type: {kind}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    base.save(args.output)
    if args.proof:
        make_proof(base, args.proof, float(spec.get("proof_safe_margin", 0.05)))
    if args.thumbnail:
        make_clean_proof(base, args.thumbnail, int(spec.get("thumbnail_maximum", 320)))
    if args.grayscale_proof:
        make_clean_proof(base, args.grayscale_proof, int(spec.get("grayscale_maximum", 1000)), grayscale=True)
    print(json.dumps({"output": str(args.output.resolve()), "size": list(base.size), "layers": len(spec.get("layers", []))}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
