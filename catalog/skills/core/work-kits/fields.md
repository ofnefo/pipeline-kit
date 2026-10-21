# Fields: team, order, sample, acceptance

Each field lists the skills per role, the order of roles, the sample to make before scaling, acceptance and traps.
Role files: [roles/](roles/). Shared visual rules: [rules/visual-quality.md](rules/visual-quality.md).

## Web (сайты, лендинги, веб-приложения)
Entry: `web-pipeline`. Production sites: no deploy, restart or delete without the owner's word for that exact site.
- **Creator:** `design-style-director`, `design-taste-frontend` Design Read, `interface-design` step 1, `ui-ux-pro-max`
  → 2–3 directions with a hero sketch each, or one if the operator named it.
- **Writer:** `ru-text` + `ru-promo` + `ru-seo`; UI text `ru-text` genre "UX" → copy per block with slot lengths;
  title / description / h1.
- **Designer:** `design-taste-frontend` or `web-immersive`; product UI `interface-design`; live site
  `redesign-existing-projects` → tokens, hero plus one real case at 1440 and 375.
- **Developer:** `web-pipeline`, `react-best-practices`, `shadcn`, `backend-baseline`, `security-baseline`,
  `web-release`; component motion `emil-design-eng`; SEO build `web-seo-growth` → working staging build with receipts.
- **Reviewer:** `impeccable` for visual critique, `web-qa`, `accessibility-audit`, `performance-optimization`,
  `ux-heuristics` as relevant → reference comparison and journey evidence 1440 / 375.

Order: creator → writer and designer together (copy fits the layout) → developer → reviewer → operator →
`web-release`. A text or SEO fix on a live site skips creator and designer.
Sample: hero plus one representative real case and the conversion path (form, contact, purchase); critique it against
the references before scaling. Taste picks the direction, `ui-ux-pro-max` supports single choices, Emil guides
component behaviour, Impeccable critiques; load each at its stage, not as four competing workflows.
Acceptance: expertise and credible work on the first screen; hierarchy holds at 375; effects serve content and
`prefers-reduced-motion` works; forms proven by request and result; old routes still work; nothing invented.
Trap: "без придумывания" means no invented content, not no design.

## Video (ролики, клипы, монтаж, моушн, генерация)
Entry: `video-pipeline`. Heavy jobs take the GPU reservation.
- **Creator:** `video-direction` (shot functions, previz), `design-style-director`, references with timecodes →
  direction sheet, story beats, shot list.
- **Writer:** `ru-text` + `ru-voiceover` for narration; titles `ru-promo` → script with timing, on-screen text.
- **Designer:** `motion-graphics` style frames, `image-prompt-library`, keyframes from the generation route.
- **Production:** `video-pipeline` (edit route), `neural-video`, `comfy` / `comfy-debug`, `comfy-motion-recipes`,
  `resolve-production`, `after-effects-production`, `video-transcription`, `voiceover-dubbing`.
- **Reviewer:** `video-watch`, QC of `video-pipeline` → contact sheets of beginning, joins and end; QC receipt.

Order: creator → writer → designer (keyframes, animatic) → production → reviewer → operator. A pure cut of supplied
footage starts at production.
Sample: story beat plus keyframes or an animatic plus one difficult transition or shot.
Acceptance: reference comparisons with timecodes; framing, lens and light chosen, not default; continuity, timing,
sound and transitions serve the story; no repeated footage, accidental speed-up, gibberish speech or text; beginning,
joins and end reviewed, not only the best shot.
Traps: tech specs like "35mm" or a film stock are intent: research the real lens or stock and A/B per model. Watch the
result with `video-watch` before saying it is good.

## SMM (посты, рилсы, каналы, кампании)
Entry: `smm-pipeline`. Planning is not permission: posting, creating accounts and buying ads need the owner's word for
that action.
- **Creator:** `smm-pipeline` (brand strategy, calendar), `design-style-director` → campaign idea, rubrics, calendar.
- **Writer:** `ru-text` + `ru-promo`; Shorts narration `ru-voiceover` → posts, hooks, captions.
- **Designer:** `design-graphic-compositor`, `photoshop-production` / `open-creative-tools` → covers, carousels,
  story frames in platform sizes.
- **Production:** `smm-content-ops`, `video-pipeline` (9:16 cuts), `motion-graphics` → Reels / Shorts cuts.
- **Reviewer:** `video-watch` for clips; the brief's acceptance list → format and claims check.
- **Publisher:** only on the owner's request, exact recipient or channel, a stable request id and a receipt.

Order: creator → writer → designer and production → reviewer → operator → publisher. Source material must already be
approved. Sample: one post or short next to its neighbours in the feed.
Acceptance: audience, offer, hook, proof and action line up; platform format, length and safe zones right; production
output is not evidence of marketing impact.
Trap: never copy cookies or logins of the owner's accounts.

## Music (треки, песни, биты, джинглы)
Entry: `music-track-director` for a song, `audio-production` for audio work. Heavy renders take the GPU reservation.
- **Creator:** `music-track-director` → mood, tempo, structure, reference tracks with timestamps.
- **Writer:** `ru-lyrics` + `music-songwriting` → lyrics with sections and stresses.
- **Production:** `music-midi-composition`, `music-neural-audio-lab`, `flstudio-production`,
  `music-vocal-production`, `music-track-editor` → MIDI, renders, vocals, mix, master, stems.
- **Designer:** `design-graphic-compositor` → cover art, in parallel after the concept.
- **Reviewer:** `audio-production` (LUFS, peaks, spectrum) plus listening notes.

Order: creator → writer → production (phrase or loop first) → reviewer → operator.
Sample: one phrase or loop plus one section transition.
Acceptance: arrangement, timbre, rhythm, intelligibility and intent match the concept, compared by listening; no
clipping or artefact claims from the waveform alone; voice source and licence facts kept with the project.

## Voice and sound (озвучка, дубляж, TTS, SFX, чистка, стемы, сведение)
Entry: `voiceover-dubbing` for voice, `audio-production` for sound. Songs are the music field.
- **Creator:** `video-direction` when sound serves a film → voice character, pace, sound palette, cue list.
- **Writer:** `ru-text` + `ru-voiceover` → read script with stresses, pauses, numbers spelled out, timing to picture.
- **Production:** `voiceover-dubbing`, `audio-production` (stems, cleanup, loudness), `video-transcription` for timing,
  `flstudio-production` for the mix → takes, SFX layer, stems, mix, master.
- **Reviewer:** `audio-production` plus listening notes; `video-watch` when it sits on picture.

SFX come from your sample library first; generation only when the library has nothing.
Order: creator → writer → production (one paragraph or scene first) → reviewer → operator.
Acceptance: stresses, names and numbers read correctly; no clipped words or robotic joins; sync within a frame where
it matters; loudness meets the destination target, checked by listening.
Traps: check TTS model licences before release (some are non-commercial); voice clones only from samples the voice
owner handed over with consent.

## Graphic, print, brand, illustration (айдентика, полиграфия, баннеры, стенды)
Entry: `design-pipeline`. Shared assets by path with licence facts.
- **Creator:** `design-style-director` → directions with hero / buildable / value-engineered and cost drivers.
- **Writer:** `ru-text` + `ru-promo`; legal lines and confirmed client copy stay verbatim.
- **Designer:** `design-graphic-compositor`, `illustrator-production`, `photoshop-production`, `open-creative-tools`,
  `design-comfy-generation`, `image-prompt-library` → layouts, key visual, brand system, print files.
- **Production:** stands, interiors and packaging in volume follow the 3D route.
- **Reviewer:** `design-production-preflight` → sizes, bleed, colour mode, fonts, links.

Order: creator → writer → designer (one composition first) → production → reviewer → operator.
Acceptance: camera, materials, light, typography and dimensions match the brief; print and cutting dimensions checked
against the spec, not assumed. Traps: client work gets the client's world; never "in the style of" a living artist.

## 3D (модели, рендер, CGI, персонажи, риг, CAD, печать, сканы)
Pick a route by job; do not reduce 3D to one tool. Check the asset library for ready models, HDRI and PBR first.
- **Creator:** `design-style-director`; previz `video-direction` → look, camera, light, material intent.
- **Designer:** `design-comfy-generation`, `image-prompt-library`, `photoshop-production` → reference sheet
  (front / side / back for characters and products).
- **Production:** `blender-production`, `image-to-scene`, `cad-production`, `3d-modeling`, `comfy`,
  `game-art-production` for game assets, `design-render-refiner` for an approved render.
- **Developer:** `game-pipeline` or `web-immersive` when it goes into an engine or a page.
- **Reviewer:** `video-watch` for turntables; `design-production-preflight` before fabrication.

| Job | Typical open route |
|---|---|
| One photo or concept → model | image-to-3D model (e.g. SF3D, Hunyuan3D) → Blender clean-up |
| Real object from many photos | COLMAP → Gaussian splat; known size for scale |
| Photo → editable scene, previz, AR | `image-to-scene` |
| Surface photo → PBR set | material-estimation model; DeepBump for normal / height |
| Character for a clip | retopology → auto-rig or manual rig → motion → retarget in Blender |
| Precise part, 3D print | `cad-production` (FreeCAD, build123d) → STEP + STL / 3MF |

Sample: one asset in its delivery views (front, back, sides, top, hero) at final material.
Acceptance: silhouette, materials and light match from every delivery angle; mesh health (normals, holes, real-unit
scale), clean UVs, correct normal-map convention; rigs deform on real motion; parts checked against the drawing.
Traps: "weights on disk" is not a working route; baked light in albedo and wrong unit scale before blaming the model;
keep the editable `.blend` next to every export.

## Photo (предметка, портрет, ретушь, вырезка, апскейл, фотогенерация)
- **Creator:** `design-style-director`, `image-prompt-library` → shot list: subject, angle, lens, light, background.
- **Writer:** only when the photo carries copy.
- **Designer:** `photoshop-production`, `open-creative-tools` (darktable, GIMP, Krita), `design-graphic-compositor`.
- **Production:** `design-comfy-generation` (cutout, edit, upscale, generation), `comfy` / `comfy-debug`.
- **Reviewer:** contact sheet of the whole set; `design-production-preflight` for print.

Order: creator → designer or production (one hero frame first) → batch → reviewer → operator.
Acceptance: product shape, logo, colour and label text match the real product; cutout edges at 100 %; faces and hands
checked on every frame; colour profile and size match the destination (web sRGB, print via preflight).
Traps: raw client photos are private; upscale does not fix a wrong face or product, fix the source.

## Interactive and realtime (инсталляции, VJ, audio-reactive, AR, WebGL)
Entry by runtime: `touchdesigner-production`, `vvvv-production`, `web-immersive`, `game-pipeline`.
- **Creator:** `design-style-director`, `video-direction` for timing → scenario: input → reaction → feeling.
- **Writer:** `ru-text` + `ru-instructions` → short prompts the visitor reads in the space.
- **Designer:** `motion-graphics`, `interface-design` for control screens, `image-to-scene` for AR scenes.
- **Developer:** the runtime skill → inputs, states, output mapping, fallbacks.
- **Production:** `blender-production`, `comfy`, `audio-production` → realtime-ready meshes, loops, sound.
- **Reviewer:** `video-watch` on a screen recording; `web-qa`; `performance-optimization`.

Sample: one interaction end to end on the target hardware: real input → visible and audible reaction.
Acceptance: target frame rate at the real resolution for the whole run; every input has a reaction and an idle state;
recovery from a lost sensor, camera or network; browser pieces at 1440 and 375 with reduced motion.
Traps: a still frame is not proof, record motion with input; set polygon and texture budgets before production.

## Office (сметы, КП, договоры, отчёты, протоколы)
Entry: `office-pipeline`.
- **Intake:** `office-document-intake`; calls and meetings `meeting-transcription`.
- **Estimator:** `estimate-production` → estimate, budget, payment schedule, reconciled totals.
- **Writer:** `ru-text`; ТЗ `ru-instructions`; selling parts of a КП `ru-promo`; numbers only from the estimate.
- **Designer:** `commercial-document-production` → Word / PDF / slides in the house layout.
- **Reviewer:** `office-preflight`.

Order: intake → estimator → writer → designer → reviewer → operator. Contracts are audit-only; legal force is the
lawyers' decision. Sample: one page with real numbers, or one estimate section reconciled end to end.
Acceptance: every number traces to the estimate and totals reconcile; names, dates, prices and requisites copied, not
retyped; the package opens in the receiver's format. Trap: personal and payment details stay inside the project.

## Game (прототипы, ассеты, сборки, моды)
Entry: `game-pipeline`; mods: `mod-any-game`.
- **Creator:** `game-pipeline` (gameplay need first), `design-style-director` → core loop, art direction.
- **Writer:** `ru-text`; tutorials `ru-instructions` → in-game text with length limits.
- **Designer:** `game-ui-ux`, `game-art-production` → HUD, menus, sprites, style sheet.
- **Developer:** `godot-development`, `save-systems` → playable build.
- **Production:** `asset-pipeline`, `comfy`, the music field for sound.
- **Reviewer:** `playtest-qa` → playtest report with captures.

Order: creator → developer greybox → designer and production → reviewer → operator. Game art starts after the gameplay
need is clear. Sample: one playable slice with the core loop and the hardest interaction.
Acceptance: the core loop is understood without explanation; UI readable at play distance with all input states;
assets fit the art direction and engine budget, licences recorded. Trap: a screenshot is not proof that a build runs.
