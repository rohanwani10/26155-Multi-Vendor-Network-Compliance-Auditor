import re


def classify_unrecognized(lines: list[str], recognized_patterns: list[re.Pattern]) -> list[str]:
    """Return the lines that don't match any known field-pattern or
    ignorable/structural pattern for this vendor's syntax. These are
    candidates for Phase 3's Tier-2 fallback, never silently dropped."""
    unrecognized = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if any(pattern.search(line) for pattern in recognized_patterns):
            continue
        unrecognized.append(line)
    return unrecognized
