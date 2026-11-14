"""Unit tests for Westpac credit risk portfolio & asset quality validator."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest
from westpac_credit_risk_validator import (
    CreditExposure,
    WestpacCreditRiskValidator,
    main,
)


@pytest.fixture
def sample_segments() -> list[CreditExposure]:
    return [
        CreditExposure(
            portfolio_segment="Residential Mortgages",
            total_exposure_nzd=68_500_000_000.0,
            stage_1_exposure_nzd=65_200_000_000.0,
            stage_2_exposure_nzd=2_750_000_000.0,
            stage_3_exposure_nzd=550_000_000.0,
            provisions_ecl_nzd=420_000_000.0,
            past_due_90_days_nzd=310_000_000.0,
            high_lvr_exposure_nzd=6_100_000_000.0,
        ),
        CreditExposure(
            portfolio_segment="Commercial Corporate",
            total_exposure_nzd=31_500_000_000.0,
            stage_1_exposure_nzd=29_200_000_000.0,
            stage_2_exposure_nzd=1_950_000_000.0,
            stage_3_exposure_nzd=350_000_000.0,
            provisions_ecl_nzd=310_000_000.0,
            past_due_90_days_nzd=240_000_000.0,
            high_lvr_exposure_nzd=1_500_000_000.0,
        ),
    ]


def test_staging_mathematical_integrity(sample_segments: list[CreditExposure]):
    for s in sample_segments:
        assert s.validate_staging_sum() is True


def test_portfolio_reconciliation_pass(sample_segments: list[CreditExposure]):
    validator = WestpacCreditRiskValidator()
    gl_total = 68_500_000_000.0 + 31_500_000_000.0  # exactly 100B
    report = validator.validate_portfolio("2026-11-14", sample_segments, gl_total)

    assert report.reconciliation_status == "PASS"
    assert report.checks_failed == 0
    assert report.checks_passed == 3  # 2 staging checks + 1 GL check
    assert report.total_credit_portfolio_nzd == 100_000_000_000.0
    assert report.overall_npl_ratio == pytest.approx(0.009, rel=1e-3)
    assert len(report.anomalies) == 0


def test_gl_reconciliation_variance_flagged(sample_segments: list[CreditExposure]):
    validator = WestpacCreditRiskValidator()
    # GL control has a $50M variance
    gl_total = 100_050_000_000.0
    report = validator.validate_portfolio("2026-11-14", sample_segments, gl_total)

    assert report.reconciliation_status == "FAIL"
    assert report.checks_failed == 1
    failed_check = [c for c in report.checks if not c.passed][0]
    assert failed_check.check_name == "General Ledger Control Tie-Out"
    assert failed_check.difference == pytest.approx(50_000_000.0, abs=1.0)


def test_staging_imbalance_detected():
    validator = WestpacCreditRiskValidator()
    broken_segment = [
        CreditExposure(
            portfolio_segment="Faulty Segment",
            total_exposure_nzd=10_000_000.0,
            stage_1_exposure_nzd=8_000_000.0,
            stage_2_exposure_nzd=1_000_000.0,
            stage_3_exposure_nzd=500_000.0,  # sum is 9.5M, missing 500k
            provisions_ecl_nzd=200_000.0,
            past_due_90_days_nzd=100_000.0,
            high_lvr_exposure_nzd=100_000.0,
        )
    ]
    report = validator.validate_portfolio("2026-11-14", broken_segment, 10_000_000.0)
    assert report.reconciliation_status == "FAIL"
    assert report.checks_failed == 1
    assert report.checks[0].check_name == "Staging Sum Integrity"
    assert report.checks[0].passed is False


def test_past_due_anomaly_alert():
    validator = WestpacCreditRiskValidator()
    suspicious_segment = [
        CreditExposure(
            portfolio_segment="Anomalous Segment",
            total_exposure_nzd=10_000_000.0,
            stage_1_exposure_nzd=8_000_000.0,
            stage_2_exposure_nzd=1_000_000.0,
            stage_3_exposure_nzd=1_000_000.0,
            provisions_ecl_nzd=500_000.0,
            past_due_90_days_nzd=1_500_000.0,  # 90+ DPD > Stage 3 impaired
            high_lvr_exposure_nzd=100_000.0,
        )
    ]
    report = validator.validate_portfolio("2026-11-14", suspicious_segment, 10_000_000.0)
    assert any("90+ DPD" in a for a in report.anomalies)


def test_cli_execution(tmp_path: Path):
    output_file = tmp_path / "westpac_report.json"
    ret = main(["--output", str(output_file)])
    assert ret == 0
    assert output_file.exists()
    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert data["institution"] == "Westpac New Zealand Limited"
    assert data["reconciliation_status"] == "PASS"
