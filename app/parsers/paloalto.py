"""Tier-1 normalizer for PAN-OS 'set'-style configs. Same rationale as
juniper.py: flat declarative statements, no matching ntc-templates
coverage, so direct line-based extraction."""

import re

from app.parsers.common import classify_unrecognized
from app.parsers.schema import empty_schema, observed

RECOGNIZED_PATTERNS = [re.compile(r"^set\s", re.IGNORECASE)]

ACL_RULE_RE = re.compile(
    r"set rulebase security rules (\S+) from (\S+) to (\S+) "
    r"source (\S+) destination (\S+) application (\S+) action (\S+)"
)


def normalize_paloalto(text: str) -> dict:
    schema = empty_schema()

    telnet_match = re.search(
        r"^set deviceconfig system service disable-telnet (yes|no)", text, re.IGNORECASE | re.MULTILINE
    )
    if telnet_match:
        schema["management_plane"]["telnet_enabled"] = observed(
            telnet_match.group(1) == "no", evidence=[telnet_match.group(0)]
        )

    ssh_match = re.search(
        r"^set deviceconfig system service disable-ssh (yes|no)", text, re.IGNORECASE | re.MULTILINE
    )
    if ssh_match:
        ssh_enabled = ssh_match.group(1) == "no"
        schema["management_plane"]["ssh_enabled"] = observed(ssh_enabled, evidence=[ssh_match.group(0)])
        # PAN-OS management SSH is SSHv2-only — a documented platform fact,
        # applicable once we've observed the service is actually enabled.
        if ssh_enabled:
            schema["management_plane"]["ssh_version"] = observed(2, derivation="vendor_default", evidence=[ssh_match.group(0)])

    aaa_match = re.search(r"authentication-profile\s+\S+", text, re.IGNORECASE | re.MULTILINE)
    if aaa_match:
        schema["auth"]["aaa_enabled"] = observed(True, evidence=[aaa_match.group(0)])

    pwd_match = re.search(
        r"^set shared password-complexity minimum-length (\d+)", text, re.IGNORECASE | re.MULTILINE
    )
    if pwd_match:
        schema["auth"]["password_min_length"] = observed(int(pwd_match.group(1)), evidence=[pwd_match.group(0)])

    banner_match = re.search(r"^set deviceconfig system login-banner\b.*$", text, re.IGNORECASE | re.MULTILINE)
    if banner_match:
        schema["auth"]["login_banner_configured"] = observed(True, evidence=[banner_match.group(0)])

    syslog_servers = re.findall(
        r"^set shared log-settings syslog \S+ server (\S+)", text, re.IGNORECASE | re.MULTILINE
    )
    if syslog_servers:
        schema["logging"]["syslog_configured"] = observed(True, evidence=syslog_servers)
    schema["logging"]["syslog_servers"] = syslog_servers

    schema["crypto"]["weak_ciphers_present"] = observed(
        bool(re.search(r"\b(3des|des-cbc|rc4|md5)\b", text, re.IGNORECASE))
    )

    schema["acl_rules"] = [
        {
            "acl_name": name,
            "from_zone": from_zone,
            "to_zone": to_zone,
            "source": source,
            "destination": destination,
            "application": application,
            "action": action,
        }
        for name, from_zone, to_zone, source, destination, application, action in ACL_RULE_RE.findall(text)
    ]
    schema["unrecognized_lines"] = classify_unrecognized(text.splitlines(), RECOGNIZED_PATTERNS)
    return schema
