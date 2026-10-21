# Deterministic layer specification

Use `scripts/compose_layers.py` for rapid block compositions, repeatable raster variants, and proofs. Keep production logos/type vector in Illustrator or PDF when appropriate.

## Example

```json
{
  "canvas": {"width": 1800, "height": 900, "background": "#4438E8"},
  "proof_safe_margin": 0.06,
  "layers": [
    {
      "name": "brand gradient",
      "type": "gradient",
      "x": 0, "y": 0, "width": 1800, "height": 900,
      "start": "#4137E8", "end": "#8A69FF", "direction": "horizontal"
    },
    {
      "name": "quiet panel",
      "type": "rectangle",
      "x": 150, "y": 160, "width": 700, "height": 500,
      "fill": "#FFFFFF18", "radius": 40
    },
    {
      "name": "city",
      "type": "image", "path": "city.png",
      "x": 0, "y": 900, "anchor": "bottom-left",
      "width": 1800, "height": 520, "fit": "cover",
      "focal_x": 0.5, "focal_y": 1.0, "opacity": 0.95
    },
    {
      "name": "trajectory",
      "type": "line", "points": [[80, 650], [500, 300], [1150, 480], [1700, 140]],
      "color": "#FFFFFFA0", "width": 8
    },
    {
      "name": "headline",
      "type": "text", "text": "КОНСУЛЬТАЦИОННАЯ ЗОНА",
      "font": "font.ttf", "size": 86, "max_width": 700,
      "x": 180, "y": 210, "color": "#FFFFFFFF", "spacing": 14
    }
  ]
}
```

## Layer types

- `image`: `path`, optional `width`, `height`, `fit` (`contain`, `cover`, `stretch`), `focal_x`, `focal_y`, `opacity`, `rotation`, `flip_x`, `flip_y`, and grayscale `mask`.
- `text`: `text`, `font`, `size`, optional `max_width`, `spacing`, `align`, `color`, stroke, and anchor.
- `rectangle` / `ellipse`: position, size, `fill`, optional `outline`, `outline_width`, and rectangle `radius`.
- `line`: list of `points`, `color`, and `width`.
- `gradient`: position/size, `start`, `end`, `direction` (`horizontal` or `vertical`), and `opacity`.

All layers are drawn in array order. Set `visible` to `false` to preserve a disabled variant. Use `name` for readability; it does not affect rendering.

## Proof outputs

```powershell
python compose_layers.py --spec layout.json --output final.png `
  --proof safe-area.jpg --thumbnail thumbnail.jpg `
  --grayscale-proof grayscale.jpg --overwrite
```

- `--proof` adds safe-area and thirds guides.
- `--thumbnail` exports a clean small hierarchy check.
- `--grayscale-proof` removes color to expose contrast and focal-order problems.
