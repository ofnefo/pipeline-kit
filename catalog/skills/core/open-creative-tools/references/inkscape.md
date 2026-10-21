# Inkscape 1.4 (Illustrator alternative)

## Verified (Inkscape 1.4.4, Windows; all exit 0, ~2.5 s each)
```
inkscape --version
inkscape in.svg --export-type=png --export-filename=out.png -w 256
inkscape in.svg --export-type=pdf --export-text-to-path --export-filename=out.pdf
inkscape in.svg "--actions=select-by-id:dot;object-to-path;object-set-property:fill,#ff0055;export-filename:out.svg;export-plain-svg;export-do"
```
The last one was checked: the circle `dot` became a path with `fill:#ff0055`.

## Caveats
- `object-set-attribute:fill,...` is overridden by an existing `style` attribute — use `object-set-property`.
- List all actions: `inkscape --action-list`.
- Print CMYK/bleed is not Inkscape's strength; final print files need a preflight in a CMYK-capable tool.
