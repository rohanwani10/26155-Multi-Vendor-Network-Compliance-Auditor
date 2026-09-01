def absent() -> dict:
    """A schema leaf the parser never found any signal for. `value` is None
    and MUST NOT be compared against a rule's `expected` value directly —
    the evaluator (app/evaluator/engine.py) treats derivation="absent_unknown"
    as Manual Review Required, never Pass or Fail. Absent configuration is
    not disabled configuration: the parser not finding a `transport input`
    line at all is a different fact from finding one that omits telnet."""
    return {"value": None, "derivation": "absent_unknown", "evidence": [], "confidence": 0.0}


def observed(value, derivation: str = "explicit", evidence: list | None = None, confidence: float = 1.0) -> dict:
    """A schema leaf backed by a real signal: a line the parser actually
    matched (derivation="explicit", confidence=1.0 for deterministic regex,
    or the classifier's own confidence for a Tier-2-applied value), or a
    documented platform default the adapter deliberately applied
    (derivation="vendor_default", e.g. "Junos SSH is always v2 once enabled").
    Only these two derivations may back a Pass/Fail verdict."""
    return {"value": value, "derivation": derivation, "evidence": evidence or [], "confidence": confidence}


def empty_schema() -> dict:
    """Vendor-neutral schema skeleton. Every scalar compliance leaf starts
    `absent()` — a concrete "not yet examined" state, not a guessed False/0 —
    so the Phase 5 rule evaluator never issues a confident verdict on data no
    adapter actually looked at. `acl_rules`/`syslog_servers`/`unrecognized_lines`
    stay plain lists: no CIS rule compares them as a scalar, and an empty
    list is already an honest, unambiguous "found nothing" (list membership
    doesn't have the "absent vs. examined-and-false" ambiguity a bool does)."""
    return {
        "management_plane": {
            "telnet_enabled": absent(),
            "ssh_enabled": absent(),
            "ssh_version": absent(),
        },
        "auth": {
            "aaa_enabled": absent(),
            "password_min_length": absent(),
            "login_banner_configured": absent(),
        },
        "logging": {
            "syslog_configured": absent(),
            "syslog_servers": [],
        },
        "acl_rules": [],
        "crypto": {
            "weak_ciphers_present": absent(),
        },
        "unrecognized_lines": [],
    }
