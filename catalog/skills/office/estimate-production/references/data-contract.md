# Estimate data contract

Canonical estimate JSON uses decimal strings for money and rates.

```json
{
  "schema_version": 1,
  "version": {"id": "v001", "status": "working"},
  "financial": {
    "contract_price": "0.00",
    "has_vat": false,
    "vat_rate": "0",
    "tax_rate": "0",
    "payroll_rate": "0",
    "bonus_rate": "0",
    "bank_guarantee": "0.00",
    "other_named_costs": "0.00",
    "scheme": "direct",
    "intermediary_rate": "0",
    "credit_rate_monthly": "0",
    "expected_return_date": null
  },
  "items": [],
  "payments": [],
  "manual_credit_accruals": []
}
```

Estimate item fields: `line_no`, `category`, `name`, `contractor`, `quantity`, `days`, `unit`, `unit_price`, optional `amount`, `comment`, `source` and `verified_at`.

Payment fields: `id`, `contractor`, `purpose`, `amount`, `source` (`CREDIT`, `OWN`, `CUSTOMER_ADVANCE`), `status`, `planned_date`, `paid_date` and `credit_start_date`.

Manual credit fields: `body`, `rate_monthly`, `start_date`, `end_date` and `note`.

Do not store signatures, credentials, secret tokens or unrestricted external filesystem paths in this file.
