#!/usr/bin/env python3
"""Portable decimal estimate and project-finance reconciliation engine.

The reusable calculation cascade uses only
the Python standard library and never mutates the input file.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

MONEY = Decimal("0.01")
RATE = Decimal("0.000001")
ZERO = Decimal("0")


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def decimal_value(value: Any, *, field: str = "value") -> Decimal:
    if value in (None, ""):
        return ZERO
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a decimal, not boolean")
    try:
        result = Decimal(str(value).replace(" ", "").replace(",", "."))
        if not result.is_finite():
            raise ValueError(f'{field} must be finite')
        return result
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} is not a valid decimal: {value!r}") from exc


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def rate(value: Decimal) -> Decimal:
    return value.quantize(RATE, rounding=ROUND_HALF_UP)


def parse_date(value: Any, *, field: str) -> date | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise ValueError(f"{field} must use YYYY-MM-DD: {value!r}") from exc


def days360(start: date, end: date) -> int:
    """Excel-compatible DAYS360 US/NASD convention."""
    d1, d2 = start.day, end.day
    if d1 == 31:
        d1 = 30
    if d2 == 31 and d1 == 30:
        d2 = 30
    return (end.year - start.year) * 360 + (end.month - start.month) * 30 + (d2 - d1)


def credit_period_months(start: date, end: date) -> Decimal:
    counted = max(0, days360(start, end))
    return (Decimal(counted) / Decimal(30)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def credit_interest(body: Decimal, monthly_rate: Decimal, start: date, end: date) -> Decimal:
    return money(body * monthly_rate * credit_period_months(start, end))


def named_costs_total(value: Any) -> Decimal:
    if isinstance(value, list):
        total = ZERO
        for index, item in enumerate(value, start=1):
            if isinstance(item, dict):
                total += decimal_value(item.get("amount"), field=f"other_named_costs[{index}].amount")
            else:
                total += decimal_value(item, field=f"other_named_costs[{index}]")
        return money(total)
    return money(decimal_value(value, field="financial.other_named_costs"))


def calculate_items(items: list[dict[str, Any]], warnings: list[str]) -> tuple[list[dict[str, Any]], Decimal]:
    calculated: list[dict[str, Any]] = []
    total = ZERO
    for index, raw in enumerate(items, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"items[{index}] must be an object")
        quantity = decimal_value(raw.get("quantity", "1"), field=f"items[{index}].quantity")
        days = decimal_value(raw.get("days") if raw.get("days") not in (None, '') else '1', field=f"items[{index}].days")
        unit_price = decimal_value(raw.get("unit_price", "0"), field=f"items[{index}].unit_price")
        derived = money(quantity * days * unit_price)
        explicit_present = raw.get("amount") not in (None, "")
        amount = money(decimal_value(raw.get("amount"), field=f"items[{index}].amount")) if explicit_present else derived
        if explicit_present and amount != derived:
            warnings.append(
                f"Line {raw.get('line_no', index)} explicit amount {amount} differs from "
                f"quantity × days × unit price {derived}."
            )
        if quantity < ZERO or days < ZERO or unit_price < ZERO or amount < ZERO:
            warnings.append(f"Line {raw.get('line_no', index)} contains a negative estimate value.")
        total += amount
        calculated.append(
            {
                "line_no": raw.get("line_no", index),
                "category": raw.get("category", ""),
                "name": raw.get("name", ""),
                "contractor": raw.get("contractor", ""),
                "quantity": quantity,
                "days": days,
                "unit": raw.get("unit", ""),
                "unit_price": money(unit_price),
                "derived_amount": derived,
                "amount": amount,
                "amount_mode": "explicit" if explicit_present else "formula",
            }
        )
    return calculated, money(total)


def calculate_credit(
    payments: list[dict[str, Any]],
    manual: list[dict[str, Any]],
    default_rate: Decimal,
    expected_return: date | None,
    warnings: list[str],
) -> tuple[list[dict[str, Any]], Decimal]:
    accruals: list[dict[str, Any]] = []
    total = ZERO
    for index, payment in enumerate(payments, start=1):
        if str(payment.get("source", "")).upper() != "CREDIT":
            continue
        start = (
            parse_date(payment.get("credit_start_date"), field=f"payments[{index}].credit_start_date")
            or parse_date(payment.get("paid_date"), field=f"payments[{index}].paid_date")
            or parse_date(payment.get("planned_date"), field=f"payments[{index}].planned_date")
        )
        if start is None or expected_return is None:
            warnings.append(f"Credit payment {payment.get('id', index)} lacks a complete accrual period.")
            continue
        body = decimal_value(payment.get("amount"), field=f"payments[{index}].amount")
        interest = credit_interest(body, default_rate, start, expected_return)
        total += interest
        accruals.append(
            {
                "source": "payment",
                "id": payment.get("id", index),
                "body": money(body),
                "rate_monthly": rate(default_rate),
                "start_date": start.isoformat(),
                "end_date": expected_return.isoformat(),
                "period_months": credit_period_months(start, expected_return),
                "interest": interest,
            }
        )
    for index, item in enumerate(manual, start=1):
        start = parse_date(item.get("start_date"), field=f"manual_credit_accruals[{index}].start_date")
        end = parse_date(item.get("end_date"), field=f"manual_credit_accruals[{index}].end_date")
        if start is None or end is None:
            raise ValueError(f"manual_credit_accruals[{index}] requires start_date and end_date")
        body = decimal_value(item.get("body"), field=f"manual_credit_accruals[{index}].body")
        monthly_rate = decimal_value(item.get("rate_monthly"), field=f"manual_credit_accruals[{index}].rate_monthly")
        interest = credit_interest(body, monthly_rate, start, end)
        total += interest
        accruals.append(
            {
                "source": "manual",
                "id": item.get("id", index),
                "body": money(body),
                "rate_monthly": rate(monthly_rate),
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "period_months": credit_period_months(start, end),
                "interest": interest,
                "note": item.get("note", ""),
            }
        )
    return accruals, money(total)


def payment_control(payments: list[dict[str, Any]], as_of: date) -> dict[str, Decimal]:
    paid = queued = due_7d = overdue = ZERO
    seven_days = as_of + timedelta(days=7)
    for index, payment in enumerate(payments, start=1):
        amount = money(decimal_value(payment.get("amount"), field=f"payments[{index}].amount"))
        status = str(payment.get("status", "")).upper()
        if status == "PAID":
            paid += amount
            continue
        if status == "CANCELLED":
            continue
        queued += amount
        planned = parse_date(payment.get("planned_date"), field=f"payments[{index}].planned_date")
        if planned is not None and planned < as_of:
            overdue += amount
        elif planned is not None and as_of <= planned <= seven_days:
            due_7d += amount
    return {"paid": money(paid), "queued": money(queued), "due_7d": money(due_7d), "overdue": money(overdue)}


def calculate(payload: dict[str, Any], *, as_of: date | None = None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("estimate root must be a JSON object")
    warnings: list[str] = []
    financial = payload.get("financial") or {}
    if not isinstance(financial, dict):
        raise ValueError("financial must be an object")
    payments = payload.get("payments") or []
    manual_credit = payload.get("manual_credit_accruals") or []
    if not isinstance(payments, list) or not isinstance(manual_credit, list):
        raise ValueError("payments and manual_credit_accruals must be arrays")
    if any(not isinstance(row, dict) for row in payments + manual_credit):
        raise ValueError('payments and manual_credit_accruals must contain objects')
    if not isinstance(payload.get('items', []), list):
        raise ValueError('items must be an array')
    if 'has_vat' in financial and not isinstance(financial['has_vat'], bool):
        raise ValueError('financial.has_vat must be boolean')
    if financial.get('scheme', 'direct') not in ('direct', 'agent'):
        raise ValueError('financial.scheme must be direct or agent')

    calculated_items, estimate_total = calculate_items(payload.get("items") or [], warnings)
    contract_price = money(decimal_value(financial.get("contract_price"), field="financial.contract_price"))
    intermediary_rate = decimal_value(financial.get("intermediary_rate"), field="financial.intermediary_rate")
    scheme = str(financial.get("scheme", "direct")).lower()
    revenue = money(contract_price - contract_price * intermediary_rate) if scheme == "agent" else contract_price
    vat_rate = decimal_value(financial.get("vat_rate"), field="financial.vat_rate")
    has_vat = bool(financial.get("has_vat", False))
    vat = money(revenue * vat_rate / (Decimal(1) + vat_rate)) if has_vat and vat_rate != ZERO else ZERO
    revenue_ex_vat = money(revenue - vat)
    expected_return = parse_date(financial.get("expected_return_date"), field="financial.expected_return_date")
    default_credit_rate = decimal_value(financial.get("credit_rate_monthly"), field="financial.credit_rate_monthly")
    credit_rows, credit_total = calculate_credit(
        payments, manual_credit, default_credit_rate, expected_return, warnings
    )
    bank_guarantee = money(decimal_value(financial.get("bank_guarantee"), field="financial.bank_guarantee"))
    other_costs = named_costs_total(financial.get("other_named_costs"))
    gross_profit = money(revenue_ex_vat - estimate_total - bank_guarantee - other_costs - credit_total)
    tax_rate = decimal_value(financial.get("tax_rate"), field="financial.tax_rate")
    payroll_rate = decimal_value(financial.get("payroll_rate"), field="financial.payroll_rate")
    bonus_rate = decimal_value(financial.get("bonus_rate"), field="financial.bonus_rate")
    tax = money(revenue * tax_rate)
    payroll = money(gross_profit * payroll_rate)
    net_before_bonus = money(gross_profit - tax - payroll)
    bonus = money(net_before_bonus * bonus_rate)
    net_profit = money(net_before_bonus - bonus)
    margin = rate(net_profit / contract_price) if contract_price != ZERO else ZERO
    if contract_price == ZERO:
        warnings.append("Contract price is zero; margin is reported as zero.")

    return {
        "schema_version": 1,
        "source_schema_version": payload.get("schema_version"),
        "version": payload.get("version") or {},
        "as_of": (as_of or date.today()).isoformat(),
        "items": calculated_items,
        "credit_accruals": credit_rows,
        "payment_control": payment_control(payments, as_of or date.today()),
        "financial_result": {
            "contract_price": contract_price,
            "revenue": revenue,
            "vat": vat,
            "revenue_ex_vat": revenue_ex_vat,
            "estimate_total": estimate_total,
            "bank_guarantee": bank_guarantee,
            "other_named_costs": other_costs,
            "credit_interest": credit_total,
            "gross_profit": gross_profit,
            "tax": tax,
            "payroll": payroll,
            "net_before_bonus": net_before_bonus,
            "bonus": bonus,
            "net_profit": net_profit,
            "margin": margin,
        },
        "warnings": warnings,
    }


def json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    return value


def main(argv: list[str] | None = None) -> int:
    configure_console()
    parser = argparse.ArgumentParser(description="Calculate and reconcile an Office Pipeline estimate JSON.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    calculate_parser = subparsers.add_parser("calculate", help="Calculate one estimate JSON.")
    calculate_parser.add_argument("input", type=Path)
    calculate_parser.add_argument("--output", type=Path)
    calculate_parser.add_argument("--as-of", type=str, help="Payment-control date in YYYY-MM-DD.")
    calculate_parser.add_argument("--strict", action="store_true", help="Return exit code 2 when warnings exist.")
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        as_of = parse_date(args.as_of, field="--as-of") if args.as_of else None
        result = json_ready(calculate(payload, as_of=as_of))
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(rendered)
        else:
            sys.stdout.write(rendered)
        return 2 if args.strict and result["warnings"] else 0
    except (OSError, json.JSONDecodeError, ValueError, ArithmeticError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
