---
name: telegram-inbox-briefing
description: "Use when reviewing Telegram chats, watched chats or a bounded message window to prepare a concise briefing, action candidates and reply drafts (RU: \"что в телеге\", \"разбери входящие\", \"сводка\"). Produces a traceable briefing in fixed buckets and local drafts. Not for sending, scheduling or auto-replying."
---

# telegram-inbox-briefing

## Purpose
Turn a bounded slice of Telegram into a short, traceable briefing the operator can act on.

## Inputs
- Scope: chats, topics and a time window (from/to) or "since last briefing".
- Source: the authorised live Telegram session (bot or personal account the operator connected). A local message archive is used
  only when the operator asks for historical search or live pagination cannot reach the period.

## Workflow
1. **Bound the review** by chats, topics and time. Say what was not covered.
2. **Read and keep references** (chat id, `message_thread_id`, message id, sender id) internally so every conclusion is traceable.
3. **Sort into buckets:**
   - Needs reply
   - Proposed tasks
   - Deadlines
   - Decisions made
   - Waiting on others
   - Informational
4. **Mark provenance:** "direct request" (someone asked) vs "inferred" (the model's suggestion), plus uncertainty.
5. **Draft replies** as local records only: requested tone, enough surrounding context for review, the target message reference.
6. When the operator picks an action: tasks go through `telegram-task-capture`; sends go through your preview -> confirm -> receipt
   path.

## Briefing format
```
<scope: chats/topics, window, source>  <n> messages read, <m> not reachable
Needs reply (k)
- [chat/topic] who: one line - ref <msg-ref> - direct|inferred
Proposed tasks / Deadlines / Decisions / Waiting on / Info
...
Drafts: <n> local drafts (not sent)
```

## Watches
A watch (recurring check of selected chats) stays **quiet** until a meaningful event appears (a direct question, a deadline, a
mention); no "nothing new" pings.

## Privacy
- Do not put unrelated private message bodies into logs, reports, tests or fixtures; quote only what the briefing needs.
- Fixtures for tests are synthetic.

## Acceptance checklist
- [ ] Scope and gaps stated at the top.
- [ ] Every item has a message reference and a direct/inferred mark.
- [ ] Drafts are local; nothing was sent or scheduled.
- [ ] No private bodies outside the briefing itself.

## Boundaries
A request for a briefing never authorises sending, scheduling, reacting or marking messages as read on the operator's behalf.
