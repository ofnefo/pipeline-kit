---
name: resolve-production
description: Use when a cut, grade, Fusion/Fairlight pass or delivery is done in DaVinci Resolve ("монтаж в Резолве", "цветокор", "экспорт из Resolve"). Plans, hands off, inspects and finishes Resolve work (media pool, timelines, rough/fine cuts, markers, colour, Fusion, Fairlight, delivery); on the free edition it hands over OTIO/XML/EDL timelines for manual import, on Studio it can drive Resolve through its scripting API. Not for generated footage (neural-video), motion graphics or After Effects compositions.
---

# Resolve production

Purpose: get an edit into, through and out of DaVinci Resolve safely, whether or not Resolve can be scripted on this
machine.

## Inputs

- The edit plan or editorial timeline (OTIO preferred), source media paths, frame rate, resolution and delivery spec.
- Which Resolve edition is installed (free or Studio) and whether external scripting is enabled.

## Free vs Studio: check first

| Capability | Free | Studio |
|---|---|---|
| External scripting API (`DaVinciResolveScript`, `scriptapp("Resolve")`) | no (returns `None`) | yes, with Preferences > System > General > External scripting = Local |
| Internal scripts (Workspace > Scripts) | Lua only, sandboxed, no file IO | Lua and Python |
| Resolve MCP servers / inbox bridges | cannot run | can run |
| Timeline import (OTIO, FCP7 XML, FCPXML, EDL, AAF) | yes, manual | yes, manual or scripted |

Record the version and edition you found, with the evidence (the `scriptapp` result, the Scripts menu contents).

## Workflow on free (files plus a click plan)

1. Write the editorial timeline as `50-edit/<plan>/timeline.otio`.
2. If Resolve needs another format, convert headlessly with OpenTimelineIO adapters
   (`otioconvert -i timeline.otio -o timeline.xml`, or `.edl`/`.fcpxml` via the matching adapter plug-in).
3. Give the operator a short click plan: File > Import > Timeline, with "automatically import source clips into
   media pool" enabled; which bin; which settings to confirm (frame rate, start timecode).
4. If no Resolve-only work is needed (grade, Fairlight), render the master with FFmpeg or another headless tool instead.

## Workflow on Studio (scripted)

1. Health check: connect, read the current project, timeline, frame rate and resolution before any mutation.
2. Save or snapshot (duplicate the timeline) before scripted changes.
3. Translate the request into a compact operation plan: bins, selects, markers, tracks, in/out points, transitions,
   render settings.
4. Apply reversible edits first. Ask before destructive deletion, mass relink, timeline replacement or render-queue
   replacement.
5. Inspect the resulting timeline, save, render a short preview when the risk warrants it, verify frames, duration and
   audio.

## Techniques and gotchas

- Never relink or delete broadly from an assumed active timeline; name the project and timeline explicitly.
- Keep VFX and motion shots as versioned components rendered elsewhere (After Effects, Fusion standalone, generated
  clips), then relink or import the returned renders.
- Resolve is a heavy GPU application: snapshot GPU/VRAM and running jobs before launching it, and take the GPU lock
  (one heavy GPU job at a time) for renders. Close only an instance you started; never save the operator's own
  projects from a script.
- Check delivery loudness and format after render (`ffprobe`, two-pass `loudnorm` measurement), not just in the Deliver
  page settings.
- Do not rely on built-in AI assistants without evaluating them on the project's own material.

## Acceptance checklist

1. Edition and scripting availability recorded with evidence.
2. Imported timeline matches the plan: clip count, total duration, frame rate, start timecode.
3. No offline media; every source clip resolves to the intended file.
4. Render matches the delivery spec (codec, size, fps, duration, audio layout, loudness).
5. A snapshot or duplicate exists from before any scripted change.

## Boundaries

Resolve editorial, colour, Fairlight and delivery work only. Generated footage is `neural-video`; graphic layers are
`motion-graphics`; compositions and templates are `after-effects-production`.
