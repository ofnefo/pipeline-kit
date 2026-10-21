---
name: smm-pipeline
description: "Use when planning or running social media for a brand or product: strategy, content plan and calendar, account inventory, publishing route, approval gate and campaign measurement (RU: \"контент-план\", \"SMM\", \"соцсети\"). Routes content work to smm-content-ops and SEO to web-seo-growth. Not for posting, creating accounts, following, mass messaging or buying advertising without an explicit request."
---

# smm-pipeline

## Purpose
One place to decide what a brand says, where, when and how success is measured, with a hard approval gate before anything leaves
the workspace.

## Inputs
- The brand's accepted strategy/decisions file (positioning, offer, proof, tone, forbidden claims).
- The account inventory (network, handle, owner, verified permissions, last check date).
- Assets and cases that are already approved; analytics exports if any.

## Routes (pick the smallest)
| Need | Route |
|---|---|
| Strategy | audience, offer, evidence, CTA, channel, measurable outcome; unknowns marked |
| Content plan / calendar | this skill, `references/content-plan-template.csv` |
| Posts, reels, carousels, briefs | `smm-content-ops` |
| Final copy | your copy-editing skill for the target language |
| Website/SEO variant | `web-seo-growth`; site deploy is a separate authorisation (`web-release`) |
| Media production | the existing video/design/music pipeline, not a new generation stack |

## Workflow
1. **Read before proposing:** strategy file, accepted decisions, previous plans and idea lists. Refine; do not duplicate.
2. **Strategy note:** audience -> problem -> offer -> proof -> CTA -> channel -> one measurable outcome per period.
3. **Content plan:** pillars (3-5), cadence per channel, formats, a calendar with planned editorial dates (with time zone),
   owner and status per item. Status flow: `idea -> production -> review -> approved -> scheduled -> published`.
4. **Account inventory:** an account is "unverified" until its access and permissions were actually tested; record what each
   permission allows (post, comments, inbox, insights). Publishing access does not imply follow/unfollow or DM access.
5. **Approval gate (mandatory):** a post moves to `approved` only after the operator (or the client, for client accounts) approves
   the exact text, media, link, account and date. Approval is per item; a plan approval is not a post approval.
6. **Publishing route:** use the connector or provider whose permissions were verified; one route per network, no parallel bots.
   Publish only on the operator's explicit request; record a provider receipt (post id/URL, time).
7. **Measure:** one changed variable per experiment, equivalent windows, source and date of every number, unknowns stated.

## Editorial workspace
If a local editorial tool keeps posts, update with the current revision; on a conflict keep the author's text and rebase
deliberately. "Ready" or "planned" never means published. Never promise automatic publication unless it exists and was tested.

## Gotchas
- Several brands: adapt intent to each audience instead of cross-posting the same text.
- Internal tools and infrastructure never appear in public copy.
- Dates in plans are editorial intentions, not commitments from the platform.

## Acceptance checklist
- [ ] Strategy facts traceable to the brand's accepted sources; unknowns marked.
- [ ] Content plan has pillars, cadence, formats, dates with time zone, owner, status.
- [ ] Every item to be published passed the approval gate for its exact content.
- [ ] Publication claims carry a provider receipt.
- [ ] Measurement plan: metric, source, window, one variable.

## Boundaries
No posting, scheduling, account creation, following, mass messaging or paid promotion without the operator's explicit request for
that action. Client accounts need the client's approval too.

## Optional reading
coreyhaines31/marketingskills (MIT): marketing-plan, content-strategy, social, analytics write-ups. Reference only, not copied.
