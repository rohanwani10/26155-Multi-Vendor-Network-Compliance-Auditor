"""Shared Tier-1 normalizer for IOS-style hierarchical configs (Cisco IOS,
Arista EOS). Single-line boolean/value fields are extracted with plain
regex; ciscoconfparse2 handles the one genuinely hierarchical structure we
care about (nested ACL blocks), and each extracted ACL body is parsed with
TextFSM using a project-authored template (ntc-templates ships no
running-config-dump templates for any of these platforms - only narrow
per-command ones - so a custom template is used here for the ACE rows,
which are the one place in these configs that's genuinely tabular)."""

import re
from pathlib import Path

import textfsm
from ciscoconfparse2 import CiscoConfParse

from app.parsers.common import classify_unrecognized
from app.parsers.schema import empty_schema, observed

ACL_TEXTFSM_TEMPLATE = Path(__file__).parent / "textfsm_templates" / "acl_entries.textfsm"

#: Fields this adapter has real extraction logic for (Correction 3's
#: coverage matrix) — declares capability, not "this file happens to have
#: it." tests/test_coverage_matrix.py enforces that the bundled fixture
#: actually demonstrates every field declared here.
DECLARED_COVERAGE = frozenset({
    "management_plane.telnet_enabled",
    "management_plane.ssh_enabled",
    "management_plane.ssh_version",
    "auth.aaa_enabled",
    "auth.password_min_length",
    "auth.login_banner_configured",
    "logging.syslog_configured",
    "crypto.weak_ciphers_present",
})

WEAK_CIPHER_RE = re.compile(r"\b(3des|des-cbc|rc4)\b", re.IGNORECASE)

# Lines recognized as valid IOS-style syntax, whether or not they map to a
# schema field. Anything NOT matching one of these is a genuine Tier-2
# candidate (unknown construct), not just "syntax we don't care about".
RECOGNIZED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^!",
        r"^building configuration",
        r"^current configuration",
        r"^version \d",
        r"^(no )?service ",
        r"^hostname ",
        r"^(no )?ip domain",
        r"^username ",
        r"^line (con|vty|aux)",
        r"^enable secret",
        r"^transport input",
        r"^login( local)?$",
        r"^aaa ",
        r"^no aaa",
        r"^banner",
        r"^\^C",
        r"^logging (host|trap)",
        r"^security passwords",
        r"^crypto key generate",
        r"^ip ssh version",
        r"^ip access-list",
        r"^(permit|deny)\b",
        r"^end$",
    )
]


def normalize(text: str) -> dict:
    schema = empty_schema()

    transport_input_lines = re.findall(r"^\s*transport input.*$", text, re.IGNORECASE | re.MULTILINE)
    if transport_input_lines:
        schema["management_plane"]["telnet_enabled"] = observed(
            any("telnet" in line.lower() for line in transport_input_lines), evidence=transport_input_lines
        )
        schema["management_plane"]["ssh_enabled"] = observed(
            any("ssh" in line.lower() for line in transport_input_lines), evidence=transport_input_lines
        )

    ssh_version_match = re.search(r"^ip ssh version (\d)", text, re.IGNORECASE | re.MULTILINE)
    if ssh_version_match:
        schema["management_plane"]["ssh_version"] = observed(
            int(ssh_version_match.group(1)), evidence=[ssh_version_match.group(0)]
        )

    aaa_match = re.search(r"^(no )?aaa (new-model|authentication login)", text, re.IGNORECASE | re.MULTILINE)
    if aaa_match:
        schema["auth"]["aaa_enabled"] = observed(not aaa_match.group(1), evidence=[aaa_match.group(0)])

    pwd_match = re.search(r"^security passwords min-length (\d+)", text, re.IGNORECASE | re.MULTILINE)
    if pwd_match:
        schema["auth"]["password_min_length"] = observed(int(pwd_match.group(1)), evidence=[pwd_match.group(0)])

    banner_match = re.search(r"^banner (motd|login|exec)\b.*$", text, re.IGNORECASE | re.MULTILINE)
    if banner_match:
        schema["auth"]["login_banner_configured"] = observed(True, evidence=[banner_match.group(0)])

    syslog_hosts = re.findall(r"^logging host (\S+)", text, re.IGNORECASE | re.MULTILINE)
    if syslog_hosts:
        schema["logging"]["syslog_configured"] = observed(True, evidence=syslog_hosts)
    schema["logging"]["syslog_servers"] = syslog_hosts

    # A full-text scan for a banned substring is exhaustive by nature — there
    # is no "unknown" middle state the way there is for e.g. a VTY transport
    # default: either the string appears in the file or it provably doesn't.
    schema["crypto"]["weak_ciphers_present"] = observed(bool(WEAK_CIPHER_RE.search(text)))

    schema["acl_rules"] = _extract_acls(text)
    schema["unrecognized_lines"] = classify_unrecognized(text.splitlines(), RECOGNIZED_PATTERNS)
    return schema


def _extract_acls(text: str) -> list[dict]:
    parse = CiscoConfParse(text.splitlines(), syntax="ios")
    rules = []
    for acl_obj in parse.find_objects(r"^ip access-list"):
        acl_name = acl_obj.text.split()[-1]
        body = "\n".join(child.text for child in acl_obj.children)
        if not body.strip():
            continue
        with ACL_TEXTFSM_TEMPLATE.open() as template_file:
            fsm = textfsm.TextFSM(template_file)
            for row in fsm.ParseText(body):
                entry = {key.lower(): value for key, value in zip(fsm.header, row)}
                entry["acl_name"] = acl_name
                rules.append(entry)
    return rules
