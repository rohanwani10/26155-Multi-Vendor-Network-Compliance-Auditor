from unittest.mock import patch

import yaml

from app.evaluator.engine import evaluate_device, evaluate_rule
from app.models import Finding
from app.pipeline import ingest_one


def test_evaluation_fails_for_telnet_enabled(client, db_session):
    # cisco_ios_1.cfg fixture has Telnet enabled (transport input telnet ssh)
    cisco_text = """!
version 15.2
hostname CISCO-GW01
line vty 0 4
 transport input telnet ssh
!
"""
    device = ingest_one(db_session, "cisco_gw.cfg", cisco_text)
    db_session.commit()

    # Trigger evaluation endpoint for CIS
    response = client.post(f"/evaluate/{device.id}?framework=CIS")
    assert response.status_code == 200
    data = response.json()

    assert data["device_id"] == device.id
    assert data["framework"] == "CIS"
    assert data["summary"]["fail_count"] >= 1

    # Find the Telnet rule finding
    telnet_finding = next((f for f in data["findings"] if f["rule_id"] == "CIS-1.1"), None)
    assert telnet_finding is not None
    assert telnet_finding["status"] == "fail"
    assert telnet_finding["severity"] == "CRITICAL"
    assert "no service telnet" in telnet_finding["remediation_text"]

    # Verify Finding record in DB
    db_finding = (
        db_session.query(Finding)
        .filter(Finding.device_id == device.id, Finding.rule_id == "CIS-1.1")
        .first()
    )
    assert db_finding is not None
    assert db_finding.status == "fail"


def test_evaluation_passes_for_hardened_config(client, db_session):
    hardened_cisco = """!
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
    device = ingest_one(db_session, "cisco_hardened.cfg", hardened_cisco)
    db_session.commit()

    findings = evaluate_device(db_session, device, framework="CIS")
    db_session.commit()

    telnet = next(f for f in findings if f.rule_id == "CIS-1.1")
    assert telnet.status == "pass"

    ssh_ver = next(f for f in findings if f.rule_id == "CIS-1.3")
    assert ssh_ver.status == "pass"

    aaa = next(f for f in findings if f.rule_id == "CIS-2.1")
    assert aaa.status == "pass"

    pwd_len = next(f for f in findings if f.rule_id == "CIS-2.2")
    assert pwd_len.status == "pass"

    banner = next(f for f in findings if f.rule_id == "CIS-2.3")
    assert banner.status == "pass"

    syslog = next(f for f in findings if f.rule_id == "CIS-3.1")
    assert syslog.status == "pass"


def test_evaluation_nist_framework(client, db_session):
    cisco_text = """!
version 15.2
hostname CISCO-GW02
line vty 0 4
 transport input telnet ssh
!
"""
    device = ingest_one(db_session, "cisco_nist.cfg", cisco_text)
    db_session.commit()

    # Trigger evaluation endpoint for NIST
    response = client.post(f"/evaluate/{device.id}?framework=NIST")
    assert response.status_code == 200
    data = response.json()

    assert data["framework"] == "NIST"
    assert data["summary"]["total_rules"] >= 7

    telnet_rule = next((f for f in data["findings"] if f["rule_id"] == "NIST-AC-17.1"), None)
    assert telnet_rule is not None
    assert telnet_rule["status"] == "fail"
    assert "no service telnet" in telnet_rule["remediation_text"]

    # Verify GET endpoint
    get_res = client.get(f"/devices/{device.id}/findings?framework=NIST")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["framework"] == "NIST"
    assert len(get_data["findings"]) == len(data["findings"])


def test_evaluation_stig_framework(client, db_session):
    # Use flat 'set'-style Junos config (what the Tier-1 Juniper parser supports)
    juniper_text = """## Last commit
set system host-name JUNIPER-01
set system services telnet
set system services ssh protocol-version v2
"""
    device = ingest_one(db_session, "juniper_stig.cfg", juniper_text)
    db_session.commit()

    response = client.post(f"/evaluate/{device.id}?framework=STIG")
    assert response.status_code == 200
    data = response.json()

    assert data["framework"] == "STIG"
    telnet_rule = next((f for f in data["findings"] if f["rule_id"] == "STIG-NET-0001"), None)
    assert telnet_rule is not None
    assert telnet_rule["status"] == "fail"
    assert "delete system services telnet" in telnet_rule["remediation_text"]


def test_evaluation_iso_framework(client, db_session):
    palo_text = """
set deviceconfig system service disable-telnet no
set deviceconfig system ssh-protocol-version v2
"""
    device = ingest_one(db_session, "palo_iso.cfg", palo_text)
    db_session.commit()

    response = client.post(f"/evaluate/{device.id}?framework=ISO")
    assert response.status_code == 200
    data = response.json()

    assert data["framework"] == "ISO"
    telnet_rule = next((f for f in data["findings"] if f["rule_id"] == "ISO-A.13.1.1"), None)
    assert telnet_rule is not None
    assert telnet_rule["status"] == "fail"
    assert "disable-telnet yes" in telnet_rule["remediation_text"]


def test_yaml_rule_added_without_code_changes():
    custom_yaml = """
id: cis_v1_0
framework: CIS
rules:
  - id: CIS-9.9
    title: Custom dynamic YAML rule
    category: auth
    field: password_min_length
    operator: ">="
    expected: 15
    severity: HIGH
    remediation:
      cisco: "security passwords min-length 15"
      default: "Increase password length"
"""
    rule_pack = yaml.safe_load(custom_yaml)
    rule = rule_pack["rules"][0]

    # Evaluate against a schema with password_min_length = 10
    schema = {"auth": {"password_min_length": 10}}
    result = evaluate_rule(rule, schema, vendor="cisco", framework_name="CIS")

    assert result["rule_id"] == "CIS-9.9"
    assert result["status"] == "fail"
    assert result["severity"] == "HIGH"
    assert result["remediation_text"] == "security passwords min-length 15"
