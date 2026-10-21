# Financial model

The default cascade follows a common agency project-finance model and must be overridden when the project contract or accountant uses another convention.

## Revenue

- Direct scheme: `revenue = contract_price`.
- Agent/intermediary scheme: `revenue = contract_price - contract_price × intermediary_rate`.

## VAT and profit

When the configured price includes VAT:

`vat = revenue × vat_rate / (1 + vat_rate)`

`revenue_ex_vat = revenue - vat`

`gross_profit = revenue_ex_vat - estimate_total - bank_guarantee - credit_interest - other_named_costs`

`tax = revenue × tax_rate`

`payroll = gross_profit × payroll_rate`

`net_before_bonus = gross_profit - tax - payroll`

`bonus = net_before_bonus × bonus_rate`

`net_profit = net_before_bonus - bonus`

`margin = net_profit / contract_price` when contract price is non-zero.

The default model calculates payroll and bonus from signed profit values. A loss can therefore produce negative allocations. Do not “fix” that silently; if the business wants zero floors, record and approve the changed convention.

## Estimate rows

Preferred derived row amount:

`amount = quantity × days × unit_price`

Treat missing/null `days` as 1. An explicit amount may override the derived value only when the row explains why. The oracle reports a warning for every difference from the rounded derived value, including one kopeck.

## Credit

The default period uses Excel-compatible 30/360 (US/NASD):

`period_months = ROUND(DAYS360(start_date, end_date) / 30, 2)`

`interest = body × monthly_rate × period_months`

For credit-funded payments, the start date is `credit_start_date`, then `paid_date`, then `planned_date`. The default end date is the expected customer payment/return date.

## Payment control

- `paid`: status is `PAID`.
- `queued`: every non-paid, non-cancelled payment.
- `overdue`: queued and planned date is before the as-of date.
- `due_7d`: queued and planned date is from the as-of date through seven calendar days.

Payment status totals do not prove bank settlement; reconcile them against an authorized source when settlement matters.
