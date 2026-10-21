# Production packet: КП + workbook, cell map, payments, QA evidence

A reusable recipe for turning one locked estimate into a draft proposal and a calculation workbook whose numbers can be
proved against the estimate calculation (the "oracle").

## Inputs

- Active estimate JSON (see `estimate-production/references/data-contract.md`) and its calculation output.
- Proposal context JSON:

```json
{
  "title": "Коммерческое предложение",
  "intro": "...",
  "schedule": "...",
  "validity": "...",
  "tax_note": "...",
  "assumptions": [],
  "exclusions": [],
  "sources": []
}
```

Missing commercial terms stay visibly unresolved ("уточняется"); never invent a validity period, schedule or tax note.

## Recipe

1. Calculate the estimate (`estimate_engine.py calculate --strict`). Warnings block the packet.
2. Build the workbook from the estimate with formulas for every derived cell (row amounts, totals, VAT, the financial
   cascade). Recalculate it headless so formula caches exist.
3. Build the КП from the same estimate version and the context JSON. The КП shows client prices only.
4. Verify the workbook against the oracle using a workbook map (below).
5. Render every sheet and every page, inspect them, and write the QA evidence file.
6. Update the document register: status `review`, never `approved` from a script.

## Workbook map

```json
{
  "schema_version": 1,
  "checks": [
    {"oracle": "financial_result.contract_price", "sheet": "Финансы", "cell": "B5", "formula": false},
    {"oracle": "financial_result.estimate_total", "sheet": "Финансы", "cell": "B6"},
    {"oracle": "financial_result.net_profit", "sheet": "Финансы", "cell": "B20"},
    {"oracle": "financial_result.margin", "sheet": "Финансы", "cell": "B21"},
    {"oracle": "items.0.amount", "sheet": "Смета", "cell": "G6"}
  ]
}
```

- `oracle` is a dotted path into the calculation output; `formula` defaults to true (the cell must hold a formula).
- Money compares exactly to the kopeck (tolerance 0.01 only if the workbook rounds differently and that is documented);
  margin compares to 6 decimals.
- A missing formula cache (file never recalculated), an error value (`#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`) or a
  formula cell holding a literal blocks the packet.

## Payment parity

The payment register CSV and the `payments` array of the estimate JSON are compared by `id`. Every difference
(amount, status, dates, source) is reported; neither side silently wins. Statuses: `PLANNED`, `TO_PAY`, `QUEUED`,
`PAID` (requires `paid_date`), `CANCELLED`.

## QA evidence (hash-bound)

One JSON entry per delivered artifact:

```json
{
  "path": "03_ДОКУМЕНТЫ/<Project>_КП_<date>_v01.pdf",
  "sha256": "<hash of the artifact>",
  "visual_status": "pass",
  "reviewer": "<who looked>",
  "reviewed_at": "<ISO timestamp>",
  "recalculated_by": "libreoffice-headless",
  "evidence_file": "03_ДОКУМЕНТЫ/qa/<render or contact sheet>",
  "evidence_sha256": "<hash>"
}
```

If the artifact hash changes, its evidence is void and the visual check must be repeated. Document register rows may
carry an optional `estimate_sha256` to bind a document to the exact estimate version.

## Readiness

The packet check ends with `ready_for_authorized_delivery: true|false`. True means "nothing blocks a delivery the
operator authorises", never "send it now".
