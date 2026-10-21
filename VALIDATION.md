# Validation status

Initial runtime baseline checked on Windows with Python 3.12 on 2026-10-21. Later updates are listed separately below. Review is proportional to the actual change under docs/RELEASE.md; this file is not publication approval. Private paths, raw operator receipts and personal scan terms are excluded from the package.

## Completed checks

- Fresh virtual environment: exact core, test and Office requirements installed; `pip check` passed. No canonical source tree or globally installed creative application is required for Control startup.
- 27 automated tests passed with no skips: local API/UI data contracts, optimistic task updates, NameNode claim conflicts, file upload/quarantine/restore and private-path rejection, missing project text-file creation and stale-write conflicts, filesystem error responses, upload free-space reserve, image conversion, SMM local export, chat persistence, local-model protocol boundaries, Office calculations/intake, graphic composition/print preflight, offline web audit, production CLI entrypoints and release boundaries.
- Importing Control did not open a connection, start a thread/process or create workspace state. Loopback/origin boundaries and disabled generation routes were tested.
- 64 Python files parsed and 38 JavaScript files passed syntax checks. The explicit 177-file release list passed both generic and operator-specific privacy scans. All 128 recorded upstream source hashes matched the selected read-only sources.
- Archive extraction into a different directory verified every member against its build manifest; initialization, capability doctor, local NameNode CLI and the integration suite ran successfully there using the clean environment.
- Browser journeys at 1440 and 375 pixels passed: create project → Studio → project visible in Projects; create task → reload → task persists. Navigation produced 16 screenshots across Home, Projects, Tasks, Studio, Converters, Skills, SMM and Settings, without script errors or horizontal document overflow. The existing Control layout was preserved. Visual review exposed a misleading monitoring status and a project-list filter mismatch; both were corrected and checked again.
- FFmpeg/ffprobe 8.1.2 CPU integration: a synthetic source produced a 48-frame, 320×180, 24 fps, two-second H.264 montage; stale sequence edits were rejected and source bytes preserved. Audio mastering produced an eight-second 48 kHz, 24-bit WAV at −16.05 LUFS; duration, loudness tolerance and true-peak checks passed.

## Agent workflow update — 2026-10-21

- Added the portable `ui-delivery` skill and working-method guide; the `web` profile selects the skill for Codex and Claude. The release allowlist now contains 191 files.
- Nine focused setup/release tests passed. Installation from an archive extracted into a separate directory installed the selected web skills for both clients; installed skill bytes matched the packaged source. Repeating installation reported unchanged files.
- Privacy scanning and local links in the changed guides passed. Runtime, dependencies and UI code are unchanged; the browser and media checks above describe the initial baseline and were not rerun for this instruction update.

## Skills catalog update — 2026-10-21

- Added `catalog/` (69 authored skills cleaned for publication, `catalog/index.json` with 55 third-party skills pinned to an upstream commit with a checked licence) and `docs/SKILLS.ru.md`. Third-party files are not copied; owner-specific skills were excluded. `tools/setup_skills.py --skills` installs an authored catalog skill by name and refuses a third-party name with its upstream link. The release allowlist now contains 421 files.
- 34 repository tests passed (one optional Office test skipped without its environment), including catalog/tree consistency and frontmatter checks; the bundled tests of `change-review`, `video-watch` and `design-production-preflight` passed. Privacy scanning of the release list and local links in the changed documents passed. Runtime and UI code are unchanged; browser and media checks were not rerun.

## Boundaries and remaining acceptance

Requested profile-driven panel composition remains unfinished. The questionnaire selects installation components, but the current UI does not hide unselected sections. No user decision waived this outcome. Acceptance still requires saved panel choices, matching navigation and a browser journey for tasks + editing after reload; instruction and installer checks do not complete that UI requirement.

Browser file upload/edit and local export are covered at the API/integration level, not by complete browser journeys. The optional local-chat transport is covered with protocol fixtures, not a running model. PDF/LibreOffice/Pandoc/OpenTimelineIO extras, live models, optional editor integrations and macOS/Linux installation have not been validated. No creative listening judgment is claimed from a synthetic audio measurement. Native applications, third-party SDK trees and model weights are not bundled.

No cloud/GPU inference, remote host scans, external messaging, scheduled jobs, production deploy or public upload was used for these checks. The release owner records the final archive digest and independent review receipts externally; changing approved code invalidates the relevant checks and requires a new candidate.
