---
name: game-art-production
description: Use when a game needs sprites, textures, tiles, characters, environments, icons or concept art and they must work in-engine ("арт для игры", "спрайты", "тайлы", "иконки", "game art"). Runs gameplay requirement -> blockout -> visual test -> asset brief -> generation or reference -> implementation -> in-game verification, with provenance and licence facts per asset. Not for engine code (godot-development), asset package intake (game-pipeline) or non-game illustration.
---

# Game art production

Purpose: art that serves gameplay and is proven in the engine, with a provenance record for every asset.

## Inputs

- The gameplay requirement: what the asset must communicate (function, state, threat, interactable).
- Engine, camera, target resolution, pixel density or texel density, palette and the art direction references.

## Workflow

1. **Gameplay requirement:** write what the player must read from the asset.
2. **Blockout:** grey boxes or placeholder shapes at real scale in the engine.
3. **Visual test:** check scale, silhouette and readability with the blockout in real camera and lighting.
4. **Asset brief:** exact dimensions, format, palette, states/frames, pivot, import settings, references.
5. **Generation or reference:** generate only raster deliverables (sprites, textures, concept, backgrounds) with an
   image model you are licensed to use, or produce them by hand/3D. Keep UI widgets, icons that need crisp scaling and
   text native (vector or engine UI), not generated.
6. **Implementation:** import with correct settings (filter, mipmaps, compression, pivot, scale).
7. **In-game verification:** look at it in the running game.
8. **Refinement:** fix what the in-game check showed.

No final art before scale, function and dimensions are known.

## Provenance record (per asset)

| Field | Content |
|---|---|
| author / tool | person or pipeline that made it |
| model | model name and version, if generated |
| date | creation date |
| inputs | prompt, references, seed or source files |
| licence | licence of the result and of every input |
| commercial use | yes / no |
| protected IP | any relation to existing characters, brands or styles |
| acceptance | who/what check accepted it, and the capture |

Assets come into the project through the asset package flow in `game-pipeline` (manifest with hashes and roles).

## In-engine checks

- Silhouette readable at gameplay distance and size.
- Contrast against real backgrounds and lighting, including dark and busy areas.
- Scale consistent with characters and the 1 m (or one-tile) reference.
- Readability of states (idle, active, damaged, disabled).
- Import settings correct (pixel art: nearest filter, no mipmaps; 3D: metres, correct normals).

## Acceptance checklist

1. Gameplay requirement written before production; blockout tested at real scale.
2. Every asset has a provenance record with licence and commercial-use facts.
3. Checked in the running game: silhouette, contrast, scale, readability, import settings; capture saved.
4. UI and text kept native, not baked into generated images.

## Boundaries

Game art from requirement to in-engine proof. Code is `godot-development`; packages and manifests are `game-pipeline`;
HUD layout is `game-ui-ux`.
