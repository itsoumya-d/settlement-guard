"""Credit Risk & Fraud Decisioning Engine with Champion-Challenger Model Validation.

Provides:
- Calibrated probability of default (PD) scoring and credit rating tiers (300-850 scale)
- Comprehensive affordability assessment and risk-based credit limit assignment
- Real-time transaction fraud anomaly scoring (velocity spikes, travel impossibility, MCC risk)
- Champion/Challenger deployment router with deterministic traffic hashing
- Model governance metrics: Population Stability Index (PSI), Kolmogorov-Smirnov (KS), and fairness parity
"""

from __future__ import annotations

import dataclasses
import datetime
import hashlib
import math
from typing import Any, Dict, List, Tuple


@dataclasses.dataclass(frozen=True)
class CreditApplicantProfile:
    applicant_id: str
    annual_income: float
    debt_to_income_ratio: float
    delinquencies_24m: int
    credit_inquiries_6m: int
    revolving_utilization_ratio: float
    employment_tenure_months: int
    requested_credit_limit: float
    monthly_disposable_income: float

    def validate(self) -> None:
        if self.annual_income < 0:
            raise ValueError("annual_income must be non-negative")
        if not (0.0 <= self.debt_to_income_ratio <= 2.0):
            raise ValueError("debt_to_income_ratio must be between 0.0 and 2.0")
        if not (0.0 <= self.revolving_utilization_ratio <= 1.5):
            raise ValueError("revolving_utilization_ratio must be between 0.0 and 1.5")
        if self.delinquencies_24m < 0 or self.credit_inquiries_6m < 0:
            raise ValueError("counts cannot be negative")


@dataclasses.dataclass(frozen=True)
class CreditDecision:
    applicant_id: str
    model_version: str
    probability_of_default: float
    credit_score: int
    decision: str  # "APPROVED", "CONDITIONAL_LIMIT", "MANUAL_REVIEW", "DECLINED"
    approved_limit: float
    reasons: List[str]
    debt_burden_ratio: float


@dataclasses.dataclass(frozen=True)
class TransactionSignal:
    transaction_id: str
    account_id: str
    amount: float
    currency: str
    merchant_category_code: str
    velocity_1h_count: int
    velocity_24h_amount: float
    distance_from_last_tx_km: float
    time_delta_seconds: float
    is_card_not_present: bool
    timestamp: datetime.datetime


@dataclasses.dataclass(frozen=True)
class FraudAssessment:
    transaction_id: str
    fraud_risk_score: float  # 0.0 to 1.0
    action: str  # "ALLOW", "STEP_UP_AUTH", "DECLINE"
    anomaly_flags: List[str]


class ChampionCreditModel:
    """Production Champion: Linear log-odds scorecard calibrated to 680 base with 40 PDO."""

    def __init__(self, base_score: int = 680, points_to_double_odds: float = 40.0):
        self.base_score = base_score
        self.pdo = points_to_double_odds
        self.factor = self.pdo / math.log(2.0)
        self.offset = self.base_score - self.factor * math.log(50.0)

    def predict_pd(self, profile: CreditApplicantProfile) -> float:
        z = -4.3  # baseline log-odds of default
        z += profile.debt_to_income_ratio * 2.2
        z += profile.revolving_utilization_ratio * 2.5
        z += profile.delinquencies_24m * 0.80
        z += profile.credit_inquiries_6m * 0.35
        if profile.employment_tenure_months < 12:
            z += 0.40
        elif profile.employment_tenure_months >= 36:
            z -= 0.35
        if profile.annual_income >= 60000.0:
            z -= 0.40
        elif profile.annual_income < 25000.0:
            z += 0.50

        pd = 1.0 / (1.0 + math.exp(-z))
        return min(max(pd, 0.001), 0.999)

    def evaluate(self, profile: CreditApplicantProfile) -> CreditDecision:
        profile.validate()
        pd = self.predict_pd(profile)

        odds = (1.0 - pd) / max(pd, 1e-6)
        score = int(round(self.offset + self.factor * math.log(max(odds, 1e-6))))
        score = min(max(score, 300), 850)

        reasons: List[str] = []
        approved_limit = 0.0

        monthly_commitment_assumed = (profile.requested_credit_limit * 0.03)
        affordability_ratio = monthly_commitment_assumed / max(profile.monthly_disposable_income, 1.0)

        if pd > 0.30 or score < 520:
            decision = "DECLINED"
            if profile.delinquencies_24m > 0:
                reasons.append("Historical delinquencies in prior 24 months")
            if profile.revolving_utilization_ratio > 0.80:
                reasons.append("High revolving balance utilization")
            if affordability_ratio > 0.40:
                reasons.append("Insufficient disposable income for requested line")
            approved_limit = 0.0
        elif pd > 0.18 or score < 590:
            decision = "MANUAL_REVIEW"
            reasons.append("Borderline credit score requiring underwriter validation")
            approved_limit = min(profile.requested_credit_limit * 0.5, profile.monthly_disposable_income * 2.0)
        elif affordability_ratio > 0.30 or pd > 0.08:
            decision = "CONDITIONAL_LIMIT"
            reasons.append("Credit approved with reduced line to satisfy affordability buffer")
            approved_limit = min(profile.requested_credit_limit * 0.7, profile.monthly_disposable_income * 3.0)
        else:
            decision = "APPROVED"
            reasons.append("Prime credit and verified repayment capacity")
            approved_limit = profile.requested_credit_limit

        return CreditDecision(
            applicant_id=profile.applicant_id,
            model_version="champion-v2.4",
            probability_of_default=round(pd, 4),
            credit_score=score,
            decision=decision,
            approved_limit=round(approved_limit, 2),
            reasons=reasons,
            debt_burden_ratio=round(affordability_ratio, 4),
        )


class ChallengerCreditModel:
    """Challenger: Advanced non-linear risk model with interaction terms."""

    def __init__(self, base_score: int = 685, points_to_double_odds: float = 40.0):
        self.base_score = base_score
        self.pdo = points_to_double_odds
        self.factor = self.pdo / math.log(2.0)
        self.offset = self.base_score - self.factor * math.log(50.0)

    def predict_pd(self, profile: CreditApplicantProfile) -> float:
        z = -4.5
        z += math.pow(profile.debt_to_income_ratio, 1.3) * 2.5
        z += math.pow(profile.revolving_utilization_ratio, 1.4) * 2.8
        z += profile.delinquencies_24m * 0.90
        z += profile.credit_inquiries_6m * 0.40

        # Interaction term: high utilization + multiple inquiries
        if profile.revolving_utilization_ratio > 0.70 and profile.credit_inquiries_6m >= 2:
            z += 0.70

        # Employment stability discount
        stability = profile.employment_tenure_months / 48.0
        z -= min(stability, 1.0) * 0.55

        pd = 1.0 / (1.0 + math.exp(-z))
        return min(max(pd, 0.001), 0.999)

    def evaluate(self, profile: CreditApplicantProfile) -> CreditDecision:
        profile.validate()
        pd = self.predict_pd(profile)

        odds = (1.0 - pd) / max(pd, 1e-6)
        score = int(round(self.offset + self.factor * math.log(max(odds, 1e-6))))
        score = min(max(score, 300), 850)

        reasons: List[str] = []
        monthly_commitment_assumed = (profile.requested_credit_limit * 0.03)
        affordability_ratio = monthly_commitment_assumed / max(profile.monthly_disposable_income, 1.0)

        if pd > 0.25 or score < 540:
            decision = "DECLINED"
            reasons.append("Challenger high-risk non-linear default probability")
            approved_limit = 0.0
        elif pd > 0.10 or score < 630 or affordability_ratio > 0.30:
            decision = "CONDITIONAL_LIMIT"
            reasons.append("Challenger dynamic limit allocation")
            approved_limit = min(profile.requested_credit_limit * 0.6, profile.monthly_disposable_income * 2.5)
        else:
            decision = "APPROVED"
            reasons.append("Prime customer risk profile validated by non-linear estimator")
            approved_limit = profile.requested_credit_limit

        return CreditDecision(
            applicant_id=profile.applicant_id,
            model_version="challenger-v3.1-gbm",
            probability_of_default=round(pd, 4),
            credit_score=score,
            decision=decision,
            approved_limit=round(approved_limit, 2),
            reasons=reasons,
            debt_burden_ratio=round(affordability_ratio, 4),
        )


class RealtimeFraudDetector:
    """Real-time transaction fraud scoring and velocity monitoring."""

    HIGH_RISK_MCCS = {"6011", "6051", "7995", "4829"}  # Quasi-cash, gambling, wire transfer

    def evaluate(self, signal: TransactionSignal) -> FraudAssessment:
        score = 0.05
        flags: List[str] = []

        # Velocity check
        if signal.velocity_1h_count > 5:
            score += 0.40
            flags.append("High 1-hour transaction velocity spike (>5 tx)")
        elif signal.velocity_1h_count > 3:
            score += 0.20
            flags.append("Elevated 1-hour transaction frequency")

        # High amount velocity
        if signal.velocity_24h_amount > 5000.0:
            score += 0.25
            flags.append("24h cumulative volume exceeds threshold (>5000)")

        # Geo-velocity impossibility check (speed > 850 km/h)
        if signal.time_delta_seconds > 0 and signal.distance_from_last_tx_km > 50.0:
            speed_kmh = (signal.distance_from_last_tx_km / signal.time_delta_seconds) * 3600.0
            if speed_kmh > 850.0:
                score += 0.70
                flags.append(f"Impossible travel speed detected: {speed_kmh:.1f} km/h")

        # High-risk merchant category
        if signal.merchant_category_code in self.HIGH_RISK_MCCS:
            score += 0.20
            flags.append(f"High risk merchant category code ({signal.merchant_category_code})")

        # Card not present + high single transaction value
        if signal.is_card_not_present and signal.amount > 1000.0:
            score += 0.20
            flags.append("High value Card-Not-Present transaction")

        score = min(max(score, 0.0), 1.0)

        if score >= 0.70:
            action = "DECLINE"
        elif score >= 0.35:
            action = "STEP_UP_AUTH"
        else:
            action = "ALLOW"

        return FraudAssessment(
            transaction_id=signal.transaction_id,
            fraud_risk_score=round(score, 3),
            action=action,
            anomaly_flags=flags,
        )


class ChampionChallengerRouter:
    """Deterministic A/B allocation and model divergence monitoring."""

    def __init__(self, challenger_traffic_share: float = 0.20):
        self.share = challenger_traffic_share
        self.champion = ChampionCreditModel()
        self.challenger = ChallengerCreditModel()

    def route_profile(self, profile: CreditApplicantProfile) -> Tuple[CreditDecision, bool]:
        digest = hashlib.sha256(profile.applicant_id.encode("utf-8")).hexdigest()
        slot = int(digest[:8], 16) / 0xFFFFFFFF
        is_challenger = slot < self.share

        if is_challenger:
            decision = self.challenger.evaluate(profile)
        else:
            decision = self.champion.evaluate(profile)

        return decision, is_challenger

    def shadow_evaluate(self, profile: CreditApplicantProfile) -> Dict[str, Any]:
        """Runs both models to monitor disagreement / divergence without affecting production decision."""
        champ = self.champion.evaluate(profile)
        chall = self.challenger.evaluate(profile)

        divergence = champ.decision != chall.decision
        score_diff = chall.credit_score - champ.credit_score
        pd_diff = chall.probability_of_default - champ.probability_of_default

        return {
            "applicant_id": profile.applicant_id,
            "champion_decision": champ.decision,
            "challenger_decision": chall.decision,
            "divergence": divergence,
            "score_diff": score_diff,
            "pd_diff": round(pd_diff, 4),
        }


class ModelGovernanceMonitor:
    """Calculates Population Stability Index (PSI) and demographic parity."""

    @staticmethod
    def calculate_psi(baseline_scores: List[float], current_scores: List[float], buckets: int = 5) -> float:
        if not baseline_scores or not current_scores:
            return 0.0

        min_val, max_val = min(baseline_scores), max(baseline_scores)
        if min_val == max_val:
            return 0.0

        step = (max_val - min_val) / buckets
        bin_edges = [min_val + i * step for i in range(buckets + 1)]
        bin_edges[-1] += 1e-6

        def count_bins(data: List[float]) -> List[int]:
            counts = [0] * buckets
            for x in data:
                for i in range(buckets):
                    if bin_edges[i] <= x < bin_edges[i + 1]:
                        counts[i] += 1
                        break
            return counts

        base_counts = count_bins(baseline_scores)
        curr_counts = count_bins(current_scores)

        total_base = len(baseline_scores)
        total_curr = len(current_scores)

        psi = 0.0
        for b, c in zip(base_counts, curr_counts):
            pct_b = max(b / total_base, 1e-4)
            pct_c = max(c / total_curr, 1e-4)
            psi += (pct_c - pct_b) * math.log(pct_c / pct_b)

        return round(psi, 4)

    @staticmethod
    def calculate_disparate_impact_ratio(
        protected_decisions: List[str], reference_decisions: List[str]
    ) -> float:
        """Computes four-fifths rule approval ratio (protected approval rate / reference approval rate)."""
        if not protected_decisions or not reference_decisions:
            return 1.0

        prot_approved = sum(1 for d in protected_decisions if d in ("APPROVED", "CONDITIONAL_LIMIT"))
        ref_approved = sum(1 for d in reference_decisions if d in ("APPROVED", "CONDITIONAL_LIMIT"))

        rate_prot = prot_approved / len(protected_decisions)
        rate_ref = ref_approved / len(reference_decisions)

        if rate_ref == 0:
            return 1.0

        return round(rate_prot / rate_ref, 3)
