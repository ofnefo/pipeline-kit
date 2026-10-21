# Visual quality: one checklist for sites, UI, graphics and video frames

A shared minimum distilled from design-direction, interface and video-direction practice. The source skills
(`design-taste-frontend`, `interface-design`, `ui-ux-pro-max`, `redesign-existing-projects`, `design-style-director`,
`video-direction`) keep the details: code recipes, dials, databases, shot grammar.

## 1. Direction before production
- **Read the job in one line:** what it is, for whom, and the one feeling or action it must produce.
- **Ground it in the subject's world.** List 5–8 concrete things from the client's domain (materials, objects, words,
  rituals, colours of the place). The design uses at least two. Generic "tech" or "premium" is not a world.
- **Name the references.** 2–4 real works with a path, URL or timecode. For each: what we take and what we do not, in
  observable terms (framing, density, type, light, rhythm). Never a living designer's name as an instruction.
- **Default check.** Describe the obvious, model-default version, then say what we do instead. If the plan matches the
  default, the direction is not done.
- **Stop-list** of 3–5 things this project will not use.

## 2. Hierarchy and system
- One focal point per screen, frame or page. Squint test: blurred, the main thing still wins.
- Tokens before pixels: one palette (neutrals + one accent; a second accent only with a stated job), one spacing
  scale, one radius set, one depth strategy. Token names belong to the product, not `blue-500`.
- Type: at most two families, both with full Cyrillic (check the actual glyphs). Body lines ≤ 75 characters.
  Hierarchy by weight, colour and space, not only size.
- Status and meaning never by colour alone. Contrast meets WCAG AA.
- Russian first: long words, full ФИО and long button labels fit at 375 px without losing meaning.

## 3. Motion
- One signature motion moment per page or sequence; everything else is quiet.
- Web: transform and opacity only, under 300 ms for interface feedback, `prefers-reduced-motion` respected, nothing
  animated on actions done many times a day.
- Video: one camera behaviour per shot; motion must change understanding or bodily state.

## 4. Honest content
- No invented numbers, logos, reviews, client names, awards or "trusted by". Missing proof → `[нужны данные]`.
- No fake product UI built from boxes; use a real screenshot, a real component or a generated image labelled as such.
- Placeholder data is locale-correct and labelled; prototype fixtures are never reported as a working integration.

## 5. States (any interactive UI)
Empty, loading, error, success, long content, no permission, offline. Double submit is harmless. Product screens also
need: search, bulk actions, export, error history, details behind expanders that remember their state, and the
existing workflow preserved.

## 6. Slop list
Reject these unless the brief explicitly asks for one:
- **Colour and light:** neon or outer glow; pure `#000`; oversaturated accents; default purple / blue-violet
  gradients; gradient headline text; glassmorphism by default; a different hue per card.
- **Layout:** three identical feature cards in a row; four icon + big-number metric boxes on every dashboard; even
  spacing everywhere with no rhythm; floating explainer text in a section-header corner.
- **Type:** the framework default font as an unexamined choice; screaming oversized H1; serif on dashboards;
  line-broken italic headlines as a "design move"; vertical rotated labels.
- **Decoration:** numbered section eyebrows (`01 / Capabilities`); `01 / 4` counters on images; decorative hairline
  grids; status dots on every row without meaning; tags over photos; mono-caps keyword strips; middle-dot separators
  everywhere; city / time / weather strips; scroll cues; build labels on marketing pages; custom cursors.
- **Depth:** grey cards on grey with faint shadows everywhere; mixed depth strategies; hard borders on every row.
- **Words:** "elevate", "seamless", "next-gen", «революционный», «инновационный»; poetic section labels; mock-humble
  asides; Lorem ipsum or «Иван Иванов» data. Russian copy follows `ru-text`, including its dash rules.
- **Icons:** emoji as icons; hand-drawn SVG icons.
- **Video and images:** mood words ("cinematic", "epic") instead of decisions; polish that erases physical evidence;
  repeated footage, accidental speed-up, gibberish text in frame.

## 7. Self-critique, fix, receipts
1. Critique the rendered result (screenshot, frame, contact sheet), not the code or prompt.
2. Put the main reference next to it and write three lines: what it does better, what we do better, what to change.
   Interface: also the swap test (would a default font or layout change anything?) and the signature test (point to
   five places the direction shows).
3. Fix by removing first, then adjusting, then adding. Re-check only what the fix touched.
4. Receipts: web at 1440 and 375 (fold and full page) plus `web-qa` checks (axe, Lighthouse, console errors); print
   with dimensions and preflight; video with contact sheets of beginning, joins and end. A screenshot is not proof that
   a form or a deploy works.
5. Report separately: technical pass, creative assessment, owner decision. Taste approval belongs to the operator or
   client.

## Where the source skills win

| Need | Skill |
|---|---|
| Landing / promo code recipes, dials, full AI-tells list | `design-taste-frontend` |
| Product UI process, swap / squint / signature / token tests, `system.md` | `interface-design` |
| Palette, font pair, chart, UX rule lookup | `ui-ux-pro-max` |
| Upgrading a live site without breaking it | `redesign-existing-projects` |
| Directions, cost drivers, hero / buildable / value-engineered | `design-style-director` |
| Shot functions, previz, version review rubric | `video-direction` |
