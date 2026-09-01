"""Phase 8 End-to-End Integration Tests.

Validates the full multi-vendor compliance auditing pipeline, PDF generation,
and the human-in-the-loop self-learning loop from end to end.
"""

from pathlib import Path
from unittest.mock import patch

from app.models import Device, LearnedRule, ParsedConfig, PendingReview
from app.pipeline import ingest_one

FIXTURES = Path(__file__).parent / "fixtures" / "configs"


def test_e2e_known_vendor_full_pipeline(client, db_session):
    """End-to-end test 1: Upload known-vendor config → evaluate → assert findings exist → generate PDF."""
    cisco_content = (FIXTURES / "cisco_ios_1.cfg").read_bytes()
    juniper_content = (FIXTURES / "juniper_1.cfg").read_bytes()

    # 1. Upload Cisco config
    cisco_upload_resp = client.post(
        "/api/devices/upload",
        files={"file": ("cisco_ios_1.cfg", cisco_content, "text/plain")},
    )
    assert cisco_upload_resp.status_code == 200
    upload_data = cisco_upload_resp.json()
    assert upload_data["status"] == "ok"
    assert upload_data["ingested_count"] == 1

    # 2. Upload Juniper config
    juniper_upload_resp = client.post(
        "/api/devices/upload",
        files={"file": ("juniper_1.cfg", juniper_content, "text/plain")},
    )
    assert juniper_upload_resp.status_code == 200

    # 3. Query /api/devices and verify both devices registered
    devices_resp = client.get("/api/devices")
    assert devices_resp.status_code == 200
    devices = devices_resp.json()
    assert len(devices) >= 2
    cisco_device = next(d for d in devices if d["filename"] == "cisco_ios_1.cfg")
    assert cisco_device["vendor"] == "cisco"

    # 4. Trigger compliance evaluation for Cisco device under CIS framework
    report_resp = client.get(f"/api/devices/{cisco_device['id']}/report?framework=CIS")
    assert report_resp.status_code == 200
    report_data = report_resp.json()

    assert report_data["device"]["filename"] == "cisco_ios_1.cfg"
    assert report_data["framework"] == "CIS"
    assert report_data["total_rules"] > 0
    assert report_data["pass_count"] + report_data["fail_count"] == report_data["total_rules"]
    assert "management_plane" in report_data["grouped_findings"]

    # 5. Generate PDF report and verify binary content
    pdf_resp = client.get(f"/devices/{cisco_device['id']}/report.pdf?framework=CIS")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF-")


def test_e2e_unknown_vendor_training_and_reevaluation(client, db_session):
    """End-to-end test 2: Ingest unrecognized config → queue for training → resolve → verify learned & evaluated."""
    unknown_line = "sec-system-policy disable-legacy-telnet"
    config_text = f"hostname EDGE-ROUTER-01\n{unknown_line}\n"

    # 1. Ingest config with low-confidence LLM classification to trigger PendingReview queue
    with patch("app.tier2.fallback.classify_via_llm") as mock_llm:
        mock_llm.return_value = {
            "category": "management_plane",
            "field": "telnet_enabled",
            "value": False,
            "confidence": 0.35,  # Below 0.75 threshold -> queue for review
        }
        device = ingest_one(db_session, "unknown_edge.cfg", config_text)
        db_session.commit()

    # 2. Query /api/training/pending and confirm item queued
    pending_resp = client.get("/api/training/pending")
    assert pending_resp.status_code == 200
    pending_items = pending_resp.json()
    review_item = next((r for r in pending_items if r["raw_line"] == unknown_line), None)
    assert review_item is not None
    assert review_item["status"] == "pending"

    # 3. Resolve the item via /api/training/resolve
    resolve_payload = {
        "review_id": review_item["id"],
        "category": "management_plane",
        "field": "telnet_enabled",
        "value": "False",
    }
    resolve_resp = client.post("/api/training/resolve", json=resolve_payload)
    assert resolve_resp.status_code == 200
    res_data = resolve_resp.json()
    assert res_data["status"] == "ok"
    assert "Successfully resolved" in res_data["message"]

    # 4. Verify LearnedRule created in DB
    learned = db_session.query(LearnedRule).filter(LearnedRule.raw_pattern == unknown_line).first()
    assert learned is not None
    assert learned.category == "management_plane"
    assert learned.field == "telnet_enabled"

    # 5. Verify PendingReview queue no longer contains the item
    pending_after_resp = client.get("/api/training/pending")
    assert pending_after_resp.status_code == 200
    assert not any(r["id"] == review_item["id"] for r in pending_after_resp.json())

    # 6. Evaluate device report and confirm compliance engine evaluates reprocessed schema correctly
    report_resp = client.get(f"/api/devices/{device.id}/report?framework=CIS")
    assert report_resp.status_code == 200
    report_data = report_resp.json()

    assert report_data["device"]["filename"] == "unknown_edge.cfg"
    assert report_data["total_rules"] > 0
    assert report_data["pass_count"] >= 1
