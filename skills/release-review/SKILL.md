---
name: release-review
description: Use before releasing changes to Pipeline Kit code, source selection, agent instructions, dependencies or public archives.
---

# Public release review

Classify scope and risk before editing: documentation-only low-impact work, shared behaviour, or security/data/publication changes. Public distribution changes require independent implementation and acceptance review. Read `docs/RELEASE.md`; reviewers need the exact file manifest, requirements, tests and known blockers.

Refresh only individually approved owned source files listed in provenance. Never recursively copy a private workspace, application SDK, cache, state directory or model installation. Reapply portable paths and safe defaults deliberately; inspect diffs. Preserve third-party licence notices and source references.

Run the release scanner and archive builder, then verify the extracted archive in a fresh environment with pinned dependencies. Run the integration suite, optional component checks actually claimed, and browser journeys at desktop/mobile widths. Verify imports/startup do not launch workers, remote scans, alerts or paid calls. Keep test output and dependency versions as evidence.

Give independent reviewers concrete source and acceptance evidence. A blocked or unrun check stays blocked; a staged archive is not a release approval. Commit, publish or deploy only within the operator's explicit authorisation after review. Record the final archive digest and review decision. Never include internal evidence containing personal paths or credentials in the public package.
