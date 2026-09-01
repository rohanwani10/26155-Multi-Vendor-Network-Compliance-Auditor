from app.parsers.schema import empty_schema

#: No extraction logic at all for a truly unrecognized vendor — every field
#: is honestly absent_unknown, so this adapter declares zero coverage.
DECLARED_COVERAGE: frozenset = frozenset()


def normalize_unknown(text: str) -> dict:
    """Vendor entirely unrecognized: Tier-1 can't map anything, so every
    non-blank line becomes a Tier-2 candidate."""
    schema = empty_schema()
    schema["unrecognized_lines"] = [line.strip() for line in text.splitlines() if line.strip()]
    return schema
