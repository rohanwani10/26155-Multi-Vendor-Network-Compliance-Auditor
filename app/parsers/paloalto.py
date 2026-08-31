"""Tier-1 normalizer for PAN-OS 'set'-style configs. Same rationale as
juniper.py: flat declarative statements, no matching ntc-templates
coverage, so direct line-based extraction."""

import re

from app.parsers.common import classify_unrecognized
from app.parsers.schema import empty_schema

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
    schema["management_plane"]["telnet_enabled"] = bool(telnet_match) and telnet_match.group(1) == "no"

    ssh_match = re.search(
        r"^set deviceconfig system service disable-ssh (yes|no)", text, re.IGNORECASE | re.MULTILINE
    )
    ssh_enabled = bool(ssh_match) and ssh_match.group(1) == "no"
    schema["management_plane"]["ssh_enabled"] = ssh_enabled
    # PAN-OS management SSH is SSHv2-only.
    schema["management_plane"]["ssh_version"] = 2 if ssh_enabled else 0

    schema["auth"]["aaa_enabled"] = bool(
        re.search(r"authentication-profile\s+\S", text, re.IGNORECASE | re.MULTILINE)
    )
    pwd_match = re.search(
        r"^set shared password-complexity minimum-length (\d+)", text, re.IGNORECASE | re.MULTILINE
    )
    schema["auth"]["password_min_length"] = int(pwd_match.group(1)) if pwd_match else 0
    schema["auth"]["login_banner_configured"] = bool(
        re.search(r"^set deviceconfig system login-banner\b", text, re.IGNORECASE | re.MULTILINE)
    )

    syslog_servers = re.findall(
        r"^set shared log-settings syslog \S+ server (\S+)", text, re.IGNORECASE | re.MULTILINE
    )
    schema["logging"]["syslog_configured"] = bool(syslog_servers)
    schema["logging"]["syslog_servers"] = syslog_servers

    schema["crypto"]["weak_ciphers_present"] = bool(
        re.search(r"\b(3des|des-cbc|rc4|md5)\b", text, re.IGNORECASE)
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
