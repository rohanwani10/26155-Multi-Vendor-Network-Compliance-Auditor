"""Item 1 (Correction 1) — every compliance verdict must be backed by real
evidence, never by an unexamined schema default.

Before this fix, `empty_schema()` defaults to concrete falsy values
(`False`/`0`), so a field the parser never saw evaluates identically to a
field the parser explicitly confirmed absent — producing confident Pass/Fail
verdicts on data that was never examined (see audit Q7/Correction 1: Juniper
fixture reports PASS on telnet and weak-ciphers, FAIL on ssh-version and
syslog, purely from unexamined defaults).

This test must fail against the pre-fix code: schema leaves are bare
bool/int values with no provenance to check at all."""

import yaml

from app.evaluator.engine import evaluate_rule
from app.parsers import normalize
from tests.test_tier1_parsing import FIXTURES, VENDOR_FIXTURES

with open("app/rules/cis.yaml", encoding="utf-8") as f:
    CIS_RULES = yaml.safe_load(f)["rules"]

VALID_STATUSES = {"pass", "fail", "manual_review"}
VERDICT_DERIVATIONS = {"explicit", "vendor_default"}


def _iter_vendor_rule_pairs():
    for vendor, fixture_name in VENDOR_FIXTURES.items():
        text = (FIXTURES / fixture_name).read_text()
        schema = normalize(vendor, text)
        for rule in CIS_RULES:
            yield vendor, rule, schema


def test_every_verdict_is_backed_by_real_evidence():
    """No control may report Pass or Fail unless the Observation backing it
    has derivation in {explicit, vendor_default}. A schema default the
    parser never examined must report Manual Review Required instead."""
    violations = []

    for vendor, rule, schema in _iter_vendor_rule_pairs():
        result = evaluate_rule(rule, schema, vendor=vendor, framework_name="CIS")
        status = result["status"]
        assert status in VALID_STATUSES, (
            f"{vendor}/{rule['id']}: status {status!r} is not one of {VALID_STATUSES}"
        )

        category = rule.get("category", "")
        field = rule.get("field", "")
        observation = schema.get(category, {}).get(field)

        is_observation_shaped = isinstance(observation, dict) and "derivation" in observation
        if not is_observation_shaped:
            if status in ("pass", "fail"):
                violations.append(
                    f"{vendor}/{rule['id']} ({category}.{field}): reported {status.upper()} "
                    f"but the backing value {observation!r} carries no provenance at all — "
                    f"cannot tell an examined field from an unexamined default"
                )
            continue

        if status in ("pass", "fail") and observation["derivation"] not in VERDICT_DERIVATIONS:
            violations.append(
                f"{vendor}/{rule['id']} ({category}.{field}): reported {status.upper()} "
                f"from derivation={observation['derivation']!r} — only "
                f"{VERDICT_DERIVATIONS} may produce a verdict"
            )

    assert not violations, "Verdicts issued on unexamined data:\n" + "\n".join(violations)


# Pinned to an inline minimal config, not the shared juniper_1.cfg fixture:
# item 2 (Correction 3) deliberately enriched that fixture to *prove* the
# adapter's declared aaa/password-length coverage, so it's no longer a case
# with zero signal. The tri-state behavior these pin still needs a genuine
# zero-signal case to regress against — this one, kept minimal on purpose.
MINIMAL_JUNIPER_CONFIG = """## Last commit
set system host-name MINIMAL-RTR
set system services ssh
"""


def test_juniper_missing_aaa_is_manual_review_not_a_false_pass():
    """No aaa/radius/tacacs line at all -> CIS-2.1 must be Manual Review,
    not a confident (and wrong) PASS."""
    schema = normalize("juniper", MINIMAL_JUNIPER_CONFIG)
    rule = next(r for r in CIS_RULES if r["id"] == "CIS-2.1")

    result = evaluate_rule(rule, schema, vendor="juniper", framework_name="CIS")
    assert result["status"] == "manual_review"


def test_juniper_missing_password_length_is_manual_review_not_a_false_fail():
    """No minimum-length line -> CIS-2.2 must be Manual Review, not a
    confident (and possibly wrong) FAIL against a default of 0."""
    schema = normalize("juniper", MINIMAL_JUNIPER_CONFIG)
    rule = next(r for r in CIS_RULES if r["id"] == "CIS-2.2")

    result = evaluate_rule(rule, schema, vendor="juniper", framework_name="CIS")
    assert result["status"] == "manual_review"
