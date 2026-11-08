import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from reconcile import reconcile


def row(rrn, event_type, amount, status="APPLIED"):
    return {"rrn": rrn, "event_type": event_type, "amount_cents": str(amount), "status": status}


def test_matched():
    report = reconcile(
        [{"rrn": "R1", "amount_cents": "1000", "currency": "NZD"}],
        [row("R1", "AUTHORIZATION", 1000), row("R1", "SETTLEMENT", 1000)],
    )

    assert report["summary"]["matched"] == 1
    assert report["breaks"][0]["break_type"] == "MATCHED"


def test_missing_authorization():
    report = reconcile(
        [{"rrn": "R2", "amount_cents": "1000", "currency": "NZD"}],
        [],
    )

    assert report["summary"]["missing_authorization"] == 1
    assert report["breaks"][0]["break_type"] == "MISSING_AUTHORIZATION"


def test_duplicate_settlement():
    report = reconcile(
        [{"rrn": "R3", "amount_cents": "1000", "currency": "NZD"}],
        [
            row("R3", "AUTHORIZATION", 1000),
            row("R3", "SETTLEMENT", 1000),
            row("R3", "SETTLEMENT", 1000),
        ],
    )

    assert report["summary"]["duplicate_settlement"] == 1
    assert report["breaks"][0]["break_type"] == "DUPLICATE_SETTLEMENT"


def test_amount_mismatch():
    report = reconcile(
        [{"rrn": "R4", "amount_cents": "1000", "currency": "NZD"}],
        [row("R4", "AUTHORIZATION", 1000), row("R4", "SETTLEMENT", 900)],
    )

    assert report["summary"]["amount_mismatch"] == 1
    assert report["breaks"][0]["expected_cents"] == 1000
    assert report["breaks"][0]["actual_cents"] == 900


def test_delayed_settlement():
    report = reconcile(
        [{"rrn": "R5", "amount_cents": "1000", "currency": "NZD"}],
        [row("R5", "AUTHORIZATION", 1000)],
    )

    assert report["summary"]["delayed_settlement"] == 1
    assert report["breaks"][0]["break_type"] == "DELAYED_SETTLEMENT"


def test_cli_writes_report(tmp_path):
    settlements = tmp_path / "settlements.csv"
    ledger = tmp_path / "ledger.csv"
    out = tmp_path / "report.json"
    settlements.write_text("rrn,amount_cents,currency\nR6,1000,NZD\n", encoding="utf-8")
    ledger.write_text(
        "rrn,event_type,amount_cents,status\nR6,AUTHORIZATION,1000,APPLIED\nR6,SETTLEMENT,1000,APPLIED\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent / "reconcile.py"),
            "--settlements",
            str(settlements),
            "--ledger",
            str(ledger),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["summary"]["matched"] == 1
