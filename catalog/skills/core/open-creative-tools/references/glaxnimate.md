# Glaxnimate 0.6 (After Effects + Bodymovin alternative for vector motion)

- One exe for GUI and CLI. Licence GPL-3.0 (KDE). Bundles Python modules lottie and Pillow.
- Packaging bug seen on a Windows standalone archive: the embedded Python stdlib lacked its `.py` files and every
  import/export crashed (0xC0000409). Fix: fill the missing stdlib files from the matching official CPython source
  release. Re-extracting the archive undoes the fix — note it next to the install.

## Verified (Glaxnimate 0.6.0, Windows; all exit 0, < 3 s)
```
glaxnimate --version
glaxnimate --export-format-list
glaxnimate in.svg -o out.json                # SVG -> Lottie (format from extension)
glaxnimate out.json -o out.svg               # Lottie -> SVG
glaxnimate out.json -r frame.png --frame 0   # render one frame to PNG
glaxnimate in.svg -o out.tgs                 # Telegram sticker
```
Export formats: glaxnimate, lottie, tgs, rive, svg, avd, video, gif, webp, dotlottie, spritesheet
(`-f <format>` forces one; only the commands above were run).

## Caveats
- TGS export warns unless the canvas is 512×512 and ≤ 3 s / 60 fps; fix the source size first for real stickers.
