"""Tier-1 normalizer for Junos 'set'-style configs. Junos syntax is flat
declarative statements ('set <namespace> ... <value>'), not the parent/child
block structure ciscoconfparse2 targets, and ntc-templates ships no Junos
running-config template, so this is a direct line-based extraction."""

import re

from app.parsers.common import classify_unrecognized
from app.parsers.schema import empty_schema, observed

RECOGNIZED_PATTERNS = [re.compile(r"^(##|set\s)", re.IGNORECASE)]

ACL_TERM_RE = re.compile(r"^set firewall filter (\S+) term (\S+) (from|then) (.+)$")


def normalize_juniper(text: str) -> dict:
    schema = empty_schema()

    telnet_match = re.search(r"^set system services telnet\b", text, re.IGNORECASE | re.MULTILINE)
    ssh_match = re.search(r"^set system services ssh\b", text, re.IGNORECASE | re.MULTILINE)
    # These are two independent opt-in directives in Junos, so "neither line
    # is present" and "ssh present, telnet absent" are both real, distinct,
    # fully-observed states here — not signal-not-found the way a shared
    # Cisco `transport input` line's absence would be.
    if telnet_match or ssh_match:
        schema["management_plane"]["telnet_enabled"] = observed(
            bool(telnet_match), evidence=[m.group(0) for m in (telnet_match, ssh_match) if m]
        )
        schema["management_plane"]["ssh_enabled"] = observed(bool(ssh_match), evidence=[ssh_match.group(0)] if ssh_match else [])
        if ssh_match:
            # Modern Junos only supports SSHv2 once the ssh service is enabled
            # at all — a documented platform fact, not a guess, but only
            # applicable once we've actually observed ssh being turned on.
            schema["management_plane"]["ssh_version"] = observed(2, derivation="vendor_default", evidence=[ssh_match.group(0)])

    aaa_match = re.search(
        r"^set system (authentication-order|radius-server|tacplus-server)\b",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if aaa_match:
        schema["auth"]["aaa_enabled"] = observed(True, evidence=[aaa_match.group(0)])

    pwd_match = re.search(
        r"^set system login password minimum-length (\d+)", text, re.IGNORECASE | re.MULTILINE
    )
    if pwd_match:
        schema["auth"]["password_min_length"] = observed(int(pwd_match.group(1)), evidence=[pwd_match.group(0)])

    banner_match = re.search(r"^set system login message\b.*$", text, re.IGNORECASE | re.MULTILINE)
    if banner_match:
        schema["auth"]["login_banner_configured"] = observed(True, evidence=[banner_match.group(0)])

    syslog_hosts = re.findall(r"^set system syslog host (\S+)", text, re.IGNORECASE | re.MULTILINE)
    if syslog_hosts:
        schema["logging"]["syslog_configured"] = observed(True, evidence=syslog_hosts)
    schema["logging"]["syslog_servers"] = syslog_hosts

    schema["crypto"]["weak_ciphers_present"] = observed(
        bool(re.search(r"\b(3des|des-cbc|rc4|md5)\b", text, re.IGNORECASE))
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
