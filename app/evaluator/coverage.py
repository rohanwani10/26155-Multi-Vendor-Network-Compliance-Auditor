"""Coverage matrix (Correction 3): for a normalized schema and a rule pack,
report which controls are actually evaluable (backed by a real
explicit/vendor_default Observation) versus which require configuration
data no adapter extracted for this device. One computation, reused as the
UI indicator, the PDF provenance section, and the enforcement test."""

from app.evaluator.engine import VERDICT_DERIVATIONS


def compute_coverage(schema: dict, rules: list[dict]) -> dict:
    controls = []
    for rule in rules:
        category = rule.get("category", "")
        field = rule.get("field", "")
        observation = schema.get(category, {}).get(field)

        if isinstance(observation, dict) and "derivation" in observation:
            derivation = observation["derivation"]
        else:
            derivation = "explicit"  # backward-compat: bare-value schema

        controls.append(
            {
                "rule_id": rule.get("id"),
                "title": rule.get("title"),
                "category": category,
                "field": field,
                "evaluable": derivation in VERDICT_DERIVATIONS,
                "derivation": derivation,
            }
        )

    evaluable_count = sum(1 for c in controls if c["evaluable"])
    return {
        "evaluable_count": evaluable_count,
        "total_controls": len(controls),
        "controls": controls,
    }


def declared_vs_actual(vendor: str, schema: dict, declared_fields: frozenset) -> dict:
    """For Correction 3's enforcement test: which fields this adapter
    *declares* it can extract were actually backed by a real Observation in
    this schema. A gap here means either the adapter's regex doesn't work,
    or the declaration overclaims — either way, a real defect to fix, not a
    test to weaken."""
    gaps = []
    for path in sorted(declared_fields):
        category, field = path.split(".", 1)
        observation = schema.get(category, {}).get(field)
        derivation = observation.get("derivation") if isinstance(observation, dict) else "explicit"
        if derivation not in VERDICT_DERIVATIONS:
            gaps.append(path)

    return {
        "vendor": vendor,
        "declared_count": len(declared_fields),
        "actual_count": len(declared_fields) - len(gaps),
        "gaps": gaps,
    }
