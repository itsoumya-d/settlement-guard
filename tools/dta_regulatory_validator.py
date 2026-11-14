#!/usr/bin/env python3
"""Reserve Bank of New Zealand Deposit Takers Act (DTA) Regulatory Return Validator.

Validates institutional regulatory data returns against prudential reporting rules:
1. Balance sheet identity: Total Assets == Total Liabilities + Equity.
2. Prudential liquidity and capital ratios:
   - Core Funding Ratio (CFR >= 75.0%)
   - Common Equity Tier 1 (CET1 >= 4.5%)
   - Total Capital Ratio (TCR >= 8.0%)
3. Statistical anomaly detection: Detects deviations > 3 standard deviations or > 25%
   quarter-on-quarter variance against historical institutional baseline.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


def _to_float(val: Any) -> float:
    if val is None or val == "":
        return 0.0
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


def validate_balance_sheet(row: dict[str, Any], tolerance: float = 0.01) -> dict[str, Any]:
    assets = _to_float(row.get("total_assets"))
    liabilities = _to_float(row.get("total_liabilities"))
    equity = _to_float(row.get("total_equity"))
    expected_assets = liabilities + equity
    diff = abs(assets - expected_assets)

    is_balanced = diff <= tolerance
    return {
        "institution_code": row.get("institution_code", "UNKNOWN"),
        "period": row.get("period", "UNKNOWN"),
        "total_assets": assets,
        "total_liabilities": liabilities,
        "total_equity": equity,
        "discrepancy": round(diff, 2),
        "is_balanced": is_balanced,
        "status": "PASS" if is_balanced else "BALANCE_MISMATCH",
    }


def validate_prudential_ratios(row: dict[str, Any]) -> dict[str, Any]:
    one_year_funding = _to_float(row.get("core_funding_one_year"))
    total_loans = _to_float(row.get("total_loans_advances"))
    cet1_capital = _to_float(row.get("cet1_capital"))
    total_capital = _to_float(row.get("total_capital"))
    risk_weighted_assets = _to_float(row.get("risk_weighted_assets"))

    cfr = (one_year_funding / total_loans * 100.0) if total_loans > 0 else 0.0
    cet1_ratio = (cet1_capital / risk_weighted_assets * 100.0) if risk_weighted_assets > 0 else 0.0
    tcr_ratio = (total_capital / risk_weighted_assets * 100.0) if risk_weighted_assets > 0 else 0.0

    breaches = []
    if cfr < 75.0 and total_loans > 0:
        breaches.append(f"CFR_BELOW_MINIMUM: {cfr:.2f}% < 75.00%")
    if cet1_ratio < 4.5 and risk_weighted_assets > 0:
        breaches.append(f"CET1_BELOW_MINIMUM: {cet1_ratio:.2f}% < 4.50%")
    if tcr_ratio < 8.0 and risk_weighted_assets > 0:
        breaches.append(f"TCR_BELOW_MINIMUM: {tcr_ratio:.2f}% < 8.00%")

    return {
        "institution_code": row.get("institution_code", "UNKNOWN"),
        "period": row.get("period", "UNKNOWN"),
        "core_funding_ratio_pct": round(cfr, 2),
        "cet1_ratio_pct": round(cet1_ratio, 2),
        "total_capital_ratio_pct": round(tcr_ratio, 2),
        "breaches": breaches,
        "is_compliant": len(breaches) == 0,
    }


def detect_statistical_anomalies(
    current_return: dict[str, Any], historical_returns: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    anomalies = []
    inst = current_return.get("institution_code")
    hist_inst = [h for h in historical_returns if h.get("institution_code") == inst]
    if len(hist_inst) < 3:
        return anomalies

    metrics_to_check = [
        "household_claims",
        "business_lending",
        "non_resident_deposits",
        "total_assets",
    ]

    for metric in metrics_to_check:
        curr_val = _to_float(current_return.get(metric))
        hist_vals = [_to_float(h.get(metric)) for h in hist_inst if h.get(metric) is not None]
        if not hist_vals:
            continue

        mean = sum(hist_vals) / len(hist_vals)
        variance = sum((x - mean) ** 2 for x in hist_vals) / len(hist_vals)
        std_dev = math.sqrt(variance)

        # Check standard deviation z-score
        if std_dev > 0:
            z_score = abs(curr_val - mean) / std_dev
            if z_score > 3.0:
                anomalies.append({
                    "metric": metric,
                    "current_value": curr_val,
                    "historical_mean": round(mean, 2),
                    "z_score": round(z_score, 2),
                    "reason": f"OUTLIER_Z_SCORE: {z_score:.2f} > 3.0 standard deviations",
                })

        # Check quarter-on-quarter spike
        latest_hist = hist_vals[-1]
        if latest_hist > 0:
            pct_change = abs(curr_val - latest_hist) / latest_hist * 100.0
            if pct_change > 25.0:
                anomalies.append({
                    "metric": metric,
                    "current_value": curr_val,
                    "prior_period_value": latest_hist,
                    "pct_change": round(pct_change, 2),
                    "reason": f"SPIKE_EXCEEDS_TOLERANCE: {pct_change:.2f}% > 25.00%",
                })

    return anomalies


def validate_returns(
    returns_data: list[dict[str, Any]], historical_data: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    historical_data = historical_data or []
    results = []
    summary = {
        "total_returns": len(returns_data),
        "valid_returns": 0,
        "balance_sheet_mismatches": 0,
        "prudential_breaches": 0,
        "statistical_anomalies": 0,
    }

    for ret in returns_data:
        bs_res = validate_balance_sheet(ret)
        ratio_res = validate_prudential_ratios(ret)
        anomalies = detect_statistical_anomalies(ret, historical_data)

        has_issue = (not bs_res["is_balanced"]) or (not ratio_res["is_compliant"]) or bool(anomalies)

        if not bs_res["is_balanced"]:
            summary["balance_sheet_mismatches"] += 1
        if not ratio_res["is_compliant"]:
            summary["prudential_breaches"] += len(ratio_res["breaches"])
        if anomalies:
            summary["statistical_anomalies"] += len(anomalies)
        if not has_issue:
            summary["valid_returns"] += 1

        results.append({
            "institution_code": ret.get("institution_code"),
            "period": ret.get("period"),
            "balance_sheet": bs_res,
            "prudential_ratios": ratio_res,
            "anomalies": anomalies,
            "overall_status": "VALID" if not has_issue else "FLAGGED_FOR_REVIEW",
        })

    return {"summary": summary, "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="RBNZ DTA Regulatory Return Validator")
    parser.add_argument("--returns", required=True, type=Path, help="CSV file of current returns")
    parser.add_argument("--historical", type=Path, default=None, help="CSV file of historical returns")
    parser.add_argument("--out", type=Path, default=None, help="Output JSON report path")
    args = parser.parse_args()

    with args.returns.open(newline="", encoding="utf-8") as f:
        returns_data = [dict(r) for r in csv.DictReader(f)]

    hist_data = []
    if args.historical and args.historical.exists():
        with args.historical.open(newline="", encoding="utf-8") as f:
            hist_data = [dict(r) for r in csv.DictReader(f)]

    report = validate_returns(returns_data, hist_data)

    if args.out:
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    else:
        print(json.dumps(report, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
