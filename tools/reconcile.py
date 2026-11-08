#!/usr/bin/env python3
"""Independent settlement reconciliation check.

Compares a settlement file against the payment event ledger and reports
matched, missing-authorization, duplicate-settlement, amount-mismatch and
delayed-settlement rows. This is intentionally a second implementation of the
Java reconciliation logic, mirroring how a payments team uses an independent
control alongside the service.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _amount(value: str | int | None) -> int:
    if value is None or value == "":
        return 0
    return int(str(value).replace(",", ""))


def reconcile(settlements: list[dict[str, str]], ledger: list[dict[str, str]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in ledger:
        grouped[row["rrn"]].append(row)

    counts = {
        "matched": 0,
        "missing_authorization": 0,
        "duplicate_settlement": 0,
        "amount_mismatch": 0,
        "delayed_settlement": 0,
    }
    breaks: list[dict[str, Any]] = []

    for row in settlements:
        rrn = row["rrn"]
        expected = _amount(row.get("amount_cents"))
        events = grouped.get(rrn, [])
        authorizations = [
            event for event in events
            if event.get("event_type") == "AUTHORIZATION" and event.get("status", "APPLIED") == "APPLIED"
        ]
        settled = [
            event for event in events
            if event.get("event_type") in {"SETTLEMENT", "CLEARING"}
            and event.get("status", "APPLIED") == "APPLIED"
        ]

        if not authorizations:
            kind = "MISSING_AUTHORIZATION"
            detail = "No applied authorization for this RRN."
            actual = None
        elif len(settled) > 1:
            kind = "DUPLICATE_SETTLEMENT"
            detail = f"Multiple applied settlement events: {len(settled)}."
            actual = _amount(settled[0].get("amount_cents"))
        elif not settled:
            kind = "DELAYED_SETTLEMENT"
            detail = "Authorization present but no settlement applied."
            actual = None
        elif _amount(settled[0].get("amount_cents")) != expected:
            kind = "AMOUNT_MISMATCH"
            detail = "Settlement amount does not match the submitted clearing amount."
            actual = _amount(settled[0].get("amount_cents"))
        else:
            kind = "MATCHED"
            detail = "Matched."
            actual = expected

        counts[kind.lower()] += 1
        breaks.append(
            {
                "rrn": rrn,
                "break_type": kind,
                "expected_cents": expected,
                "actual_cents": actual,
                "detail": detail,
            }
        )

    return {
        "summary": {"total_rows": len(settlements), **counts},
        "breaks": breaks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile settlement rows against a payment ledger.")
    parser.add_argument("--settlements", required=True, type=Path, help="Settlement CSV: rrn,amount_cents,currency")
    parser.add_argument("--ledger", required=True, type=Path, help="Ledger CSV: rrn,event_type,amount_cents,status")
    parser.add_argument("--out", type=Path, help="Optional JSON output path")
    args = parser.parse_args()

    report = reconcile(load_rows(args.settlements), load_rows(args.ledger))
    payload = json.dumps(report, indent=2)

    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    summary = report["summary"]
    print(
        f"rows={summary['total_rows']} matched={summary['matched']} "
        f"missing={summary['missing_authorization']} duplicates={summary['duplicate_settlement']} "
        f"mismatches={summary['amount_mismatch']} delayed={summary['delayed_settlement']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
