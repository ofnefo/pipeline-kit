---
name: telegram-contact-organizer
description: "Use when organising imported Telegram contacts, chats and channels into collections, tags, chat folders or reviewed matches with people in a directory (RU: \"разбери контакты\", \"папки в телеге\"). Keeps imports as evidence, writes a local overlay, sends ambiguous matches to review and previews bulk changes. Not for editing source records directly or for merges, deletes or Telegram contact changes without a dedicated confirmation."
---

# telegram-contact-organizer

## Purpose
Make a large Telegram contact and chat list usable (collections, tags, folders, links to known people) without corrupting the
imported data or the operator's account.

## Inputs
- An import of contacts/dialogs (export file or authorised account read), the operator's people directory, desired collections.

## Data model
- **Imported rows are evidence**, never edited in place.
- A **local overlay** keyed by internal person id + verified Telegram numeric user id holds tags, collections and notes.
- One person can be in several collections and carry tags such as role, city, project, priority, relationship.
- **Chat folders** (Telegram's own dialog filters) are separate from collections; link them explicitly when wanted.
- One shared service writes the overlay; every UI (bot, app, agent) uses it.

## Workflow
1. Normalise for matching (phone E.164, lowercase username, trimmed names) but keep originals.
2. Match on numeric Telegram id first, then phone, then username; a repeated phone or username is a signal, not proof.
3. Ambiguous and many-to-one matches go to a **human review list**, never auto-resolved.
4. Propose collections/tags/folders as a **bulk preview**: included | excluded | ambiguous | unchanged, with counts and samples.
5. Apply to the overlay after confirmation; store a receipt.
6. Merges, deletes and external changes (adding/removing Telegram contacts, editing folders in the account) each need a
   **dedicated confirmation** and a reversible receipt (before/after state).

## Gotchas
- Usernames are reassigned; display names are not identity.
- Phone formats vary by country; never match on the last digits only.
- Telegram folder limits (count, chats per folder) depend on account type; check before proposing.

## Acceptance checklist
- [ ] Source import untouched; overlay holds every change.
- [ ] Each match states its basis (id / phone / username) and confidence.
- [ ] Ambiguous items listed for review, not resolved.
- [ ] Bulk preview confirmed; receipt stored; external changes confirmed separately and reversible.

## Boundaries
No direct edits of source records; no merges, deletes or account-side contact/folder changes without a dedicated confirmation;
no enrichment of people from outside sources.
