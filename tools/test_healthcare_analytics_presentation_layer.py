"""Unit tests for Healthcare Analytics Presentation Layer & PII Governance."""

from __future__ import annotations

import pytest
from healthcare_analytics_presentation_layer import (
    ClinicalConsultationModel,
    ClinicalDataQualityError,
    ClinicalDataQualityGate,
    HealthcarePresentationWarehouse,
    PiiGovernancePolicy,
)


def test_pii_governance_masking() -> None:
    gov = PiiGovernancePolicy(salt="test_salt")
    assert gov.mask_identifier("") == ""

    id1 = gov.mask_identifier("485 777 3456")
    id2 = gov.mask_identifier("4857773456")
    assert id1 == id2
    assert id1.startswith("ANON_")
    assert len(id1) == 21

    assert gov.redact_free_text("") == ""

    raw_note = (
        "Patient NHS 987 654 3210 called from 07123 456 789 or +44 7123 456789. "
        "Email dr.smith@nhs.net, lives at SW1A 1AA."
    )
    redacted = gov.redact_free_text(raw_note)
    assert "[REDACTED_NHS_NO]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_POSTCODE]" in redacted
    assert "987 654 3210" not in redacted
    assert "07123" not in redacted
    assert "dr.smith@nhs.net" not in redacted


def test_pii_governance_role_based() -> None:
    gov = PiiGovernancePolicy()
    record = {
        "consultation_id": "c1",
        "patient_nhs_number": "123 456 7890",
        "patient_phone": "+44 7111 222333",
        "clinical_notes": "Follow up with patient at EC2A 4NE.",
    }
    analyst_view = gov.apply_governance(record, role="analyst")
    assert analyst_view["patient_nhs_number"].startswith("ANON_")
    assert analyst_view["patient_phone"] == "[MASKED_PHONE]"
    assert "[REDACTED_POSTCODE]" in analyst_view["clinical_notes"]

    lead_view = gov.apply_governance(record, role="clinical_lead")
    assert lead_view["patient_nhs_number"] == "123 456 7890"
    assert lead_view["patient_phone"] == "+44 7111 222333"
    assert lead_view["clinical_notes"] == "Follow up with patient at EC2A 4NE."


def test_clinical_data_quality_gate_valid() -> None:
    valid = {
        "consultation_id": "c100",
        "patient_id": "p500",
        "practice_ods_code": "Y12345",
        "consultation_type": "triage",
        "status": "completed",
        "duration_seconds": 420,
        "created_at": "2026-11-22T08:30:00Z",
    }
    assert ClinicalDataQualityGate.validate_consultation(valid) == []
    ClinicalDataQualityGate.enforce(valid)


def test_clinical_data_quality_gate_violations() -> None:
    invalid = {
        "consultation_id": "",
        "patient_id": "",
        "practice_ods_code": "",
        "consultation_type": "telepathy",
        "status": "unknown_status",
        "duration_seconds": -50,
        "created_at": "invalid-datetime",
    }
    violations = ClinicalDataQualityGate.validate_consultation(invalid)
    assert len(violations) >= 6
    assert any("consultation_id" in v for v in violations)
    assert any("patient_id" in v for v in violations)
    assert any("practice_ods_code" in v for v in violations)
    assert any("Invalid consultation_type" in v for v in violations)
    assert any("Invalid status" in v for v in violations)
    assert any("duration_seconds must be a non-negative" in v for v in violations)
    assert any("not valid ISO 8601" in v for v in violations)

    with pytest.raises(ClinicalDataQualityError):
        ClinicalDataQualityGate.enforce(invalid)

    bad_ts = {
        "consultation_id": "c1",
        "patient_id": "p1",
        "practice_ods_code": "A123",
        "consultation_type": "self_book",
        "status": "completed",
    }
    v_ts = ClinicalDataQualityGate.validate_consultation(bad_ts)
    assert any("Missing created_at" in v for v in v_ts)

    bad_dur = dict(bad_ts, created_at="2026-11-22T10:00:00", duration_seconds=100000)
    v_dur = ClinicalDataQualityGate.validate_consultation(bad_dur)
    assert any("exceeds 24 hours" in v for v in v_dur)


def test_clinical_consultation_model_transformation() -> None:
    model = ClinicalConsultationModel()
    raw = {
        "consultation_id": "c-999",
        "patient_id": "patient-77",
        "clinician_id": "dr-jones",
        "practice_ods_code": "F84001",
        "consultation_type": "ambient_scribe",
        "status": "completed",
        "duration_seconds": 600,
        "is_scribe_assisted": True,
        "is_self_booked": False,
        "triage_urgency_tier": "urgent",
        "patient_nhs_number": "111 222 3333",
        "clinical_notes": "Scribe drafted: patient reported symptoms at 07700900123.",
        "created_at": "2026-11-22T09:15:00+00:00",
    }
    fact = model.build_fact_record(raw, role="analyst")
    assert fact["consultation_id"] == "c-999"
    assert len(fact["consultation_key"]) == 16
    assert len(fact["patient_key"]) == 16
    assert len(fact["clinician_key"]) == 16
    assert len(fact["practice_key"]) == 16
    assert fact["practice_ods_code"] == "F84001"
    assert fact["consultation_date"] == "2026-11-22"
    assert fact["is_scribe_assisted"] is True
    assert fact["is_self_booked"] is False
    assert fact["triage_urgency_tier"] == "urgent"
    assert "[REDACTED_PHONE]" in fact["clinical_notes_redacted"]


def test_healthcare_presentation_warehouse_aggregation() -> None:
    warehouse = HealthcarePresentationWarehouse()

    empty_summary = warehouse.compute_practice_summary("NON_EXISTENT")
    assert empty_summary["total_consultations"] == 0
    assert empty_summary["scribe_adoption_rate"] == 0.0

    events = [
        {
            "consultation_id": "c1",
            "patient_id": "p1",
            "practice_ods_code": "P001",
            "consultation_type": "ambient_scribe",
            "status": "completed",
            "duration_seconds": 600,
            "is_scribe_assisted": True,
            "is_self_booked": False,
            "created_at": "2026-11-22T09:00:00Z",
        },
        {
            "consultation_id": "c2",
            "patient_id": "p2",
            "practice_ods_code": "P001",
            "consultation_type": "self_book",
            "status": "completed",
            "duration_seconds": 300,
            "is_scribe_assisted": False,
            "is_self_booked": True,
            "created_at": "2026-11-22T10:00:00Z",
        },
        {
            "consultation_id": "c3",
            "patient_id": "p3",
            "practice_ods_code": "P002",
            "consultation_type": "triage",
            "status": "completed",
            "duration_seconds": 180,
            "is_scribe_assisted": False,
            "is_self_booked": False,
            "created_at": "2026-11-22T11:00:00Z",
        },
    ]

    for ev in events:
        warehouse.ingest_event(ev)

    summary_p1 = warehouse.compute_practice_summary("P001")
    assert summary_p1["total_consultations"] == 2
    assert summary_p1["scribe_adoption_rate"] == 0.5
    assert summary_p1["self_booked_rate"] == 0.5
    assert summary_p1["avg_duration_minutes"] == 7.5

    summary_p2 = warehouse.compute_practice_summary("P002")
    assert summary_p2["total_consultations"] == 1
    assert summary_p2["scribe_adoption_rate"] == 0.0
    assert summary_p2["self_booked_rate"] == 0.0
    assert summary_p2["avg_duration_minutes"] == 3.0
