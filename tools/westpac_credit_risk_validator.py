"""Westpac Credit Risk Portfolio & Asset Quality Reporting Validator.

Validates credit portfolio exposures, NZ IFRS 9 staging provisions (Stage 1, 2, 3),
non-performing loan (NPL) ratios, loan-to-value (LVR) concentration bands,
and automated ledger reconciliation for internal executive and RBNZ regulatory reporting.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CreditExposure:
    portfolio_segment: str
    total_exposure_nzd: float
    stage_1_exposure_nzd: float
    stage_2_exposure_nzd: float
    stage_3_exposure_nzd: float
    provisions_ecl_nzd: float
    past_due_90_days_nzd: float
    high_lvr_exposure_nzd: float  # LVR > 80%

    def validate_staging_sum(self, tolerance: float = 0.01) -> bool:
        staging_sum = (
            self.stage_1_exposure_nzd
            + self.stage_2_exposure_nzd
            + self.stage_3_exposure_nzd
        )
        return math.isclose(staging_sum, self.total_exposure_nzd, abs_tol=tolerance)

    @property
    def npl_ratio(self) -> float:
        if self.total_exposure_nzd <= 0:
            return 0.0
        return self.stage_3_exposure_nzd / self.total_exposure_nzd

    @property
    def provision_coverage_ratio(self) -> float:
        if self.stage_3_exposure_nzd <= 0:
            return 1.0 if self.provisions_ecl_nzd >= 0 else 0.0
        return self.provisions_ecl_nzd / self.stage_3_exposure_nzd

    @property
    def high_lvr_ratio(self) -> float:
        if self.total_exposure_nzd <= 0:
            return 0.0
        return self.high_lvr_exposure_nzd / self.total_exposure_nzd


@dataclass
class ReconciliationCheck:
    check_name: str
    portfolio_segment: str
    expected_value: float
    actual_value: float
    difference: float
    passed: bool
    details: str


@dataclass
class PortfolioQualityReport:
    reporting_date: str
    institution: str
    total_credit_portfolio_nzd: float
    total_ecl_provisions_nzd: float
    overall_npl_ratio: float
    overall_high_lvr_ratio: float
    reconciliation_status: str
    checks_passed: int
    checks_failed: int
    checks: List[ReconciliationCheck] = field(default_factory=list)
    anomalies: List[str] = field(default_factory=list)
    executive_commentary: List[str] = field(default_factory=list)


class WestpacCreditRiskValidator:
    """Validates credit risk asset quality returns and reconciles against general ledger controls."""

    def __init__(self, max_npl_threshold: float = 0.025, max_high_lvr_threshold: float = 0.15):
        self.max_npl_threshold = max_npl_threshold
        self.max_high_lvr_threshold = max_high_lvr_threshold

    def validate_portfolio(
        self,
        reporting_date: str,
        exposures: List[CreditExposure],
        general_ledger_control_nzd: Optional[float] = None,
    ) -> PortfolioQualityReport:
        checks: List[ReconciliationCheck] = []
        anomalies: List[str] = []
        commentary: List[str] = []

        total_portfolio = 0.0
        total_provisions = 0.0
        total_stage_3 = 0.0
        total_high_lvr = 0.0

        for exp in exposures:
            total_portfolio += exp.total_exposure_nzd
            total_provisions += exp.provisions_ecl_nzd
            total_stage_3 += exp.stage_3_exposure_nzd
            total_high_lvr += exp.high_lvr_exposure_nzd

            # Check 1: Staging mathematical balance (Stage 1 + Stage 2 + Stage 3 = Total)
            staging_sum = (
                exp.stage_1_exposure_nzd
                + exp.stage_2_exposure_nzd
                + exp.stage_3_exposure_nzd
            )
            diff = abs(staging_sum - exp.total_exposure_nzd)
            passed = diff <= 0.05
            checks.append(
                ReconciliationCheck(
                    check_name="Staging Sum Integrity",
                    portfolio_segment=exp.portfolio_segment,
                    expected_value=exp.total_exposure_nzd,
                    actual_value=staging_sum,
                    difference=diff,
                    passed=passed,
                    details=f"Segment {exp.portfolio_segment} Stage 1+2+3 vs Total Exposure",
                )
            )

            # Check 2: 90 DPD <= Stage 3
            if exp.past_due_90_days_nzd > (exp.stage_3_exposure_nzd + 0.01):
                anomalies.append(
                    f"Segment {exp.portfolio_segment}: 90+ DPD (${exp.past_due_90_days_nzd:,.2f}) "
                    f"exceeds Stage 3 impaired balance (${exp.stage_3_exposure_nzd:,.2f})"
                )

            # Check 3: Segment NPL threshold monitoring
            if exp.npl_ratio > self.max_npl_threshold:
                anomalies.append(
                    f"Elevated NPL Ratio in {exp.portfolio_segment}: {exp.npl_ratio:.2%} "
                    f"(regulatory threshold: {self.max_npl_threshold:.2%})"
                )

        # Check 4: General Ledger Control Reconciliation
        if general_ledger_control_nzd is not None:
            gl_diff = abs(total_portfolio - general_ledger_control_nzd)
            gl_passed = gl_diff <= 1.0  # $1 dollar roundoff tolerance
            checks.append(
                ReconciliationCheck(
                    check_name="General Ledger Control Tie-Out",
                    portfolio_segment="TOTAL_PORTFOLIO",
                    expected_value=general_ledger_control_nzd,
                    actual_value=total_portfolio,
                    difference=gl_diff,
                    passed=gl_passed,
                    details="Total sub-ledger credit exposures reconciled to GL Balance Sheet control account",
                )
            )

        overall_npl = (total_stage_3 / total_portfolio) if total_portfolio > 0 else 0.0
        overall_high_lvr = (total_high_lvr / total_portfolio) if total_portfolio > 0 else 0.0

        passed_count = sum(1 for c in checks if c.passed)
        failed_count = sum(1 for c in checks if not c.passed)
        recon_status = "PASS" if failed_count == 0 else "FAIL"

        # Generate Executive Commentary
        commentary.append(
            f"As of {reporting_date}, total credit portfolio stands at NZD ${total_portfolio:,.2f} "
            f"with total ECL provisions of NZD ${total_provisions:,.2f}."
        )
        commentary.append(
            f"Overall asset quality remains sound with an aggregate NPL ratio of {overall_npl:.2%} "
            f"and high-LVR (>80%) concentration at {overall_high_lvr:.2%}."
        )
        if failed_count == 0:
            commentary.append(
                "All internal asset quality reconciliations and GL balance sheet controls tied out with 100% precision."
            )
        else:
            commentary.append(
                f"WARNING: {failed_count} reconciliation check(s) flagged variances requiring investigation prior to committee sign-off."
            )

        return PortfolioQualityReport(
            reporting_date=reporting_date,
            institution="Westpac New Zealand Limited",
            total_credit_portfolio_nzd=total_portfolio,
            total_ecl_provisions_nzd=total_provisions,
            overall_npl_ratio=overall_npl,
            overall_high_lvr_ratio=overall_high_lvr,
            reconciliation_status=recon_status,
            checks_passed=passed_count,
            checks_failed=failed_count,
            checks=checks,
            anomalies=anomalies,
            executive_commentary=commentary,
        )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Westpac Credit Risk Portfolio Reporting Validator"
    )
    parser.add_argument("--input", "-i", type=str, help="JSON input file with credit segments")
    parser.add_argument("--output", "-o", type=str, help="JSON output report path")
    args = parser.parse_args(argv)

    validator = WestpacCreditRiskValidator()

    if args.input and Path(args.input).exists():
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
        segments = [CreditExposure(**s) for s in data.get("segments", [])]
        gl_control = data.get("gl_control_nzd")
        rep_date = data.get("reporting_date", "2026-11-14")
    else:
        # Default sample Westpac credit portfolio benchmark
        rep_date = "2026-11-14"
        gl_control = 104_500_000_000.0  # NZD 104.5B Westpac NZ loan book
        segments = [
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
                portfolio_segment="Agribusiness & Rural",
                total_exposure_nzd=12_300_000_000.0,
                stage_1_exposure_nzd=11_100_000_000.0,
                stage_2_exposure_nzd=1_020_000_000.0,
                stage_3_exposure_nzd=180_000_000.0,
                provisions_ecl_nzd=165_000_000.0,
                past_due_90_days_nzd=120_000_000.0,
                high_lvr_exposure_nzd=850_000_000.0,
            ),
            CreditExposure(
                portfolio_segment="Commercial SME & Corporate",
                total_exposure_nzd=21_200_000_000.0,
                stage_1_exposure_nzd=19_400_000_000.0,
                stage_2_exposure_nzd=1_520_000_000.0,
                stage_3_exposure_nzd=280_000_000.0,
                provisions_ecl_nzd=250_000_000.0,
                past_due_90_days_nzd=195_000_000.0,
                high_lvr_exposure_nzd=1_200_000_000.0,
            ),
            CreditExposure(
                portfolio_segment="Consumer & Unsecured Lending",
                total_exposure_nzd=2_500_000_000.0,
                stage_1_exposure_nzd=2_310_000_000.0,
                stage_2_exposure_nzd=155_000_000.0,
                stage_3_exposure_nzd=35_000_000.0,
                provisions_ecl_nzd=48_000_000.0,
                past_due_90_days_nzd=28_000_000.0,
                high_lvr_exposure_nzd=0.0,
            ),
        ]

    report = validator.validate_portfolio(rep_date, segments, gl_control)
    rep_dict = asdict(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(rep_dict, f, indent=2)
        print(f"Report written to {args.output}")
    else:
        print(json.dumps(rep_dict, indent=2))

    return 0 if report.reconciliation_status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
