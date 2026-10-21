---
name: smm-content-ops
description: "Use when turning an approved case, clip, design or track into social posts: Reels/Shorts/TikTok variants, carousels, Telegram posts, captions and a production brief (RU: \"сделай посты\", \"нарежь рилсы\"). Produces reviewable drafts, variant cards and handoffs plus a pre-publish checklist. Not for publishing, rendering without a task, or inventing claims, metrics or client permissions."
---

# smm-content-ops

## Purpose
One approved master -> several platform-native drafts that are ready for the approval gate in `smm-pipeline`.

## Inputs
- The accepted master (exact path and version), brand strategy/decisions, the target channels.
- Capture: brand, audience, **one** objective, evidence, hook, CTA. Unknown client permissions, release dates, feature readiness
  or performance data stay marked **unknown**.

## Post formats
| Format | Core structure | Checks |
|---|---|---|
| Short video (Reels/Shorts/TikTok, 9:16) | first-frame hook (0-2 s) -> payoff -> evidence -> next action | safe areas, burned-in or readable subtitles, platform length limit, audio rights |
| Carousel (4-10 slides) | hook slide -> one idea per slide -> proof -> CTA slide | text legible at phone size, consistent grid, alt text |
| Single image + caption | image carries the claim; caption adds context and CTA | crop per platform ratio, caption not clipped before the key line |
| Telegram post | first line = the point; short paragraphs; one link; optional media | link preview correct, formatting renders, topic/channel correct |
| Website case / article | problem -> approach -> result with evidence -> CTA | hand off to `web-seo-growth` |

Check each platform's current format specs before export; they change.

## Workflow
1. Reuse the accepted master; never regenerate it here.
2. Write a short **brief** per variant: source path, excerpt/timecodes, format, aspect ratio, duration, copy, acceptance criteria.
   Production goes to the existing video/design/music workflow.
3. Adapt intent and copy per audience and platform; do not mechanically duplicate across brands or networks.
4. Product claims come from the product's documented decisions; brand voice comes from owner-provided samples, otherwise neutral
   concrete language. Run final copy through your copy-editing skill.
5. Store each platform variant as its own card linked to the campaign/master; status `idea -> production -> review -> ready`.
6. Hand the ready variants to the `smm-pipeline` approval gate. A planned date is an editorial date, not a schedule.

## Pre-publish checklist (review once at delivery size)
- [ ] Opening readable/understandable in the first seconds without sound.
- [ ] Facts, names, numbers and dates correct and sourced.
- [ ] Audio appropriate and licensed; subtitles match speech.
- [ ] Caption not clipped before the key line; hashtags/mentions intentional.
- [ ] Link/destination works, UTM set if measured; CTA matches the offer.
- [ ] No private data, internal tools, client-confidential material or unreleased features.
- [ ] Correct account, channel/topic and date; explicit approval recorded for this exact item.

## Measurement
One changed variable per experiment (hook, cover, length, time); equivalent windows; record source, date and unknowns.

## Acceptance checklist
- [ ] Every variant traces to the accepted master and brand sources.
- [ ] Brief has exact source, format and acceptance criteria.
- [ ] Pre-publish checklist passed; unknowns listed.
- [ ] Nothing was published or scheduled by this skill.

## Boundaries
No silent sends or scheduling; an approved draft is not a published post, and a provider receipt is a separate record.
