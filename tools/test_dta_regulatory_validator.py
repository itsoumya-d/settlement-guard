import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dta_regulatory_validator import (
    validate_balance_sheet,
    validate_prudential_ratios,
    detect_statistical_anomalies,
    validate_returns,
)


def sample_return(
    institution="BK01",
    period="2026-Q3",
    assets=100000.0,
    liabilities=90000.0,
    equity=10000.0,
    core_funding=80000.0,
    loans=90000.0,
    cet1=8000.0,
    total_capital=12000.0,
    rwa=80000.0,
    household=50000.0,
    business=30000.0,
):
    return {
        "institution_code": institution,
        "period": period,
        "total_assets": str(assets),
        "total_liabilities": str(liabilities),
        "total_equity": str(equity),
        "core_funding_one_year": str(core_funding),
        "total_loans_advances": str(loans),
        "cet1_capital": str(cet1),
        "total_capital": str(total_capital),
        "risk_weighted_assets": str(rwa),
        "household_claims": str(household),
        "business_lending": str(business),
    }


def test_balanced_return():
    ret = sample_return()
    res = validate_balance_sheet(ret)
    assert res["is_balanced"] is True
    assert res["status"] == "PASS"
    assert res["discrepancy"] == 0.0


def test_unbalanced_return():
    ret = sample_return(assets=105000.0, liabilities=90000.0, equity=10000.0)
    res = validate_balance_sheet(ret)
    assert res["is_balanced"] is False
    assert res["status"] == "BALANCE_MISMATCH"
    assert res["discrepancy"] == 5000.0


def test_prudential_ratios_pass():
    ret = sample_return()
    res = validate_prudential_ratios(ret)
    assert res["is_compliant"] is True
    assert len(res["breaches"]) == 0
    assert res["core_funding_ratio_pct"] == 88.89
    assert res["cet1_ratio_pct"] == 10.0
    assert res["total_capital_ratio_pct"] == 15.0


def test_prudential_ratios_breach():
    # CFR below 75%, CET1 below 4.5%
    ret = sample_return(core_funding=50000.0, loans=100000.0, cet1=3000.0, rwa=100000.0)
    res = validate_prudential_ratios(ret)
    assert res["is_compliant"] is False
    assert any("CFR_BELOW_MINIMUM" in b for b in res["breaches"])
    assert any("CET1_BELOW_MINIMUM" in b for b in res["breaches"])


def test_statistical_anomaly_detection():
    hist = [
        sample_return(period=f"2025-Q{i}", household=50000.0) for i in range(1, 5)
    ]
    # Current has massive spike (75000 vs 50000, 50% spike)
    curr = sample_return(period="2026-Q1", household=75000.0)
    anomalies = detect_statistical_anomalies(curr, hist)
    assert len(anomalies) > 0
    assert any("SPIKE_EXCEEDS_TOLERANCE" in a["reason"] for a in anomalies)


def test_validate_returns_aggregation():
    ret1 = sample_return(institution="BK01")
    ret2 = sample_return(institution="BK02", assets=99999.0, liabilities=90000.0, equity=5000.0)
    report = validate_returns([ret1, ret2])

    assert report["summary"]["total_returns"] == 2
    assert report["summary"]["valid_returns"] == 1
    assert report["summary"]["balance_sheet_mismatches"] == 1
    assert report["results"][0]["overall_status"] == "VALID"
    assert report["results"][1]["overall_status"] == "FLAGGED_FOR_REVIEW"


def test_cli_execution(tmp_path):
    returns_csv = tmp_path / "returns.csv"
    returns_csv.write_text(
        "institution_code,period,total_assets,total_liabilities,total_equity,core_funding_one_year,total_loans_advances,cet1_capital,total_capital,risk_weighted_assets,household_claims,business_lending\n"
        "BK01,2026-Q3,100000,90000,10000,80000,90000,8000,12000,80000,50000,30000\n",
        encoding="utf-8",
    )
    out_json = tmp_path / "out.json"

    res = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent / "dta_regulatory_validator.py"),
            "--returns",
            str(returns_csv),
            "--out",
            str(out_json),
        ],
        capture_output=True,
        text=True,
    )

    assert res.returncode == 0
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["summary"]["total_returns"] == 1
    assert payload["summary"]["valid_returns"] == 1
