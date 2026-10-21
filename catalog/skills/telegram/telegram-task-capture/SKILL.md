---
name: telegram-task-capture
description: "Use when turning free-form notes or Telegram messages into reviewable tasks with dates, assignees, group/topic routing and reminders, or when changing task status or announcing tasks in Telegram (RU: \"создай задачу\", \"запиши в задачи\"). Extracts only supported facts, previews a batch, writes after explicit confirmation with a receipt. Not for sending messages without confirmation or for building a second task store."
---

# telegram-task-capture

## Purpose
Capture tasks from chats and notes into **one** task store your assistant already has (app, bot and agent tools all write to the
same entity). Telegram is a source and an optional notification target, never a parallel store.

## Inputs
- Free text, one or more forwarded messages, or a message window (chat id + message ids).
- The task store's create/update preview path, the project list, people/assignee directory, the chat-and-topic routing map.

## Workflow
1. **Extract only supported facts:** title, due date (with time zone), assignees, project, source chat/message reference, intended
   notification topic. Keep the original text as provenance.
2. **Mark uncertainty** (relative dates such as "next Friday", ambiguous names, unknown project) for review instead of guessing.
3. **Multiple lines** -> one draft per line, shown as a compact batch preview (title | due | assignee | project | topic | flags).
4. **Deduplicate** against open tasks by normalised title + source reference. Similar is not identical: never auto-merge.
5. **One durable preview** per write: exact arguments for the task write and any Telegram announcement, plus a preview hash.
6. **Execute only after explicit confirmation** of that preview hash. Persist a receipt (task id, message id, hash, timestamp).
7. **Verify** the stored task and, if requested, the Telegram message (chat id + `message_thread_id` + message id).
8. An uncertain send (timeout, unknown result) is **not retried automatically**; check first, then ask.

## Status changes
Completion, cancellation and reopening update the existing task. If a status change also posts to Telegram, that post is a
separate confirmed action.

## Telegram-native checklists
A Telegram checklist is not your task store. `sendChecklist` (Bot API 9.1+) works on behalf of a connected **Telegram Business**
account; treat a checklist as an optional projection after capability and account checks, and keep the canonical record in the
task store.

## Gotchas
- Dates in chats are relative to the message time, not to "now"; resolve them against the message timestamp and time zone.
- Usernames change; resolve people by numeric Telegram user id or by your directory id.
- Routing by visible topic name is fragile; use the stored chat id + `message_thread_id` map.

## Acceptance checklist
- [ ] Every draft carries the source reference and original text.
- [ ] Uncertain fields are flagged, not invented.
- [ ] Batch preview shown; duplicates reported, not merged.
- [ ] Write happened only after confirmation of the exact preview hash; receipt stored.
- [ ] Task and any message verified after the write.

## Boundaries
No sends, edits or deletes in Telegram without explicit confirmation; no second task store; no automatic retry of uncertain sends.
