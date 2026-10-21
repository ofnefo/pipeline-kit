# Video-call speaker review (visible labels, not faces)

Most video-call apps (Zoom, Teams, Google Meet, Яндекс Телемост and others) highlight the active participant's tile
with a border and show a name label. That is usable evidence for mapping acoustic clusters to names.

## Steps

1. Transcribe and diarise first (see SKILL.md). Keep the original timeline, including leading silence.
2. **Extract evidence frames.** For each transcript segment, sample frames (1 fps; `--fps 2` for short turns), detect
   the highlighted tile by its border colour (OpenCV), and save crops with timestamps into an evidence folder
   (`visual-evidence.json` + crops). Build 1280 px contact sheets for human review.
3. **Optional OCR of the label strip.** OCR only the caption strip of the active tile (Tesseract `rus+eng` or the OS
   OCR). The result is candidate text, not a verified identity.
4. **Write a speaker map** (`speaker-map-v001.json`):

```json
{
  "evidence_sha256": "<hash of visual-evidence.json>",
  "reviewer": "<who reviewed>",
  "assignments": [
    {"cluster": "Спикер 1", "speaker": "<name from the visible label>", "method": "visual", "evidence_ids": ["f0012", "f0047"], "note": ""},
    {"cluster": "Спикер 3", "speaker": null, "method": "unverified", "evidence_ids": [], "note": "off-screen"}
  ]
}
```

   Methods: `visual` - a matching visible label on an unambiguous active frame; `context` - an explicitly marked
   conversational inference ("Иван, тебе слово"); `unverified` - not enough evidence. Never reuse names or tile
   positions from a previous call.
5. **Apply** the map to produce a new reviewed transcript version. Refuse a map whose evidence hash does not match,
   missing segments or an existing output folder. Recognised words stay unchanged.

## Pitfalls

- The border marks the app's active participant, not every audible voice in that interval. During overlap, rapid
  turns, off-screen participants, shared screens or layout changes, check adjacent frames and audio and keep the
  attribution uncertain.
- A border can stick to the recording participant while another microphone is active.
- If one segment spans two people, split it at real word timestamps in a new evidence version; never label the whole
  segment with unjustified certainty.
- Do not infer identity from faces or voices.
