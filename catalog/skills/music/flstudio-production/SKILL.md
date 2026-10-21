---
name: flstudio-production
description: Use when an FL Studio session must be planned, inspected, automated or verified ("сделай проект во FL", "разведи микшер", "паттерны", "FLP"): patterns, arrangement, mixer routing, plugin parameters, automation, MIDI import, diagnosis, snapshots and production handoff through an FL Studio MCP bridge, MIDI/Piano Roll scripting or offline FLP analysis. Not for DAW-independent audio processing (audio-production) or writing parts (music-midi-composition).
---

# FL Studio Production

Routes, from safest to most invasive:

- **Route A - offline FLP (PyFLP):** inspect, create from a template, set tempo/metadata/channel names, load and
  arrange samples. Always work on a copy and reopen the result in FL Studio.
- **Route B - live bridge (Flapi / an FL Studio MCP server):** transport, tempo, mixer, channels and narrow live
  expressions. Connect only after the FL-side MIDI setup and a smoke test on a disposable project.
- **Route C - Piano Roll scripts:** transpose, humanise, strum, note repeats, scale fill. Install only into the FL
  user-data directory you actually discovered on this machine.

Public bridges to evaluate: an FL Studio MCP server with offline FLP + Flapi + Piano Roll routes as the primary,
any experimental bridge as secondary. Check each project's licence before installing.

## Live session protocol

1. Verify FL version, project identity, sample rate, tempo, time signature, audio device, headroom and bridge
   connectivity.
2. Inspect before writes: channels, patterns, playlist, mixer routes, peaks, plugin inventory, current selection.
3. Save a new FLP version (and a bridge snapshot) before any batch mutation.
4. Apply the smallest calibrated change; write down the exact target and expected effect.
5. Read back parameters/state and compare measurements. Roll back if the result diverges.
6. Render named stems and a reference mix only after routing and tail lengths are checked.

## Arrangement discipline

Named markers and patterns. Separate musical information from texture. Create contrast by addition, removal,
register, density and space, not only volume. Keep buses explicit: drums, bass, music, lead vocal, doubles/ad-libs,
FX returns, pre-master.

## Versioned session preparation

A helper may prepare a new `50-arrangement/fl-session-NNN/` package: hash-checked sample copies, an FLP from a
template with tempo and playlist read back, and a manifest of proposed bus routing, section markers and automation.
Proposed items are not live changes until applied and read back in FL Studio.

## Compatibility gotchas

- A newer FL version than the bridge's documented target: treat open/save/reopen of a disposable FLP as a required
  compatibility gate.
- PyFLP may warn about unknown records; offline parsing is not a native FL round trip.
- If MIDI loopback ports are missing the live bridge fails to connect; fix the MIDI setup, do not retry blindly.
- If FL Studio is not installed or reachable, produce a complete session blueprint plus a MIDI package instead of
  pretending live changes happened.
- Use only a signed, licensed FL Studio binary. Never automate licence activation, import registry files from
  portable launchers or use cracked builds.

## Acceptance

- [ ] FLP version saved before writes; source FLP untouched.
- [ ] Every change read back and compared with its intended effect.
- [ ] Routing and tails checked before stem/reference renders.
- [ ] Report separates applied changes from proposed ones.
