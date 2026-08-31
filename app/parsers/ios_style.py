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
from app.parsers.schema import empty_schema

ACL_TEXTFSM_TEMPLATE = Path(__file__).parent / "textfsm_templates" / "acl_entries.textfsm"

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

    schema["management_plane"]["telnet_enabled"] = bool(
        re.search(r"^\s*transport input.*\btelnet\b", text, re.IGNORECASE | re.MULTILINE)
    )
    schema["management_plane"]["ssh_enabled"] = bool(
        re.search(r"^\s*transport input.*\bssh\b", text, re.IGNORECASE | re.MULTILINE)
    )
    ssh_version_match = re.search(r"^ip ssh version (\d)", text, re.IGNORECASE | re.MULTILINE)
    schema["management_plane"]["ssh_version"] = int(ssh_version_match.group(1)) if ssh_version_match else 0

    schema["auth"]["aaa_enabled"] = bool(
        re.search(r"^aaa (new-model|authentication login)", text, re.IGNORECASE | re.MULTILINE)
    )
    pwd_match = re.search(r"^security passwords min-length (\d+)", text, re.IGNORECASE | re.MULTILINE)
    schema["auth"]["password_min_length"] = int(pwd_match.group(1)) if pwd_match else 0
    schema["auth"]["login_banner_configured"] = bool(
        re.search(r"^banner (motd|login|exec)", text, re.IGNORECASE | re.MULTILINE)
    )

    syslog_hosts = re.findall(r"^logging host (\S+)", text, re.IGNORECASE | re.MULTILINE)
    schema["logging"]["syslog_configured"] = bool(syslog_hosts)
    schema["logging"]["syslog_servers"] = syslog_hosts

    schema["crypto"]["weak_ciphers_present"] = bool(WEAK_CIPHER_RE.search(text))

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
