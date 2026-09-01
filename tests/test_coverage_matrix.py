"""Item 2 (Correction 3) — the coverage matrix and its enforcement test.

A vendor adapter declares which fields it has real extraction logic for
(app.parsers.*.DECLARED_COVERAGE). This test fails when a declared field is
never actually backed by a real Observation against that vendor's own
canonical fixture — i.e. when the declaration overclaims what the adapter
(or its fixture) can actually prove."""

import yaml

from app.evaluator.coverage import compute_coverage, declared_vs_actual
from app.parsers import declared_coverage, normalize
from tests.test_tier1_parsing import FIXTURES, VENDOR_FIXTURES

with open("app/rules/cis.yaml", encoding="utf-8") as f:
    CIS_RULES = yaml.safe_load(f)["rules"]


def test_declared_coverage_never_exceeds_actual_coverage():
    """This is the enforcement mechanism for Correction 1: an adapter must
    be able to prove every field it claims to cover, against its own
    fixture, or the declaration is a lie and the fixture needs enriching."""
    failures = []
    for vendor in VENDOR_FIXTURES:
        text = (FIXTURES / VENDOR_FIXTURES[vendor]).read_text()
        schema = normalize(vendor, text)
        result = declared_vs_actual(vendor, schema, declared_coverage(vendor))
        if result["gaps"]:
            failures.append(
                f"{vendor}: declares {result['declared_count']} fields but its fixture only "
                f"demonstrates {result['actual_count']} — gaps: {result['gaps']}"
            )

    assert not failures, "Declared coverage exceeds what the fixture proves:\n" + "\n".join(failures)


def test_coverage_summary_matches_control_count():
    """Sanity check on compute_coverage's own arithmetic, independent of
    any particular fixture's content."""
    for vendor in VENDOR_FIXTURES:
        text = (FIXTURES / VENDOR_FIXTURES[vendor]).read_text()
        schema = normalize(vendor, text)
        summary = compute_coverage(schema, CIS_RULES)
        assert summary["total_controls"] == len(CIS_RULES)
        assert 0 <= summary["evaluable_count"] <= summary["total_controls"]


def test_unknown_vendor_declares_zero_coverage():
    text = (FIXTURES / "unknown_device.txt").read_text()
    schema = normalize("unknown", text)
    summary = compute_coverage(schema, CIS_RULES)
    assert summary["evaluable_count"] == 0
