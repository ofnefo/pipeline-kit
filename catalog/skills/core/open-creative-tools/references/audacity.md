# Audacity / REAPER (Audition alternative)

## Not verified
- No headless recipe was run. Audacity has no batch CLI; its mod-script-pipe scripting needs the GUI running.
- For deterministic batch audio (normalise, trim, convert, loudness) use FFmpeg, e.g.
  `ffmpeg -i in.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 48000 -ac 2 out.wav`, plus `atrim`, `-ar`, `-ac`.
- REAPER can render projects from the command line (`reaper -renderproject project.rpp`) — not verified here.
