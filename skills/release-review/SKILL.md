---
name: release-review
description: Use before releasing changes to Pipeline Kit code, source selection, agent instructions, dependencies or public archives.
---

# Public release review

Classify scope and risk before editing: documentation-only low-impact work, shared behaviour, or security/data/publication changes. Routine prose needs a focused self-check; shared code/skills/setup behaviour one independent review; agent rules, security, destructive operations and production deployment independent implementation and acceptance review. Classify the current operation, not a legacy whole-project label. Read `docs/RELEASE.md`; reviewers need the exact file manifest, requirements, tests and known blockers.

Refresh only individually approved owned source files listed in provenance. Never recursively copy a private workspace, application SDK, cache, state directory or model installation. Reapply portable paths and safe defaults deliberately; inspect diffs. Preserve third-party licence notices and source references.

Run the release scanner and archive builder, then verify the extracted archive. For changed skills/profiles, test installation from that archive. A first runtime/dependency release needs a fresh environment with pinned dependencies and the applicable integration suite. For later releases, run only affected checks and reuse valid versioned evidence for unchanged behaviour. Browser journeys at desktop/mobile widths are required for changed UI, not unrelated prose; optional components need checks when their behaviour or verification claim changes. Verify imports/startup do not launch workers, remote scans, alerts or paid calls. Keep test output and dependency versions as evidence.

Give reviewers the original request and latest corrections, the full current diff and concrete acceptance evidence. A unilateral OUT OF SCOPE line cannot excuse missing requested behaviour. Reuse unaffected checks after a repair; optional preferences do not create another review round. A blocked or unrun check stays blocked; a staged archive is not a release approval. Commit, publish or deploy only within the operator's explicit authorisation after review. Record the final archive digest and review decision. Never include internal evidence containing personal paths or credentials in the public package.
