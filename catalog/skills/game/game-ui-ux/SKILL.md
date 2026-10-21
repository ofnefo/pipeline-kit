---
name: game-ui-ux
description: Use when designing or reviewing game HUD, menus, tooltips, feedback, input prompts or readability ("интерфейс игры", "HUD", "меню", "непонятно игроку", "game UI"). Checks that the player can always see threats, knowledge, failure reasons, resources and what changed, then verifies the UI in the running game at several resolutions and with keyboard/mouse and controller. Not for engine code (godot-development), art production (game-art-production) or web/app UI.
---

# Game UI/UX

Purpose: a game interface that answers the player's questions at a glance and is verified in the real game, not in
mock-ups.

## Inputs

- The current build and the mechanic or screen in question.
- Target platforms, input devices and minimum resolution.

## The five player questions

At any moment the UI must let the player answer:

1. What threatens me, and what does it intend to do?
2. What do I know (and what is still hidden)?
3. Why did my action fail or get blocked?
4. What resources do I have, and is the game paused?
5. What just changed?

## Rules

- Stable hierarchy: the same information lives in the same place on every screen.
- Explain blocked actions with a reason, not just a disabled button.
- Never rely on colour alone: duplicate colour meaning with an icon, shape or text.
- Keep presentation state (animations, tweens, hover) separate from game state; UI requests, the game decides.
- Support keyboard/mouse and controller focus navigation; every interactive element is reachable and shows focus.
- Test at 1280x720, 1920x1080 and at least one other aspect ratio (ultrawide or 16:10, or portrait for mobile).
- Text stays readable at the minimum resolution; no text baked into images that need translation.
- One icon set and one visual language across HUD and menus.

## Workflow

1. List the states the screen can be in (normal, blocked, empty, low resource, paused, game over).
2. Map each of the five questions to a UI element for those states.
3. Implement or adjust, keeping UI non-authoritative.
4. Walk every state in the running game with both input methods and at all test resolutions; capture each.
5. Fix overlap, clipping, unreadable text and missing reasons; re-capture only the changed states.

## Acceptance checklist

1. All five questions answerable in every listed state.
2. Captures at 1280x720, 1920x1080 and one other aspect, no overlap or clipping.
3. Keyboard/mouse and controller focus both walked through every interactive element.
4. Colour meaning duplicated; blocked actions show a reason; one icon set.

## Boundaries

Game interface design and verification. Code changes are `godot-development`; art assets are `game-art-production`;
full playtests are `playtest-qa`.
