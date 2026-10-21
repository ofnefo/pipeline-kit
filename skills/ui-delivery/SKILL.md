---
name: ui-delivery
description: Use when implementing or repairing a screen, panel, form, navigation or responsive UI. Preserve the requested behaviour, implement it in the app and verify the rendered user journey.
---

# Deliver a working interface

Use the project's existing stack and design direction. Resolve its source, preview URL and ownership before editing. The user request and latest corrections are the acceptance contract; an implementation plan cannot silently exclude them.

For a routine fix, record the expected before/after behaviour in the existing task note, reproduce it, change the relevant code and walk the affected journey. Do not start a redesign, palette search or whole-project audit. For a substantial redesign, establish a representative screen and direction before propagating it. Reuse approvals already given.

Separate required outcomes, user-approved exclusions and unresolved blockers. A requested interaction is unfinished if only its documentation, API, configuration profile or test was added. Reviewers receive the original request and corrections, not only the author's interpretation.

Check the rendered screen at desktop and narrow mobile width, adapted to supported devices. Exercise the changed action, its resulting state and relevant persistence after navigation or reload. Check keyboard focus and error/empty states affected by the change. Record URL/build, steps, expected/observed result and screenshots. A screenshot alone does not prove saving or navigation; a unit test alone does not prove layout.

Use additional skills only for the concrete work: design direction for a new visual system, component motion for an interaction, systematic debugging for a reproducible failure, accessibility/performance audit when required by the task or a demonstrated defect. Available skills and tools differ by installation; do not claim an absent integration was used. The bundled `web-evidence` skill can inspect saved HTML metadata; it does not replace browser acceptance.

If the user rejects the result, identify the unmet outcome and change the implementation or approach. Repeating the same check is useful only after an affected input changes. After two failures with the same cause, inspect that cause before another attempt. Keep evidence for unaffected behaviour; optional reviewer preferences do not reopen accepted work.

Acceptance: the requested journey works in the actual rendered application, relevant checks have evidence and remaining gaps are explicit. Apply review proportional to the changed behaviour and deployment risk; preserve existing security and data requirements. Complete authorised delivery after checks pass. Report implementation, verification and publication separately; technical PASS does not imply the user's visual approval.
