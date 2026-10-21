---
name: motion-graphics
description: Use when a graphic layer or a design-led animated piece is needed ("титры", "плашка", "нижняя треть", "кинетическая типографика", "анимация логотипа", "инфографика в видео"). Routes titles, kinetic type, lower thirds, overlay cards, logo stings, stat/chart animations, caption styling, explainers and slideshows to one engine (HyperFrames, Remotion, Lottie/Skottie, canvas lower thirds or ASS via libass) and renders a versioned file for the edit. Not for cutting footage, generated footage (neural-video) or After Effects compositions (after-effects-production).
---

# Motion graphics

Purpose: pick **one** engine per piece, render it to a versioned project folder (`60-motion/<piece>/v001/...`) and hand
the file (MP4, or an alpha overlay) to the edit.

## Inputs

- The brief: what the graphic must say, duration, delivery size and fps, where it sits (full screen or over footage).
- Brand assets in the project: fonts (files, not names only), logo vectors, colour values.
- For overlays: the actual footage frames it will sit over, plus the safe-area rules of the platform.

## Route

| Need | Engine | Where to get the know-how |
|---|---|---|
| Short design-led unit (<10 s, no narration): kinetic type, count-up, chart hit, logo sting, animated map, UI animation; MP4 or alpha overlay | HyperFrames (HTML to video) | upstream skills: https://github.com/heygen-com/hyperframes (`skills/`, Apache-2.0) |
| Longer or multi-scene piece: sizzle/brand reel, explainer, footage remix, overlay cards on an interview, navigable slideshow | HyperFrames | same upstream (`general-video`, `talking-head-recut`, `slideshow` skills) |
| Lower third / chyron / corner bug with transparency (WebM alpha, ProRes 4444) | canvas + headless browser + FFmpeg | https://github.com/iart-ai/lower-thirds-skills (MIT) |
| React composition inside an existing Remotion project | Remotion | https://github.com/remotion-dev/skills (check the Remotion licence for commercial use) |
| Lottie/Bodymovin JSON (icons, loaders, microinteractions, type) for a Skottie/lottie player | Lottie | https://github.com/diffusionstudio/lottie (MIT); spec: https://github.com/lottie/lottie-spec |
| Kinetic text titles burned in or composited with libass | ASS subtitles + FFmpeg | `ffmpeg -i in.mp4 -vf "ass=titles.ass:fontsdir=fonts" -c:a copy out.mp4` |
| AE template, compositing, MOGRT | After Effects | `after-effects-production` |

Install upstream skills and CLIs yourself, pinned to a commit or version, in a project or tool sandbox. Read them; do
not rewrite vendored text. Keep a provenance note (URL, commit, licence, local changes) next to any vendored copy.

## Workflow

1. **Brief and engine.** Write the piece's job in one line, its duration and the delivery spec. Pick one engine from
   the table; do not mix engines inside one piece.
2. **Style frame.** One still at delivery size over a real footage frame (or the real background). Check legibility,
   safe areas and brand colours before animating.
3. **Animate.** Timing on beats of the voice or music. Keep holds long enough to read: about 3 words per second plus
   0.5 s, and never under ~1.5 s for a short line.
4. **Render.** Versioned output; for overlays render alpha (ProRes 4444 or VP9/WebM with alpha), for full-screen pieces
   H.264/H.265 at the delivery fps. Record a render receipt (inputs, engine and version, output path, hash).
5. **Review** the rendered file, not the editor preview: at delivery size, over the real footage, frame-stepping the
   in and out transitions.

## Techniques and gotchas

- Fonts: ASS through FFmpeg/libass needs the font's PostScript/family name and the font file reachable via `fontsdir`;
  HTML engines need the font file inside the project (no system-font assumptions on a render host).
- Alpha: verify the alpha channel actually survived (`ffprobe -show_streams` -> `pix_fmt` with `a`, e.g. `yuva420p`,
  `yuva444p10le`). H.264 has no alpha.
- Headless HTML renderers: pin the browser build; disable telemetry; refuse cloud render or account commands unless the
  operator asked for them for this job.
- Network-capable helpers (map tile baking, package installs) only on explicit request; pin versions per project.
- On-screen text in a language you do not proofread natively goes through a proofreading pass before render.
- Charts: numbers on screen must match the source data; keep the source table with the render.

## Acceptance checklist

1. One engine per piece; render receipt present (inputs, engine/version, output path, hash).
2. Size, fps, duration and codec match the delivery spec (`ffprobe`); alpha present where the piece is an overlay.
3. Every line is readable at delivery size for its hold time; nothing crosses the safe area.
4. Fonts are the brand fonts (no fallback substitution visible); colours match brand values.
5. Reviewed over real footage, including alpha edges and the first/last frames of each transition.
6. Text proofread; figures checked against the source.

## Boundaries

Graphic layers and design-led pieces only. Cutting footage is editing work; generated footage is `neural-video`;
After Effects compositions and templates are `after-effects-production`.
