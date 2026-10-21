---
name: web-qa
description: "Use when asked to check, audit or accept a site or screen (accessibility, speed, Lighthouse, screenshots 1440/375, before/after comparison, watching a page for changes; RU: \"проверь сайт\", \"приёмка\"): user-journey walk on desktop and mobile, axe + Lighthouse, screenshot diff and change monitoring, preview check for 3D/scroll pages. Read-only for live sites. Not for designing the UI itself."
---

# web-qa: checking, accepting and watching sites

Runs locally in an isolated headless Chromium (temporary profile, never a real user profile, no cloud testing services). Where the
site lives and where fixes go comes from the project card. A live site is read-only (GET); forms on production are not submitted.

## Inputs
- URL (dev `http://127.0.0.1:<port>` or a built folder served locally), pages, key user journeys (from the brief, card or rules).
- What counts as "passed" for this task, written down before starting.

## Tools (public, interchangeable)
- Playwright (`playwright-core` + chrome-headless-shell or bundled Chromium) for journeys and screenshots.
- `@axe-core/playwright` (or axe-core injected) for accessibility; Lighthouse CLI for performance/a11y/SEO scores.
- Screenshot diff: `pixelmatch` / `odiff` or Playwright `toHaveScreenshot`.

## Order (do not skip)
1. **Recon.** URL, pages, journeys, pass criteria. Dev server not running -> start it hidden, with an owner and a TTL.
2. **Screenshots at 1440 and 375** (first screen + full page, warn on horizontal scroll). Look at them: hierarchy, gaps, clipped
   text, overlaps, long names.
3. **Journey walk** (below) at 1440x900 and 375x812: every action, every state.
4. **axe + Lighthouse** on the same URL; a second run with the desktop preset if relevant.
5. **Report**: the table below, with paths to every screenshot and the summary. Say "works" only with a receipt.

## Journey walk
- **Look before acting:** open the page, wait for the network to settle, take a screenshot or the accessibility tree, and only then
  choose elements. Locator priority: role -> label -> text -> `data-testid`; CSS chains last.
- Wait on state (`expect(locator).toBeVisible()`, waiting for a response), never `sleep`.
- Collect console and network errors from the first second (`page.on('console')`, `page.on('pageerror')`, responses >= 400).
- A screenshot per step: `NN-<step>@<width>.png`. Check: focus visible and in order from the keyboard, no horizontal scroll, touch
  targets >= 40-44 px, dialogs close on Esc and return focus.
- **States:** loading/progress, empty, empty after filter (with reset), error with an action, success; resubmit is harmless; input
  survives a network drop (emulate offline). For lists: search, bulk actions, export.
- **Forms:** on dev submit for real and show the result (server response, record, mail in a test inbox). A screenshot of a form is
  not proof that it works. On production fill only, do not submit, unless the operator says otherwise.
- One `prefers-reduced-motion: reduce` run: all content visible, no pins or scrub.
- **Collapsed stays collapsed at 375:** a responsive rule such as `tr{display:block}` overrides the `hidden` attribute and every
  "More" block opens at once (the page becomes many times taller). Check: 0 visible `[hidden]` elements, page height at 375
  comparable to 1440; in CSS `[hidden]{display:none!important}`.

## Accessibility and performance audit
- Lighthouse mobile preset (390x844) by default; desktop as a second run. Example gates: fail on axe `serious`, performance >= 80.
- Block analytics/counters during audits so visits are not counted; allow them only when the task is about analytics.
- axe finds only part of WCAG: keyboard, focus and labels are checked in the walk above. Lighthouse is one lab run; for decisions
  use 3 runs (median) or field data.

## Before/after comparison
Shoot the same pages and widths for the before build and the after build, diff them, and classify each page: `same`, `changed`,
`layout` (size changed), `missing`, `new`, `error`. A change is not a failure, but each one is explained.

## Watching for changes
Baseline on the first run, then periodic diffs within one supervised process (no OS scheduler entries without the operator's
request). Hide unstable elements (clocks, sliders, carousels) by selector. Send diffs through your delivery channel only when
the operator asks.

## Scroll scenes, 3D, preview video
For pages with pins, rails and 3D (`web-immersive`): additionally wheel-scroll the page at 1440x900 and 390x844, check the console,
the reduced-motion mode and glass (`backdrop-filter` present in the built CSS). A preview video comes from
`web-immersive/scripts/record_preview.mjs` (exit 3 = the page logged console errors).

## Report
Table: page | width | problem | severity | what to do | who (agent / operator). Below it: paths to screenshots, the audit
summary, the console log. Fixes go into the dev copy; production deploy only on the operator's explicit request for that site.

## Acceptance checklist
1. Screenshots at 1440 and 375 of all stated pages exist, paths in the report; no horizontal scroll; 0 visible `[hidden]` at 375.
2. Every key journey walked to its result at both widths; a screenshot per step.
3. Loading, empty / empty-after-filter, error-with-action and success states shown.
4. Forms submitted on dev with the result confirmed; nothing submitted on production.
5. Console and network clean (or errors listed in the report).
6. No axe `serious`/`critical` violations, or they are in the table with a fix; LCP/CLS within the site budget.
7. Keyboard and focus checked by hand; reduced-motion run done.
8. Report is a table with severity and owner; technical acceptance is not presented as the operator's approval.

## Anti-patterns
- "Checked, everything works" without screenshot paths, exit codes or a summary.
- A screenshot of a form as proof that the form works.
- `sleep(3000)` instead of waiting on state; selectors chosen before the page loaded and was inspected.
- Desktop only, or "mobile" as a narrowed desktop window without touch emulation.
- Submitting forms, logging in or registering on a live site; automating a real browser profile.
- Repeating the same heavy run without a change; "while I'm here" fixes outside the task.
