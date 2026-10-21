---
name: telegram-group-topics
description: "Use when planning, creating, renaming, closing, reopening or routing work to Telegram forum topics or bot private-chat topics (RU: \"топики\", \"темы в группе\"). Checks forum mode and bot rights, previews a minimal topic set, records every message_thread_id and keeps a purpose-to-thread map. Not for deleting topics without a dedicated confirmation or for routing by visible topic names."
---

# telegram-group-topics

## Purpose
Give a Telegram group (or a bot's private chat) a small, stable topic structure and route work into it reliably.

## Inputs
- Target chat (id), the workflows that need a place (intake, tasks, contractors, per-project), the bot that will manage topics.

## Before proposing anything
- **Supergroup:** forum mode is on and the bot is an admin with `can_manage_topics` (`getChat`, `getChatMember`).
- **Private chat topics** (Bot API 9.4+): the bot's topic mode is enabled and supported for that account.
- Read existing topics first; never assume the list is empty.

## Plan
- Derive a **minimal** topic set from real workflows: stable functional names (e.g. "Inbox", "Tasks", "Contractors") plus one
  topic per active project, not a speculative hierarchy.
- Preview: the chat, topic names, icon colours/emoji, routing rules (what goes where), and collisions with existing topics.

## Execute
1. Create topics (`createForumTopic`) only after explicit confirmation of the preview.
2. Record every returned `message_thread_id` immediately in a local map: purpose -> chat id + `message_thread_id`.
3. Verify routing with a harmless test post only if the operator agreed, before binding tasks or reminders to the topic.
4. Rename (`editForumTopic`), close (`closeForumTopic`) and reopen (`reopenForumTopic`) are separate mutations, each with its own
   exact preview.
5. **Delete** (`deleteForumTopic`) also deletes all messages in the topic: destructive, needs a dedicated confirmation naming the
   topic, never bundled with a reorganisation.

## Gotchas
- The "General" topic has special rules (it can be hidden/renamed but not deleted).
- Sending to a topic needs `message_thread_id`; a missing id silently posts to General.
- Never infer a topic from its visible name: names change and repeat across chats.

## Acceptance checklist
- [ ] Forum mode / topic mode and `can_manage_topics` verified and recorded.
- [ ] Preview confirmed before every mutation; delete confirmed separately.
- [ ] Every `message_thread_id` stored in the purpose map; routing verified.

## Boundaries
No topic mutations without confirmation; no deletes bundled with other changes; no posting into topics beyond an agreed test.
