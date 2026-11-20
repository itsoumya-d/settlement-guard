"""Unit tests for payment_pipeline_orchestrator.py."""

import datetime
import decimal

from tools.payment_pipeline_orchestrator import (
    PaymentEvent,
    PaymentEventIngestionPipeline,
    PaymentStatus,
    OLAPWarehouseSyncBridge,
    ReconciliationObservabilityMonitor,
)


def test_payment_event_fingerprinting():
    ts = datetime.datetime(2026, 11, 20, 10, 0, 0, tzinfo=datetime.timezone.utc)
    ev1 = PaymentEvent(
        event_id="evt_001",
        transaction_id="tx_123",
        merchant_id="merch_abc",
        psp_name="Stripe",
        payment_method="credit_card",
        amount=decimal.Decimal("150.00"),
        currency="EUR",
        status=PaymentStatus.CAPTURED,
        timestamp=ts
    )
    ev2 = PaymentEvent(
        event_id="evt_002",
        transaction_id="tx_123",
        merchant_id="merch_abc",
        psp_name="Stripe",
        payment_method="credit_card",
        amount=decimal.Decimal("150.00"),
        currency="EUR",
        status=PaymentStatus.CAPTURED,
        timestamp=ts
    )
    # Different event_id, but identical transaction payload fingerprint
    assert ev1.fingerprint() == ev2.fingerprint()


def test_ingest_event_success():
    pipeline = PaymentEventIngestionPipeline()
    payload = {
        "event_id": "evt_101",
        "transaction_id": "tx_999",
        "merchant_id": "merch_global",
        "psp_name": "Adyen",
        "payment_method": "sepa_debit",
        "amount": "249.50",
        "currency": "EUR",
        "status": "CAPTURED",
        "timestamp": "2026-11-20T08:30:00Z"
    }
    success, ev, msg = pipeline.ingest_event(payload)
    assert success is True
    assert ev is not None
    assert ev.amount == decimal.Decimal("249.50")
    assert ev.status == PaymentStatus.CAPTURED
    assert pipeline.get_ledger_count() == 1


def test_ingest_event_schema_validation_failures():
    pipeline = PaymentEventIngestionPipeline()

    # Missing required field
    bad_payload = {"event_id": "evt_001", "transaction_id": "tx_001"}
    success, ev, msg = pipeline.ingest_event(bad_payload)
    assert success is False
    assert "Missing required field" in msg

    # Negative amount
    negative_payload = {
        "event_id": "evt_002",
        "transaction_id": "tx_002",
        "merchant_id": "m1",
        "psp_name": "Stripe",
        "amount": "-50.00",
        "currency": "EUR",
        "status": "CAPTURED"
    }
    success, ev, msg = pipeline.ingest_event(negative_payload)
    assert success is False
    assert "amount must be positive" in msg

    # Invalid currency
    bad_currency = {
        "event_id": "evt_003",
        "transaction_id": "tx_003",
        "merchant_id": "m1",
        "psp_name": "Stripe",
        "amount": "50.00",
        "currency": "EUROPEAN",
        "status": "CAPTURED"
    }
    success, ev, msg = pipeline.ingest_event(bad_currency)
    assert success is False
    assert "Invalid ISO-4217 currency" in msg


def test_ingest_event_idempotent_deduplication():
    pipeline = PaymentEventIngestionPipeline()
    ts_str = "2026-11-20T10:00:00Z"
    payload = {
        "event_id": "evt_unique_1",
        "transaction_id": "tx_idem_1",
        "merchant_id": "m_test",
        "psp_name": "Checkout.com",
        "amount": "80.00",
        "currency": "EUR",
        "status": "AUTHORIZED",
        "timestamp": ts_str
    }
    # First ingestion succeeds
    success1, ev1, msg1 = pipeline.ingest_event(payload)
    assert success1 is True
    assert pipeline.get_ledger_count() == 1

    # Exact duplicate event payload
    duplicate_payload = {
        "event_id": "evt_unique_2",
        "transaction_id": "tx_idem_1",
        "merchant_id": "m_test",
        "psp_name": "Checkout.com",
        "amount": "80.00",
        "currency": "EUR",
        "status": "AUTHORIZED",
        "timestamp": ts_str
    }
    success2, ev2, msg2 = pipeline.ingest_event(duplicate_payload)
    assert success2 is False
    assert "idempotent no-op" in msg2
    assert pipeline.get_ledger_count() == 1


def test_olap_warehouse_sync_dimensional_batch():
    bridge = OLAPWarehouseSyncBridge(target_warehouse="Snowflake")
    events = [
        PaymentEvent(
            event_id="e1",
            transaction_id="t1",
            merchant_id="m_fashion",
            psp_name="Stripe",
            payment_method="credit_card",
            amount=decimal.Decimal("120.00"),
            currency="EUR",
            status=PaymentStatus.SETTLED,
            timestamp=datetime.datetime(2026, 11, 20, 11, 0, tzinfo=datetime.timezone.utc)
        ),
        PaymentEvent(
            event_id="e2",
            transaction_id="t2",
            merchant_id="m_travel",
            psp_name="Adyen",
            payment_method="apple_pay",
            amount=decimal.Decimal("340.50"),
            currency="EUR",
            status=PaymentStatus.SETTLED,
            timestamp=datetime.datetime(2026, 11, 20, 11, 5, tzinfo=datetime.timezone.utc)
        )
    ]

    batch = bridge.generate_dimensional_batch(events)
    assert len(batch["fact_payment_settlement"]) == 2
    assert len(batch["dim_merchant"]) == 2
    assert len(batch["dim_psp"]) == 2
    assert batch["fact_payment_settlement"][0]["settled_amount"] == 120.00
    assert batch["dim_psp"][0]["psp_name"] in ["Stripe", "Adyen"]


def test_reconciliation_observability_balanced():
    monitor = ReconciliationObservabilityMonitor(variance_tolerance_pct=0.01)
    events = [
        PaymentEvent(
            event_id="e1", transaction_id="t1", merchant_id="m1", psp_name="Stripe",
            payment_method="card", amount=decimal.Decimal("1000.00"), currency="EUR",
            status=PaymentStatus.CAPTURED, timestamp=datetime.datetime.now(datetime.timezone.utc)
        ),
        PaymentEvent(
            event_id="e2", transaction_id="t2", merchant_id="m1", psp_name="Adyen",
            payment_method="card", amount=decimal.Decimal("2500.00"), currency="EUR",
            status=PaymentStatus.SETTLED, timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
    ]

    # Matching PSP report
    psp_report = {
        "Stripe": decimal.Decimal("1000.00"),
        "Adyen": decimal.Decimal("2500.00")
    }

    report = monitor.evaluate_settlement_reconciliation(events, psp_report)
    assert report["reconciliation_passed"] is True
    assert report["circuit_breaker_tripped"] is False
    assert len(report["discrepancies"]) == 2


def test_reconciliation_observability_circuit_breaker_trip():
    monitor = ReconciliationObservabilityMonitor(variance_tolerance_pct=0.01)
    events = [
        PaymentEvent(
            event_id="e1", transaction_id="t1", merchant_id="m1", psp_name="Stripe",
            payment_method="card", amount=decimal.Decimal("10000.00"), currency="EUR",
            status=PaymentStatus.SETTLED, timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
    ]

    # Major shortfall in PSP payout (e.g. 10% discrepancy)
    psp_report = {
        "Stripe": decimal.Decimal("9000.00")
    }

    report = monitor.evaluate_settlement_reconciliation(events, psp_report)
    assert report["reconciliation_passed"] is False
    assert report["circuit_breaker_tripped"] is True
    assert report["discrepancies"][0]["variance_pct"] == 10.0
