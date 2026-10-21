# GIMP 3.x (Photoshop alternative for batch raster work)

- Headless exe: `gimp-console-3` (on Windows `gimp-console-3.exe` in the GIMP `bin` folder); GUI `gimp-3`.

## Verified (GIMP 3.2, Windows)
Python-Fu (exit 0, ~46 s including the first-start plug-in scan):
```
gimp-console-3 -i --batch-interpreter=python-fu-eval -b "from gi.repository import Gimp, Gio; img = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, Gio.File.new_for_path('/path/in.png')); img.scale(64, 64); img.flatten(); Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, Gio.File.new_for_path('/path/out.jpg'), None); img.delete()" --quit
```
Script-Fu (exit 0, ~7 s):
```
gimp-console-3 -i --batch-interpreter=plug-in-script-fu-eval -b "(let* ((img (car (gimp-file-load RUN-NONINTERACTIVE \"/path/in.png\")))) (gimp-image-scale img 32 32) (gimp-file-save RUN-NONINTERACTIVE img \"/path/out.png\" -1) (gimp-image-delete img))" --quit
```

## Failure seen
- Without `--batch-interpreter=...` GIMP 3 does not run the batch: it hung until a 300 s timeout. Always pass it.

## Caveats
- The GIMP 3 API differs from 2.10 (`Gimp.file_load` takes a `Gio.File`; Script-Fu `gimp-file-save` has no raw-filename argument).
- Always end with `--quit`; for many files loop inside one `-b` call instead of starting GIMP per file.
