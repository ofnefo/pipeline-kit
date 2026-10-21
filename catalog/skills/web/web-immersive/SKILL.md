---
name: web-immersive
description: "Use when building cinematic or immersive web pages: portfolios, promo and wow-effect pages, 3D heroes, scroll scenes, page transitions, or recording a preview video of a site. Gives a three.js + GSAP ScrollTrigger + Lenis motion engine, tested recipes (pinned rails, flips, glass, before/after, CRT pass) and a headless preview-video recorder. Not for product UI, dashboards or plain landing pages."
---

# web-immersive: 3D, scroll scenes, transitions, preview video

For promo, portfolio and "cinematic" pages. Product UI and dashboards belong to an interface-design skill; a plain landing page to a
landing/taste skill; a live-site audit to `web-qa`. Where the site lives, where changes go and how it deploys come from the project's
card in your project map. Production deploys happen only on the operator's explicit request for that exact site (`web-release`).

## Inputs
- Brief: audience, mood words, 3-5 named references (sites, films, studios), what must be shown (works, product, contact).
- Assets: photos/renders, cut-outs with alpha, video clips; licence noted for each.
- Target: local dev URL, build command, deploy doc.

## Before you start
1. Pick references first and write one line per reference about *what* to take (depth, cut-out objects, page-turn, glass, brutal grid).
   "A collection of screenshots" is not a concept.
2. Reuse what the project already has (motion helpers, scroll-video component, sitemap canvas) before writing new code.
3. Images for scenes: follow your generation route (curated references, then your image models). Cut-outs: WebP with alpha, check
   edges at 2x zoom. Heavy local GPU jobs run one at a time; record the preview video after them, not alongside.

## Default stack
Astro (static) + TS islands; `three`, `gsap` + `ScrollTrigger`, `lenis`. Next/React only if the project already uses it.
One motion engine per page:

```ts
const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
const fine = matchMedia('(hover: hover) and (pointer: fine)').matches;   // cursor effects only here
if (!calm) {                                                             // calm -> native scroll, no Lenis
  lenis = new Lenis({ lerp: 0.11, anchors: { offset: -64 }, autoRaf: false });
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add((t) => lenis.raf(t * 1000));
  gsap.ticker.lagSmoothing(0);
  // dialogs: lenis.stop() while dialog[open], lenis.start() after close
}
```

## Recipes
| Technique | How | Gotcha |
|---|---|---|
| Pinned horizontal rail | `gsap.to(track,{x:()=>-dist(),ease:'none',paused:true})` + `ScrollTrigger.create({pin, scrub:0.5, animation, invalidateOnRefresh:true, onRefreshInit:size})` | sizes only via functions, otherwise resize breaks it |
| Details inside the rail | `scrollTrigger:{containerAnimation: run, start:'left right'}`; photo parallax `xPercent ±7`, wipe `clipPath: inset(0 0 0 100%) -> 0` | `containerAnimation` has no `pin`/`snap` |
| Velocity skew | `gsap.quickTo(track,'skewX')` from `self.getVelocity()/-260`, clamp ±6, back to 0 after 140 ms | - |
| Card flip / page turn | `rotateY` + `backface-visibility`; fade opacity only in the last 30% of the turn | earlier fade reads as a plain crossfade |
| Text scramble | random glyphs -> final text | skip when `calm` |
| 3D scene (ring of works, hall) | `setPixelRatio(min(dpr, mobile ? 1.5 : 1.75))`; pause on `IntersectionObserver` + `visibilitychange`; `dispose()` on leave; textures via `loadAsync` + `Promise.allSettled`; too few loaded -> drop the scene, show a static fallback | an unpaused render loop burns battery and GPU |
| Glass | `backdrop-filter: blur()` + `@supports not (backdrop-filter: blur(1px))` solid fallback | lightningcss keeps only `-webkit-backdrop-filter` when the source has both: write one property and grep the built CSS (`grep backdrop-filter dist/**/*.css`) |
| Dark page + line art | `filter: invert(1) hue-rotate(180deg)` | line art only, never photos |
| Before/after wipe | two layers, top one `clip-path: inset(0 0 0 var(--x))`, `--x` from pointer/scroll; handle is an `<input type=range>` for keyboard | without JS show "after" in full |
| HUD captions with cursor | frames and mono labels in an absolute layer over photo/video, coordinates in %; cursor follows via `gsap.quickTo` with lag | static captions when `calm` |
| CRT / dither / halftone over 3D | `EffectComposer` + custom `ShaderPass` | one more render pass: disable on mobile |
| Page transitions | View Transitions (Astro `<ClientRouter/>`) or a GSAP wipe; afterwards `ScrollTrigger.refresh()` and rebuild scenes | three.js leaks without `dispose()` |

## Mobile and accessibility
- Check 390x844 and 1440x900. On touch screens replace a horizontal pin with a vertical list or native `scroll-snap`.
- Fixed header: give the first sections top padding (e.g. `padding-top: 64px` for a card deck under a 64 px header).
- `prefers-reduced-motion`: no Lenis, no scrub animations, no scramble; all content visible, also without JS.
- Budget: LCP <= 2.5 s, CLS < 0.1; load 3D after first paint (`requestIdleCallback` / on visibility); textures WebP <= 1600 px.

## Preview video
```bash
# run from a folder where playwright-core is installed; ffmpeg on PATH
node scripts/record_preview.mjs --url http://127.0.0.1:4321/ --out <out-dir> --w 1440 --h 900 \
  --stops "[data-rx],[data-os],.section" --step 40 --dark [--chrome <path-to-chrome-headless-shell>] [--angle d3d11|metal|vulkan]
```
- Sequence: 2.6 s on the hero -> circular cursor sweep (parallax) -> wheel scroll to the end with a 0.7 s pause at each `--stops`
  match -> 1.8 s hold. Frames via CDP screencast, then ffmpeg (`-fps_mode vfr`, 30 fps, x264 crf 20, faststart) ->
  `<out>/preview.mp4` + `preview.json` (receipt: bytes, frames, seconds, viewport, stops, console errors).
- Browser: `--chrome` / `CHROME_PATH` or Playwright's bundled Chromium; always a temporary profile, never a real user profile.
  WebGL on GPU by default; `--cpu` = SwiftShader (no GPU, ~2 fps, choppy), only when the GPU is busy.
- Exit codes: 0 ok; 3 video written but the page logged console errors (listed in the receipt); 1 failure (scroll stalled, no
  frames, ffmpeg); 64 bad arguments, including an invalid `--stops` selector (one selector list; commas inside `:is()` are fine);
  69 no browser / Playwright. Frames go to a temp `frames-*` folder inside `--out`; only that folder is removed.
- Lighter file for messengers: `--crf 25` or `--w 1280 --h 800`. Send it only through your delivery channel after the operator asks.

## Acceptance (in order, one pass)
1. Build passes; the built CSS contains `backdrop-filter` if glass is in the design.
2. Section screenshots at 1440 and 390; walk the real user path (hero -> works -> contact/form) and look at every step.
3. `web-qa`: axe + Lighthouse on the local URL; console clean.
4. Reduced-motion run: everything readable, no pins or scrub.
5. Preview video recorded; `console_errors` in `preview.json` is empty; compared side by side with the named references.

## Boundaries
- No production deploy, no sending of the video, unless the operator asks for that exact site or recipient.
- Technical acceptance is not the operator's or client's creative approval.
