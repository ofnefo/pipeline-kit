---
name: telegram-api-modernization
description: "Use when adding or reviewing support for new Telegram Bot API or account features in an assistant (rich messages, drafts, checklists, topics, business features), choosing a bot library, or borrowing architecture ideas from open-source bot frameworks. Builds a capability matrix, adds typed methods with fallbacks and adapter tests. Not for sending real messages during development or copying code from copyleft projects."
---

# telegram-api-modernization

## Purpose
Keep a Telegram integration current without rewrites: new API features land as typed, capability-checked, tested methods with a
safe fallback, and outside ideas are adopted clean-room.

## Inputs
- The integration's current transport(s): typically a typed raw-HTTP Bot API adapter and, separately, a user-account (MTProto)
  client for the personal account.
- The official sources: Bot API reference, Bot API changelog, forum and checklist docs (see `references/compatibility.md`).
- The feature the operator wants (e.g. streamed drafts, rich messages, private-chat topics).

## Architecture rules
- Keep the typed raw-HTTP Bot API adapter while wrapper libraries lag behind the official API. Adopt a wrapper only when it covers
  the needed API version and removes real code.
- Keep the user-account transport separate from the bot transport; never route bot features through the personal account.
- Do not add a second bot runtime just to get nicer abstractions.

## Patterns worth adopting (clean-room)
- **Capability negotiation:** probe or configure what the chat/account supports before choosing a method.
- **Typed events:** parse updates into typed objects; unknown fields are ignored, never fatal.
- **Narrow plugins:** each feature is a small module with explicit permissions.
- **Middleware vs policy:** transport middleware (retry, rate limit, logging) is separate from policy (who may do what).
- **Workflow triggers:** commands and events map to named workflows, not ad-hoc handlers.
- **Adapter tests:** every method has fixture tests for request shape and response parsing.

## Change protocol
1. **Capability matrix** for the feature: official API (version, date) | current adapter support | wrapper support | fallback.
2. **Capability flag** per feature; when off or unsupported, fall back to a plain `sendMessage` with equivalent text.
3. **Unknown update fields** must not crash polling or webhooks; log them at debug level.
4. **Write methods** are typed, bounded (lengths, counts), permission-checked, previewed, idempotent (client key or dedupe),
   receipted and verified after the call.
5. **Tests:** fixture tests first, then a staging bot in a test chat; never test against real contacts or production chats.
6. Record the baseline date in `references/compatibility.md` and re-check the changelog before each change.

## Gotchas
- Ephemeral draft methods (streamed "typing" previews) are not messages: always finish with a real send, and stop drafting on error.
- Business-account features (e.g. checklists) need a connected business account and its permissions.
- Topic routing needs `message_thread_id`; a missing id posts to the General topic.
- Library licences differ (LGPL, AGPL, MIT). Ideas are free; copying code or text from copyleft projects is not.

## Acceptance checklist
- [ ] Capability matrix with official source and date.
- [ ] Feature behind a flag with a plain-message fallback.
- [ ] Unknown fields tolerated; adapter fixture tests pass.
- [ ] Staging-bot test receipt; no real chats touched.
- [ ] Any borrowed idea credited in NOTICE.md if its licence allows; no copied copyleft code or text.

## Boundaries
No real sends during development; no new runtime without a measured need; no copied AGPL/LGPL/GPL code or text.
