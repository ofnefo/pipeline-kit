---
name: design-style-director
description: Use when a project needs design directions chosen or developed - brand identity, campaign, merch or spatial experience concepts, moodboard briefs, trend or portfolio benchmarks, comparing visual approaches. Produces 2-3 comparable directions with rules, references, cost drivers and hero / buildable / value-engineered variants. Not for executing the chosen direction (compositor, Illustrator, Blender skills) and never imitates a named living designer.
---

# Design Style Director

Turn references and project constraints into comparable, producible directions.

## Inputs

- The active project file and every existing project-rules file it lists.
- The project's own references, brand assets and any existing approved system (if there is one, use its rules instead of restarting discovery).
- Your studio's style catalogue if it has one. Without it use `references/style-framework.md` as the schema.
- For spatial work: discipline, venue, plan and camera locks. For flat brand work these are not required.

Explicit operator instructions outrank project files; project files outrank reusable examples. No preset is the default for a client name.

## Keep the axes independent

```text
discipline + typology + style + experience mechanic + build system
+ delivery level + creative level
```

Do not call a double-deck stand a style, kinetic a budget, or premium a typology. Competency (what the team can build) and visual approach are separate questions.

## Workflow

1. Restate the objective, audience, required content and constraints. For spatial work add venue, geometry, visitor journey, budget, schedule, installation, maintenance, safety and reuse.
2. Collect references: the project's own first, then type and asset libraries the studio already holds, then external search. Record each source and the observable decisions taken from it. A library landing page is not evidence that a specific work was reviewed.
3. Propose the requested number of directions, or 2-3 when unspecified. Keep function, required content and comparison formats constant; vary the underlying idea and composition. Preserve the approved plan and camera when spatial locks apply.
4. For each direction state:
   - one-sentence concept and five visual or spatial rules;
   - typology / style / mechanic / build system IDs;
   - what is taken from each reference and what is explicitly not taken;
   - materials, palette, light, media, hero moment and stop-list;
   - main production and cost drivers;
   - low/base/high cost logic or `TBD_RATE`, never invented certainty;
   - fit, risks and one recommendation.
5. After one direction is chosen, derive three delivery levels:
   - `hero`: the complete expressive idea;
   - `buildable`: the recommended real-world version;
   - `value_engineered`: the same recognizable idea with expensive nodes simplified.

## Trends and portfolios

For any claim about what is current, check official portfolios, event sites, award programmes or primary publications and record `as_of` per case, separately from the research date. Awards show a market contour, not a command to copy. Never put "in the style of [living designer]" in a generation prompt; extract observable principles (geometry, density, material, light, journey, build logic) and keep author and URL only in the source card. Label trend hypotheses as hypotheses.

## Acceptance checklist

- [ ] Directions are comparable: same function, content, formats and (spatial) camera.
- [ ] Every reference has a source and a take / do-not-take note.
- [ ] Cost logic is ranged or `TBD_RATE`; nothing invented.
- [ ] One recommendation with risks.
- [ ] No living-designer imitation in prompts.

## Output

A style-direction sheet (one YAML record per direction, schema in the reference) that can feed a moodboard, style frames, the estimate and an approval record. A style frame is never engineering or production approval. Copy on graphics goes through your copy-editing step before it is placed; brand names, legal lines and confirmed client copy stay verbatim.

## Boundaries

- Locked-image finishing goes to `design-render-refiner`.
- Deterministic brand graphics go to `design-graphic-compositor`.
- Production checks go to `design-production-preflight`.
