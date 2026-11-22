"""Healthcare Analytics Presentation Layer & Clinical Data Governance.

Purpose-built for modern healthcare communication platforms and clinical data platforms.
Provides:
  - Dimensional star schema models (dim_patients, dim_clinicians, dim_practices, fct_clinical_consultations)
  - NHS Caldicott / IG-compliant dynamic PII de-identification and HMAC masking
  - Production data quality assertion gates with schema validation
  - Analytical presentation aggregation for self-serve BI and clinical operations
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import re
from typing import Any, ClassVar


class ClinicalDataQualityError(ValueError):
    """Raised when clinical data fails data quality assertion gates."""


class PiiGovernancePolicy:
    """Dynamic de-identification and governance masking engine for clinical data."""

    def __init__(self, salt: str = "accurx_gov_salt_2026") -> None:
        self.salt: bytes = salt.encode("utf-8")
        self._phone_rx: re.Pattern[str] = re.compile(r"(\+44\s?7\d{3}|\b07\d{3})\s?\d{3}\s?\d{3}\b")
        self._nhs_no_rx: re.Pattern[str] = re.compile(r"\b\d{3}\s?\d{3}\s?\d{4}\b")
        self._email_rx: re.Pattern[str] = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
        self._postcode_rx: re.Pattern[str] = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.IGNORECASE)

    def mask_identifier(self, raw_id: str) -> str:
        """Deterministically pseudo-anonymize an NHS number or patient identifier using HMAC-SHA256."""
        if not raw_id:
            return ""
        clean = re.sub(r"\s+", "", str(raw_id).strip())
        digest = hmac.new(self.salt, clean.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"ANON_{digest[:16].upper()}"

    def redact_free_text(self, text: str) -> str:
        """Redact sensitive PII (phones, emails, UK postcodes, raw NHS numbers) from clinical notes."""
        if not text:
            return ""
        s = self._nhs_no_rx.sub("[REDACTED_NHS_NO]", text)
        s = self._phone_rx.sub("[REDACTED_PHONE]", s)
        s = self._email_rx.sub("[REDACTED_EMAIL]", s)
        return self._postcode_rx.sub("[REDACTED_POSTCODE]", s)

    def apply_governance(self, record: dict[str, Any], role: str = "analyst") -> dict[str, Any]:
        """Apply role-based masking. 'analyst' gets masked PII; 'clinical_lead' retains verified audit identifiers."""
        out = dict(record)
        if role != "clinical_lead":
            if "patient_nhs_number" in out:
                out["patient_nhs_number"] = self.mask_identifier(str(out["patient_nhs_number"]))
            if "patient_phone" in out:
                out["patient_phone"] = "[MASKED_PHONE]"
            if "clinical_notes" in out:
                out["clinical_notes"] = self.redact_free_text(str(out["clinical_notes"]))
        return out


class ClinicalDataQualityGate:
    """Enforces rigorous data quality assertions on incoming operational clinical events."""

    VALID_CONSULTATION_TYPES: ClassVar[set[str]] = {
        "triage",
        "self_book",
        "ambient_scribe",
        "accumail_message",
        "routine_review",
    }
    VALID_STATUSES: ClassVar[set[str]] = {"completed", "in_progress", "scheduled", "cancelled", "escalated"}

    @classmethod
    def validate_consultation(cls, record: dict[str, Any]) -> list[str]:
        """Validate consultation attributes, returning list of violation descriptions."""
        violations: list[str] = []
        if not record.get("consultation_id"):
            violations.append("Missing consultation_id")
        if not record.get("patient_id"):
            violations.append("Missing patient_id")
        if not record.get("practice_ods_code"):
            violations.append("Missing practice_ods_code")

        c_type = record.get("consultation_type")
        if c_type not in cls.VALID_CONSULTATION_TYPES:
            violations.append(
                f"Invalid consultation_type '{c_type}'; must be one of {sorted(cls.VALID_CONSULTATION_TYPES)}"
            )

        status = record.get("status")
        if status not in cls.VALID_STATUSES:
            violations.append(f"Invalid status '{status}'; must be one of {sorted(cls.VALID_STATUSES)}")

        dur = record.get("duration_seconds")
        if dur is not None:
            if not isinstance(dur, (int, float)) or dur < 0:
                violations.append(f"duration_seconds must be a non-negative number, got {dur}")
            elif dur > 86400:
                violations.append(f"duration_seconds exceeds 24 hours ({dur})")

        ts = record.get("created_at")
        if ts:
            try:
                dt.datetime.fromisoformat(str(ts))
            except ValueError:
                violations.append(f"created_at '{ts}' is not valid ISO 8601")
        else:
            violations.append("Missing created_at timestamp")

        return violations

    @classmethod
    def enforce(cls, record: dict[str, Any]) -> None:
        """Raise ClinicalDataQualityError if validation fails."""
        violations = cls.validate_consultation(record)
        if violations:
            raise ClinicalDataQualityError(f"Clinical data quality assertions failed: {'; '.join(violations)}")


class ClinicalConsultationModel:
    """Transforms raw healthcare operational events into dimensional presentation star schema records."""

    def __init__(self, governance_policy: PiiGovernancePolicy | None = None) -> None:
        self.governance: PiiGovernancePolicy = governance_policy or PiiGovernancePolicy()

    def build_fact_record(self, raw_event: dict[str, Any], role: str = "analyst") -> dict[str, Any]:
        """Validate, govern, and model an operational clinical event into a presentation fact row."""
        ClinicalDataQualityGate.enforce(raw_event)
        governed = self.governance.apply_governance(raw_event, role=role)

        raw_consultation_id = str(governed["consultation_id"])
        c_key = hashlib.md5(f"consultation:{raw_consultation_id}".encode()).hexdigest()[:16]
        p_key = hashlib.md5(f"patient:{governed['patient_id']}".encode()).hexdigest()[:16]
        c_clinician_key = hashlib.md5(
            f"clinician:{governed.get('clinician_id', 'unassigned')}".encode()
        ).hexdigest()[:16]
        prac_key = hashlib.md5(f"practice:{governed['practice_ods_code']}".encode()).hexdigest()[:16]

        created_dt = dt.datetime.fromisoformat(str(governed["created_at"]))

        return {
            "consultation_key": c_key,
            "consultation_id": raw_consultation_id,
            "patient_key": p_key,
            "clinician_key": c_clinician_key,
            "practice_key": prac_key,
            "practice_ods_code": governed["practice_ods_code"],
            "consultation_date": created_dt.date().isoformat(),
            "consultation_timestamp": created_dt.isoformat(),
            "consultation_type": governed["consultation_type"],
            "status": governed["status"],
            "duration_seconds": governed.get("duration_seconds", 0),
            "is_scribe_assisted": bool(governed.get("is_scribe_assisted", False)),
            "is_self_booked": bool(governed.get("is_self_booked", False)),
            "triage_urgency_tier": governed.get("triage_urgency_tier", "routine"),
            "clinical_notes_redacted": governed.get("clinical_notes", ""),
        }


class HealthcarePresentationWarehouse:
    """Presentation layer aggregator for self-serve BI and clinical operations analytics."""

    def __init__(self) -> None:
        self.model: ClinicalConsultationModel = ClinicalConsultationModel()
        self.records: list[dict[str, Any]] = []

    def ingest_event(self, raw_event: dict[str, Any], role: str = "analyst") -> dict[str, Any]:
        fact = self.model.build_fact_record(raw_event, role=role)
        self.records.append(fact)
        return fact

    def compute_practice_summary(self, practice_ods_code: str) -> dict[str, Any]:
        """Aggregate practice-level metrics (consultation volume, scribe adoption, avg duration)."""
        practice_recs = [r for r in self.records if r["practice_ods_code"] == practice_ods_code]
        total = len(practice_recs)
        if total == 0:
            return {
                "practice_ods_code": practice_ods_code,
                "total_consultations": 0,
                "scribe_adoption_rate": 0.0,
                "self_booked_rate": 0.0,
                "avg_duration_minutes": 0.0,
            }

        scribe_count = sum(1 for r in practice_recs if r["is_scribe_assisted"])
        self_book_count = sum(1 for r in practice_recs if r["is_self_booked"])
        total_duration = sum(r["duration_seconds"] for r in practice_recs)

        return {
            "practice_ods_code": practice_ods_code,
            "total_consultations": total,
            "scribe_adoption_rate": round(scribe_count / total, 4),
            "self_booked_rate": round(self_book_count / total, 4),
            "avg_duration_minutes": round((total_duration / total) / 60.0, 2),
        }
