def empty_schema() -> dict:
    """Vendor-neutral schema skeleton. Leaf fields default to their
    "not found" value (False / 0 / empty list) rather than None, so the
    Phase 5 rule evaluator always has a concrete value to compare against
    and the Phase 2 exit criteria ('>80% of fields populated, not null')
    is met by construction."""
    return {
        "management_plane": {
            "telnet_enabled": False,
            "ssh_enabled": False,
            "ssh_version": 0,
        },
        "auth": {
            "aaa_enabled": False,
            "password_min_length": 0,
            "login_banner_configured": False,
        },
        "logging": {
            "syslog_configured": False,
            "syslog_servers": [],
        },
        "acl_rules": [],
        "crypto": {
            "weak_ciphers_present": False,
        },
        "unrecognized_lines": [],
    }
