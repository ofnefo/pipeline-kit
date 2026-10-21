# darktable 5.x (Lightroom alternative)

- Headless exe: `darktable-cli` (GUI `darktable` in the same folder). Licence GPL-3.0-or-later.
- Install from the official GitHub release and check the published sha256. On Windows the installer registers an
  uninstall entry and shell menus; uninstall via Apps, not by deleting the folder.

## Headless recipe (verified exit 0, darktable 5.6.2, Windows)
```
darktable-cli in.raw [in.raw.xmp] out.jpg --core --configdir <tmp>
```
- **Use forward slashes in paths.** Backslashes are eaten: a backslash path lost all its separators and the export failed.
- `--configdir` pointing to a temp folder keeps runs off the user's library database.
- Look/preset: pass an `.xmp` sidecar exported from a GUI edit, or `--style <name>` (the style must exist in that configdir).
- Size: `--width N --height N`; the format follows the output extension (jpg, png, tif, webp).
