# Telegram compatibility baseline

Baseline checked: 2026-09-04. **Re-verify against the official changelog before relying on any line below.**

Official sources:
- Bot API reference: https://core.telegram.org/bots/api
- Bot API changelog: https://core.telegram.org/bots/api-changelog
- Forum topics: https://core.telegram.org/api/forum
- Checklists (to-do lists): https://core.telegram.org/api/todo

## Features by Bot API version (newest first)

| Version | Feature | Notes for an assistant |
|---|---|---|
| 10.3 | Rich message buttons, document blocks, compact tables, expandable quotes | Capability-flag; fall back to plain text with links |
| 10.1 | `sendRichMessage`; ephemeral `sendRichMessageDraft` | Draft is a preview only; always finish with a real send |
| 9.5 | `sendMessageDraft` available to all bots; member tags | Use for streamed replies; stop on error |
| 9.4 | Topics in private chats with bots | Check that topic mode is enabled before routing |
| 9.1 | Checklists (`sendChecklist`) via connected Business accounts | Optional projection of tasks, not a task store |

## Library notes
- A maintained Python wrapper (python-telegram-bot, LGPL-3.0) supported Bot API 10.0 at the baseline date; check its release notes
  for the version you need before switching from a raw-HTTP adapter.
- A user-account (MTProto) client stays a separate transport.

## Capability matrix template

| Feature | Official (version, date) | Our adapter | Wrapper | Fallback | Flag |
|---|---|---|---|---|---|
| | | yes/no | version or no | plain message / none | name |
