"""Tier-1 normalizer for FortiOS block-style configs ('config ... edit ...
next ... end'). ntc-templates has zero Fortinet templates at all, so this
is direct line/block-based extraction."""

import re

from app.parsers.common import classify_unrecognized
from app.parsers.schema import empty_schema, observed

RECOGNIZED_PATTERNS = [re.compile(r"^(#|config\s|edit\s|next$|end$|set\s)", re.IGNORECASE)]

POLICY_FIELDS = ("srcintf", "dstintf", "action", "service")


def normalize_fortinet(text: str) -> dict:
    schema = empty_schema()

    telnet_match = re.search(r"^\s*set admin-telnet (enable|disable)", text, re.IGNORECASE | re.MULTILINE)
    if telnet_match:
        schema["management_plane"]["telnet_enabled"] = observed(
            telnet_match.group(1) == "enable", evidence=[telnet_match.group(0)]
        )

    ssh_match = re.search(r"^\s*set admin-ssh-port\b.*$", text, re.IGNORECASE | re.MULTILINE)
    if ssh_match:
        schema["management_plane"]["ssh_enabled"] = observed(True, evidence=[ssh_match.group(0)])
        schema["management_plane"]["ssh_version"] = observed(2, derivation="vendor_default", evidence=[ssh_match.group(0)])

    aaa_match = re.search(r"^config user (radius|tacacs\+|group)\b.*$", text, re.IGNORECASE | re.MULTILINE)
    if aaa_match:
        schema["auth"]["aaa_enabled"] = observed(True, evidence=[aaa_match.group(0)])

    pwd_match = re.search(r"^\s*set minimum-length (\d+)", text, re.IGNORECASE | re.MULTILINE)
    if pwd_match:
        schema["auth"]["password_min_length"] = observed(int(pwd_match.group(1)), evidence=[pwd_match.group(0)])

    banner_match = re.search(r"^\s*set (pre|post)-login-banner enable", text, re.IGNORECASE | re.MULTILINE)
    if banner_match:
        schema["auth"]["login_banner_configured"] = observed(True, evidence=[banner_match.group(0)])

    syslog_block = re.search(r"config log syslogd setting.*?set status enable", text, re.IGNORECASE | re.DOTALL)
    syslog_servers = re.findall(
        r"config log syslogd setting.*?set server \"?([^\"\n]+)\"?", text, re.IGNORECASE | re.DOTALL
    )
    if syslog_block:
        schema["logging"]["syslog_configured"] = observed(True, evidence=[syslog_block.group(0)])
    schema["logging"]["syslog_servers"] = syslog_servers

    schema["crypto"]["weak_ciphers_present"] = observed(
        bool(re.search(r"\b(3des|des-cbc|rc4|md5)\b", text, re.IGNORECASE))
    )

    schema["acl_rules"] = _extract_acls(text)
    schema["unrecognized_lines"] = classify_unrecognized(text.splitlines(), RECOGNIZED_PATTERNS)
    return schema


def _extract_acls(text: str) -> list[dict]:
    policy_block = re.search(r"config firewall policy(.*?)\nend", text, re.IGNORECASE | re.DOTALL)
    if not policy_block:
        return []

    rules = []
    for policy_id, body in re.findall(r"edit (\S+)(.*?)next", policy_block.group(1), re.DOTALL):
        entry = {"acl_name": policy_id}
        for field in POLICY_FIELDS:
            field_match = re.search(rf'set {field} "?([^"\n]+)"?', body)
            if field_match:
                entry[field] = field_match.group(1).strip()
        rules.append(entry)
    return rules
