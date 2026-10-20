---
name: video-editing
description: Use when reviewing source footage, annotating edits, building CPU video timelines or exporting montage revisions in Pipeline Kit.
---

# Video review and editing

Read `docs/MODULES.md`. Resolve the named project under the configured workspace and define duration, aspect, delivery codec, reference look and audio target. Use a lowercase hyphenated slug. Check FFmpeg/ffprobe availability before rendering. Do not start GPU or cloud jobs; no generation worker is included.

Open the project in Studio → Montage. Import project-owned footage, inspect it with timestamps, and save comments or ranges. Task handoffs are board records only. Select a version explicitly and preserve sources. For scripted work inspect `modules/video/scripts/editorial.py --help` and `montage.py --help`; each subcommand documents exact project/spec arguments. Keep edit specs and output receipts with the project.

Review a draft before a master. Check actual transitions, first/last frames, captions, geometry, duration, frame rate and audio synchronisation. Listen to the result and check loudness/true peak using the chosen profile. FFmpeg success alone is not visual/audio approval. Do not approve an edit from filenames or an inherited machine receipt.

Acceptance: a playable local output exists, probe metadata matches the requested format, sources were preserved, representative frames and audio were reviewed, and remaining creative feedback is explicit. Timeline interchange requires the optional OpenTimelineIO dependency. FilmCraft, EffectCraft, OpenMontage and neural workflows require separate adapters and are not promised by this skill.
