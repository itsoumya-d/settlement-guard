"""Tests for Credit Risk & Fraud Decisioning Engine."""

import datetime
import pytest

from credit_risk_decision_engine import (
    CreditApplicantProfile,
    ChampionCreditModel,
    ChallengerCreditModel,
    RealtimeFraudDetector,
    TransactionSignal,
    ChampionChallengerRouter,
    ModelGovernanceMonitor,
)


@pytest.fixture
def prime_applicant() -> CreditApplicantProfile:
    return CreditApplicantProfile(
        applicant_id="app-1001",
        annual_income=85000.0,
        debt_to_income_ratio=0.15,
        delinquencies_24m=0,
        credit_inquiries_6m=0,
        revolving_utilization_ratio=0.12,
        employment_tenure_months=48,
        requested_credit_limit=5000.0,
        monthly_disposable_income=3200.0,
    )


@pytest.fixture
def distressed_applicant() -> CreditApplicantProfile:
    return CreditApplicantProfile(
        applicant_id="app-9999",
        annual_income=22000.0,
        debt_to_income_ratio=0.65,
        delinquencies_24m=3,
        credit_inquiries_6m=5,
        revolving_utilization_ratio=0.92,
        employment_tenure_months=6,
        requested_credit_limit=6000.0,
        monthly_disposable_income=250.0,
    )


def test_applicant_validation(prime_applicant):
    prime_applicant.validate()

    bad_income = CreditApplicantProfile(
        applicant_id="bad-1",
        annual_income=-100.0,
        debt_to_income_ratio=0.2,
        delinquencies_24m=0,
        credit_inquiries_6m=0,
        revolving_utilization_ratio=0.2,
        employment_tenure_months=12,
        requested_credit_limit=1000.0,
        monthly_disposable_income=500.0,
    )
    with pytest.raises(ValueError, match="annual_income"):
        bad_income.validate()

    bad_dti = CreditApplicantProfile(
        applicant_id="bad-2",
        annual_income=50000.0,
        debt_to_income_ratio=2.5,
        delinquencies_24m=0,
        credit_inquiries_6m=0,
        revolving_utilization_ratio=0.2,
        employment_tenure_months=12,
        requested_credit_limit=1000.0,
        monthly_disposable_income=500.0,
    )
    with pytest.raises(ValueError, match="debt_to_income_ratio"):
        bad_dti.validate()


def test_champion_model_prime(prime_applicant):
    model = ChampionCreditModel()
    decision = model.evaluate(prime_applicant)

    assert decision.decision == "APPROVED"
    assert decision.approved_limit == 5000.0
    assert decision.credit_score >= 700
    assert decision.probability_of_default < 0.05
    assert "Prime credit" in decision.reasons[0]


def test_champion_model_distressed(distressed_applicant):
    model = ChampionCreditModel()
    decision = model.evaluate(distressed_applicant)

    assert decision.decision == "DECLINED"
    assert decision.approved_limit == 0.0
    assert decision.credit_score < 560
    assert decision.probability_of_default > 0.20
    assert any("delinquencies" in r.lower() for r in decision.reasons)


def test_champion_model_borderline_affordability():
    borderline = CreditApplicantProfile(
        applicant_id="app-5050",
        annual_income=42000.0,
        debt_to_income_ratio=0.38,
        delinquencies_24m=0,
        credit_inquiries_6m=1,
        revolving_utilization_ratio=0.55,
        employment_tenure_months=24,
        requested_credit_limit=12000.0,  # 3% = 360 monthly vs 800 disp -> > 40%
        monthly_disposable_income=800.0,
    )
    model = ChampionCreditModel()
    decision = model.evaluate(borderline)

    assert decision.decision in ("CONDITIONAL_LIMIT", "MANUAL_REVIEW")
    assert decision.approved_limit < 12000.0


def test_challenger_model_evaluation(prime_applicant, distressed_applicant):
    challenger = ChallengerCreditModel()

    prime_dec = challenger.evaluate(prime_applicant)
    assert prime_dec.decision == "APPROVED"
    assert prime_dec.model_version == "challenger-v3.1-gbm"
    assert prime_dec.credit_score >= 700

    distressed_dec = challenger.evaluate(distressed_applicant)
    assert distressed_dec.decision == "DECLINED"
    assert distressed_dec.approved_limit == 0.0


def test_realtime_fraud_detector_normal():
    detector = RealtimeFraudDetector()
    now = datetime.datetime.now(datetime.timezone.utc)
    sig = TransactionSignal(
        transaction_id="tx-100",
        account_id="acc-1",
        amount=45.0,
        currency="GBP",
        merchant_category_code="5411",  # Grocery
        velocity_1h_count=1,
        velocity_24h_amount=120.0,
        distance_from_last_tx_km=2.0,
        time_delta_seconds=3600.0,
        is_card_not_present=False,
        timestamp=now,
    )
    res = detector.evaluate(sig)
    assert res.action == "ALLOW"
    assert res.fraud_risk_score < 0.20
    assert len(res.anomaly_flags) == 0


def test_realtime_fraud_detector_impossible_travel():
    detector = RealtimeFraudDetector()
    now = datetime.datetime.now(datetime.timezone.utc)
    sig = TransactionSignal(
        transaction_id="tx-200",
        account_id="acc-2",
        amount=250.0,
        currency="GBP",
        merchant_category_code="5812",
        velocity_1h_count=2,
        velocity_24h_amount=500.0,
        distance_from_last_tx_km=900.0,  # 900 km in 10 minutes -> 5400 km/h
        time_delta_seconds=600.0,
        is_card_not_present=False,
        timestamp=now,
    )
    res = detector.evaluate(sig)
    assert res.action == "DECLINE"
    assert res.fraud_risk_score >= 0.70
    assert any("impossible travel" in f.lower() for f in res.anomaly_flags)


def test_realtime_fraud_detector_velocity_step_up():
    detector = RealtimeFraudDetector()
    now = datetime.datetime.now(datetime.timezone.utc)
    sig = TransactionSignal(
        transaction_id="tx-300",
        account_id="acc-3",
        amount=150.0,
        currency="GBP",
        merchant_category_code="5732",  # Electronics
        velocity_1h_count=6,  # >5 triggers spike
        velocity_24h_amount=1200.0,
        distance_from_last_tx_km=5.0,
        time_delta_seconds=300.0,
        is_card_not_present=True,
        timestamp=now,
    )
    res = detector.evaluate(sig)
    assert res.action in ("STEP_UP_AUTH", "DECLINE")
    assert any("velocity spike" in f.lower() for f in res.anomaly_flags)


def test_champion_challenger_routing(prime_applicant):
    router = ChampionChallengerRouter(challenger_traffic_share=0.50)

    dec_1, is_chall_1 = router.route_profile(prime_applicant)
    assert dec_1.applicant_id == prime_applicant.applicant_id

    # Determinism: same ID always yields same route
    dec_2, is_chall_2 = router.route_profile(prime_applicant)
    assert is_chall_1 == is_chall_2
    assert dec_1.model_version == dec_2.model_version

    shadow = router.shadow_evaluate(prime_applicant)
    assert "divergence" in shadow
    assert "score_diff" in shadow
    assert "pd_diff" in shadow


def test_model_governance_psi():
    baseline = [650.0, 680.0, 710.0, 720.0, 750.0, 600.0, 580.0, 690.0, 740.0, 780.0]
    similar = [645.0, 685.0, 705.0, 725.0, 745.0, 605.0, 585.0, 695.0, 735.0, 775.0]

    psi_stable = ModelGovernanceMonitor.calculate_psi(baseline, similar, buckets=4)
    assert psi_stable < 0.10  # PSI < 0.10 indicates stable distribution

    drifted = [500.0, 520.0, 510.0, 540.0, 530.0, 550.0, 515.0, 525.0, 535.0, 545.0]
    psi_drift = ModelGovernanceMonitor.calculate_psi(baseline, drifted, buckets=4)
    assert psi_drift > 0.25  # PSI > 0.25 indicates significant population shift


def test_model_governance_fairness():
    ref_decisions = ["APPROVED", "APPROVED", "APPROVED", "DECLINED"]  # 75% approval
    prot_decisions = ["APPROVED", "CONDITIONAL_LIMIT", "APPROVED", "DECLINED"]  # 75% approval

    dir_ratio = ModelGovernanceMonitor.calculate_disparate_impact_ratio(prot_decisions, ref_decisions)
    assert dir_ratio == 1.0  # Perfect demographic parity

    biased_prot = ["DECLINED", "DECLINED", "APPROVED", "DECLINED"]  # 25% approval
    dir_biased = ModelGovernanceMonitor.calculate_disparate_impact_ratio(biased_prot, ref_decisions)
    assert dir_biased < 0.80  # Fails 4/5ths rule (< 0.80)
