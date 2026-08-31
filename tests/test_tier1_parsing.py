from pathlib import Path

from app.models import Device, ParsedConfig
from app.parsers import normalize

FIXTURES = Path(__file__).parent / "fixtures" / "configs"

VENDOR_FIXTURES = {
    "cisco": "cisco_ios_1.cfg",
    "arista": "arista_1.cfg",
    "juniper": "juniper_1.cfg",
    "paloalto": "paloalto_1.cfg",
    "fortinet": "fortinet_1.cfg",
}


def _leaf_values(schema: dict) -> list:
    """Flatten the schema's scalar leaves (skip list-valued fields like
    acl_rules/unrecognized_lines/syslog_servers, which are structurally
    always present as a list rather than a single populated value)."""
    leaves = []
    for value in schema.values():
        if isinstance(value, dict):
            leaves.extend(_leaf_values(value))
        elif isinstance(value, list):
            continue
        else:
            leaves.append(value)
    return leaves


def test_cisco_telnet_enabled_is_bool_not_none():
    text = (FIXTURES / VENDOR_FIXTURES["cisco"]).read_text()
    schema = normalize("cisco", text)
    assert isinstance(schema["management_plane"]["telnet_enabled"], bool)
    assert schema["management_plane"]["telnet_enabled"] is True  # vty 0 4 allows telnet


def test_juniper_fields_populated():
    text = (FIXTURES / VENDOR_FIXTURES["juniper"]).read_text()
    schema = normalize("juniper", text)
    assert isinstance(schema["management_plane"]["telnet_enabled"], bool)
    assert isinstance(schema["management_plane"]["ssh_enabled"], bool)
    assert isinstance(schema["auth"]["aaa_enabled"], bool)
    assert isinstance(schema["logging"]["syslog_configured"], bool)
    assert schema["management_plane"]["telnet_enabled"] is True
    assert schema["management_plane"]["ssh_enabled"] is True
    assert schema["logging"]["syslog_configured"] is True
    assert schema["logging"]["syslog_servers"] == ["10.0.0.50"]


def test_injected_nonsense_line_is_captured_not_dropped():
    base = (FIXTURES / VENDOR_FIXTURES["cisco"]).read_text()
    nonsense = "FROBNICATE_UNKNOWN_DIRECTIVE_XYZ"
    injected = base + "\n" + nonsense + "\n"

    schema = normalize("cisco", injected)

    assert nonsense in schema["unrecognized_lines"]


def test_injected_nonsense_line_captured_for_set_style_vendor():
    base = (FIXTURES / VENDOR_FIXTURES["juniper"]).read_text()
    nonsense = "FROBNICATE_UNKNOWN_DIRECTIVE_XYZ"
    injected = base + "\n" + nonsense + "\n"

    schema = normalize("juniper", injected)

    assert nonsense in schema["unrecognized_lines"]


def test_all_five_vendor_fixtures_normalize_with_over_80_percent_fields_populated():
    for vendor, fixture_name in VENDOR_FIXTURES.items():
        text = (FIXTURES / fixture_name).read_text()
        schema = normalize(vendor, text)
        leaves = _leaf_values(schema)
        populated = [v for v in leaves if v is not None]
        ratio = len(populated) / len(leaves)
        assert ratio > 0.8, f"{vendor}: only {ratio:.0%} of fields populated"


def test_all_five_vendor_fixtures_produce_well_formed_schema():
    required_top_level = {"management_plane", "auth", "logging", "acl_rules", "crypto", "unrecognized_lines"}
    for vendor, fixture_name in VENDOR_FIXTURES.items():
        text = (FIXTURES / fixture_name).read_text()
        schema = normalize(vendor, text)
        assert required_top_level.issubset(schema.keys())
        assert isinstance(schema["acl_rules"], list)


def test_cisco_and_arista_acl_blocks_extracted_via_ciscoconfparse_and_textfsm():
    cisco_schema = normalize("cisco", (FIXTURES / VENDOR_FIXTURES["cisco"]).read_text())
    assert cisco_schema["acl_rules"] == [
        {"action": "deny", "protocol": "tcp", "source": "any", "dest": "any", "port": "23", "acl_name": "BLOCK-TELNET-IN"},
        {"action": "permit", "protocol": "ip", "source": "any", "dest": "any", "port": "", "acl_name": "BLOCK-TELNET-IN"},
    ]

    arista_schema = normalize("arista", (FIXTURES / VENDOR_FIXTURES["arista"]).read_text())
    assert len(arista_schema["acl_rules"]) == 2
    assert arista_schema["acl_rules"][0]["acl_name"] == "MGMT-ACL"


def test_unknown_vendor_puts_everything_in_unrecognized():
    text = (FIXTURES / "unknown_device.txt").read_text()
    schema = normalize("unknown", text)
    assert schema["unrecognized_lines"]
    assert schema["management_plane"]["telnet_enabled"] is False


def test_upload_persists_normalized_json_and_parse_tier(client, db_session):
    content = (FIXTURES / VENDOR_FIXTURES["cisco"]).read_bytes()
    response = client.post(
        "/devices/upload",
        files={"file": ("cisco_ios_1.cfg", content, "text/plain")},
    )
    assert response.status_code == 200

    device = db_session.query(Device).one()
    parsed = db_session.query(ParsedConfig).filter_by(device_id=device.id).one()
    assert parsed.parse_tier == 1
    assert parsed.normalized_json["management_plane"]["telnet_enabled"] is True
