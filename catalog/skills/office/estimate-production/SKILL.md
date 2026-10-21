---
name: estimate-production
description: Use when a project estimate, budget, payment plan, credit cost, margin or financial result must be built, audited, versioned or reconciled ("смета", "посчитай маржу", "проверь итоги", "НМЦК", "НДС", "кредит по платежам"). Keeps a decimal JSON source of truth, a formula-driven workbook and a calculation oracle that must agree to the kopeck. Not for drafting the КП/contract text (commercial-document-production) or for tax advice.
---

# Estimate Production

This skill owns the business model and the reconciliation. Use a spreadsheet skill (or openpyxl) for the Excel
artifact itself.

## Inputs

- Project config, the active estimate JSON and/or workbook, the payment register.
- Contract inputs: price, currency, VAT/tax regime, direct or agency scheme.
- Researched prices with source and date.

## 1. Establish the source of truth

- If only a workbook exists, keep it and extract its assumptions/formulas into a JSON counterpart.
- If only JSON exists, build the workbook from the same named assumptions.
- Never merge several "final" estimates silently: choose one active version, keep the others as history.

## 2. Model explicitly

Keep these groups separate:

- contract inputs: price, currency, VAT/tax mode, intermediary scheme;
- estimate rows: category, item, contractor, quantity, days, unit, unit price, amount, comment, source, verified date;
- project costs: bank guarantee, logistics, contingency, other named costs;
- credit: body, monthly rate, start and expected return dates;
- payments: contractor, purpose, source, status, planned/paid dates;
- result: revenue, VAT, revenue ex VAT, estimate total, credit cost, gross profit, tax, payroll, bonus, net, margin.

Formulas: [references/financial-model.md](references/financial-model.md). JSON fields:
[references/data-contract.md](references/data-contract.md). Layout and pricing conventions (internal vs client file,
НМЦК ceiling, markup, VAT wording, reserves): [references/estimate-conventions.md](references/estimate-conventions.md).

## 3. Calculate (decimal oracle)

```bash
python scripts/estimate_engine.py calculate <estimate.json> --output <calc_v001.json> [--as-of YYYY-MM-DD] [--strict]
```

- Output files are create-only: use a new versioned name per run.
- Every difference between an explicit row amount and `quantity × days × unit_price` is a warning, including one
  kopeck. Null `days` = 1. `--strict` exits 2 on any warning.
- Payment control (paid / queued / overdue / due in 7 days) is computed against `--as-of`.

## 4. Reconcile the workbook

- Derived cells contain formulas, never pasted oracle results. Assumptions live in visible, named input cells with
  comments for non-obvious values.
- Recalculate headless, then compare workbook cells to the oracle: money to 0.01, percentages to the documented
  precision. Explain any intentional difference before approval.
- Render every sheet and look for `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, truncated cells and hidden rows that
  carry money.

## 5. Version and approve

- Version statuses: `working`, `review`, `approved`, `superseded`. A change to an approved estimate creates a new
  version; never hide a price change inside formatting.
- Before approval check row formulas, category totals, tax treatment, credit dates, contingency, payment plan,
  document totals and formula errors. Approval is a project decision, not a side effect of a calculation.
- Text around the numbers (assumption notes, КП summary) may go through a Russian editing skill; it never touches
  amounts or formulas.

## Edge rules

- Decimal strings for serialised money and rates; no binary floats as canonical state.
- Keep a negative margin visible; never clamp a loss to zero.
- Missing VAT/tax settings are unresolved, not a licence to guess.
- DAYS360 (US/NASD) credit math is a selectable convention; name it in the assumptions when used.
- Research current rates and laws from authoritative sources when the operator did not supply them; record the date.

## Acceptance

- [ ] One active version; oracle run with `--strict` has no unexplained warnings.
- [ ] Workbook matches the oracle on every mapped cell; no formula errors.
- [ ] Internal and client files agree on totals; the client file carries no internal markup or notes.
- [ ] Tax regime, credit convention and price sources are stated in the assumptions.
