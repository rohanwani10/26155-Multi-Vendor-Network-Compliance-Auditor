"""Phase 6 tests — HTML report, PDF download, and dashboard."""

from bs4 import BeautifulSoup

from app.evaluator.engine import evaluate_device
from app.models import Finding
from app.pipeline import ingest_one


def _ingest_and_evaluate(db_session, client, filename, config_text, framework="CIS"):
    """Helper: ingest a config, commit, evaluate via API, return device."""
    device = ingest_one(db_session, filename, config_text)
    db_session.commit()
    resp = client.post(f"/evaluate/{device.id}?framework={framework}")
    assert resp.status_code == 200
    return device


HARDENED_CISCO = """!
version 15.2
hostname CISCO-SECURE
ip ssh version 2
line vty 0 4
 transport input ssh
aaa new-model
security passwords min-length 10
banner motd ^C Authorized Access Only ^C
logging host 10.0.0.50
!
"""

INSECURE_CISCO = """!
version 15.2
hostname CISCO-VULN
line vty 0 4
 transport input telnet ssh
!
"""


def test_report_html_contains_device_findings(client, db_session):
    device = _ingest_and_evaluate(db_session, client, "cisco_report.cfg", INSECURE_CISCO)

    resp = client.get(f"/devices/{device.id}/report?framework=CIS")
    assert resp.status_code == 200

    data = resp.json()
    assert data["device"]["filename"] == "cisco_report.cfg"
    assert data["fail_count"] >= 1

    findings = [f for cat in data["grouped_findings"].values() for f in cat]
    rule_ids = [f["rule_id"] for f in findings]
    assert "CIS-1.1" in rule_ids

    failed_remediations = [f["remediation_text"] for f in findings if f["status"] == "fail"]
    assert any("no service telnet" in (r or "") for r in failed_remediations)


def test_report_html_shows_pass_for_hardened_config(client, db_session):
    device = _ingest_and_evaluate(db_session, client, "cisco_hardened_rpt.cfg", HARDENED_CISCO)

    resp = client.get(f"/devices/{device.id}/report?framework=CIS")
    assert resp.status_code == 200

    data = resp.json()
    assert data["pass_count"] >= 1
    assert data["fail_count"] == 0


def test_report_pdf_returns_valid_pdf(client, db_session):
    device = _ingest_and_evaluate(db_session, client, "cisco_pdf_test.cfg", INSECURE_CISCO)

    resp = client.get(f"/devices/{device.id}/report.pdf?framework=CIS")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"

    # Check PDF magic bytes
    assert resp.content[:5] == b"%PDF-"


def test_report_404_for_nonexistent_device(client, db_session):
    resp = client.get("/devices/99999/report")
    assert resp.status_code == 404


def test_dashboard_renders_with_evaluated_devices(client, db_session):
    _ingest_and_evaluate(db_session, client, "cisco_dash1.cfg", INSECURE_CISCO)
    _ingest_and_evaluate(db_session, client, "cisco_dash2.cfg", HARDENED_CISCO)

    resp = client.get("/dashboard")
    assert resp.status_code == 200

    data = resp.json()
    assert data["total_devices"] == 2
    assert len(data["device_summaries"]) == 2
    filenames = [d["filename"] for d in data["device_summaries"]]
    assert "cisco_dash1.cfg" in filenames
    assert "cisco_dash2.cfg" in filenames


def test_dashboard_empty_state(client, db_session):
    resp = client.get("/dashboard")
    assert resp.status_code == 200

    data = resp.json()
    assert data["total_devices"] == 0
    assert data["total_findings"] == 0

