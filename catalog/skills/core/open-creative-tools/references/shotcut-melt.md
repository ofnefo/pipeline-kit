# Shotcut / MLT melt 7.x (Premiere alternative)

- GUI: `shotcut`; headless engine: `melt` in the same folder (with a bundled `ffmpeg`).
- Shotcut projects (`.mlt`) render headless with melt.

## Verified (melt 7.41, Windows)
- `melt -version` → exit 0.
- Still image + watermark overlay → H.264 (exit 0, ~1 s):
```
melt /path/in.png out=47 -filter watermark:/path/overlay.png -consumer avformat:/path/out.mp4 vcodec=libx264 an=1 width=256 height=256 frame_rate_num=24
```

## Not verified
- Rendering a saved Shotcut project: `melt project.mlt -consumer avformat:out.mp4 ...` (standard MLT usage).

## Caveats
- Probing, transcodes and proxies are FFmpeg's job; use melt when an MLT/Shotcut timeline exists.
