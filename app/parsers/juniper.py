"""Tier-1 normalizer for Junos 'set'-style configs. Junos syntax is flat
declarative statements ('set <namespace> ... <value>'), not the parent/child
block structure ciscoconfparse2 targets, and ntc-templates ships no Junos
running-config template, so this is a direct line-based extraction."""

import re

from app.parsers.common import classify_unrecognized
from app.parsers.schema import empty_schema

RECOGNIZED_PATTERNS = [re.compile(r"^(##|set\s)", re.IGNORECASE)]

ACL_TERM_RE = re.compile(r"^set firewall filter (\S+) term (\S+) (from|then) (.+)$")


def normalize_juniper(text: str) -> dict:
    schema = empty_schema()

    schema["management_plane"]["telnet_enabled"] = bool(
        re.search(r"^set system services telnet\b", text, re.IGNORECASE | re.MULTILINE)
    )
    ssh_enabled = bool(re.search(r"^set system services ssh\b", text, re.IGNORECASE | re.MULTILINE))
    schema["management_plane"]["ssh_enabled"] = ssh_enabled
    # Modern Junos only supports SSHv2 once ssh service is enabled.
    schema["management_plane"]["ssh_version"] = 2 if ssh_enabled else 0

    schema["auth"]["aaa_enabled"] = bool(
        re.search(
            r"^set system (authentication-order|radius-server|tacplus-server)\b",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
    )
    pwd_match = re.search(
        r"^set system login password minimum-length (\d+)", text, re.IGNORECASE | re.MULTILINE
    )
    schema["auth"]["password_min_length"] = int(pwd_match.group(1)) if pwd_match else 0
    schema["auth"]["login_banner_configured"] = bool(
        re.search(r"^set system login message\b", text, re.IGNORECASE | re.MULTILINE)
    )

    syslog_hosts = re.findall(r"^set system syslog host (\S+)", text, re.IGNORECASE | re.MULTILINE)
    schema["logging"]["syslog_configured"] = bool(syslog_hosts)
    schema["logging"]["syslog_servers"] = syslog_hosts

    schema["crypto"]["weak_ciphers_present"] = bool(
        re.search(r"\b(3des|des-cbc|rc4|md5)\b", text, re.IGNORECASE)
    )

    schema["acl_rules"] = _extract_acls(text)
    schema["unrecognized_lines"] = classify_unrecognized(text.splitlines(), RECOGNIZED_PATTERNS)
    return schema


def _extract_acls(text: str) -> list[dict]:
    terms: dict[tuple[str, str], dict] = {}
    for line in text.splitlines():
        match = ACL_TERM_RE.match(line.strip())
        if not match:
            continue
        filter_name, term_name, clause, rest = match.groups()
        entry = terms.setdefault(
            (filter_name, term_name),
            {"acl_name": filter_name, "term": term_name, "protocol": None, "port": None, "action": None},
        )
        if clause == "from":
            if rest.startswith("protocol"):
                entry["protocol"] = rest.split()[-1]
            elif rest.startswith("port"):
                entry["port"] = rest.split()[-1]
        else:
            entry["action"] = rest.strip()
    return list(terms.values())
