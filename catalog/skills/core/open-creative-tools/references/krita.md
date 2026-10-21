# Krita 5.x (Photoshop alternative for painting)

- Exe: `krita` (on Windows `krita.exe` in the Krita `bin` folder); scripting runner `kritarunner` in the same folder.

## Verified (Krita 5.3, Windows)
- `krita --version` → exit 0.
- `krita /path/in.png --export --export-filename /path/out.jpg` → exit 0, ~52 s (slow start; fontconfig warnings on
  stderr are harmless). Use for format conversion / flattening `.kra` and `.psd` to PNG/JPG; no edits in this mode.

## Not verified
- `kritarunner -s <script>` (Python scripting without GUI).
- `--export-sequence` for animation frames.

## Caveats
- Heavy app (~50 s start): batch many files through one scripted session rather than one launch per file, and take a
  resource snapshot first.
