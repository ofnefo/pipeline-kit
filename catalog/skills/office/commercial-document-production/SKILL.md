---
name: commercial-document-production
description: Use when a commercial document set must be planned, drafted, versioned or reconciled against an approved estimate - КП/proposals, contracts, appendices, invoices, acts, letters, reports, tender responses, ТЗ, waybills ("подготовь КП", "собери акт", "поставь печати", "ТТН по машинам"). Builds each document from approved facts only, reconciles totals and keeps a document register. Not for estimate calculation (estimate-production) or legal approval.
---

# Commercial Document Production

The document register is the control plane. Each row has a document id, type, title, counterparty, source estimate
version, owner, status, native file, PDF file, approval state and delivery target - see
[references/document-register.md](references/document-register.md).

## Inputs

- The active estimate version and its calculation output.
- Project facts: parties, requisites, dates, tax regime, templates bound to the project.
- Supplied stamp/signature images when documents must be stamped.

Keep organisation facts and templates inside the project. Never pick an organisation profile from a shared/global
location, and never treat a synthetic demo template as approved. Preserve names exactly (including «ё»).

## Workflow

1. Identify the active estimate version and project sources.
2. Resolve the document type and the template bound to the project.
3. Separate provided facts from unresolved fields. Never invent requisites, signatures, dates, tax status or legal
   clauses. A calculated value the operator explicitly asked for is allowed when it is labelled as calculated in the
   document and the register.
4. Draft the native file with the format skill (Word/Spreadsheet/PDF/Presentation) or a template engine (docxtpl).
5. Reconcile every total, line item, date and party name against the approved sources.
6. Render the native file and the PDF; inspect every page.
7. Update the register only to the status actually reached.

## Document families

- **КП / proposal** - scope, assumptions, exclusions, price, validity, schedule, next decision. Client prices only.
- **Contract / appendix / specification** - parties, subject, deliverables, amounts, milestones, acceptance,
  document hierarchy.
- **Invoice / payment request** - exact payer/payee facts, basis, amount, currency, tax treatment, due date.
- **Act / report** - delivered scope, period, evidence, acceptance gaps; signatures stay placeholders until supplied.
- **Letter** - addressee, basis, request/decision, attachments, owner, response deadline.
- **Tender / ТЗ** - requirement matrix: source clause, interpretation, evidence, owner, status.
- **Waybill (ТрН / ТТН)** - one vehicle per document; stamping rules and form notes in
  [references/document-conventions.md](references/document-conventions.md).

Stamps, signatures, act layout, waybill and closing-document conventions: read
[references/document-conventions.md](references/document-conventions.md) before producing acts, waybills, contracts or
contractor closing packets.

## Russian text

КП copy, letters, cover notes and ТЗ prose go through a Russian editing skill (and the genre skill for offers or
instructions). Amounts, requisites, contract clauses and quoted source text stay exact.

## Acceptance

- [ ] Every number and party fact traces to the active estimate or a named source.
- [ ] Unresolved fields are visibly marked, not filled with plausible values.
- [ ] Totals in text, tables and PDF agree to the kopeck.
- [ ] Every page rendered and inspected; stamps/signatures (if any) at consistent size and position.
- [ ] Register row updated to the real status; a changed approved document got a new version.

## Legal and delivery boundary

Label legal text as a draft unless an authorised reviewer approved it. For current law, tax, procurement or
regulatory claims, verify an authoritative source and its effective date. Do not sign, send, upload, approve or pay
merely because the local file is complete.
