"""Tier-2 fallback orchestration: embedding match against learned patterns
first, local LLM classification second, in that order (PRD G3)."""

import os

from app.tier2.embeddings import find_learned_match
from app.tier2.llm_classifier import LLMClassificationError, classify_via_llm

CONFIDENCE_THRESHOLD = float(os.environ.get("TIER2_CONFIDENCE_THRESHOLD", "0.75"))

APPLICABLE_CATEGORIES = {"management_plane", "auth", "logging", "crypto"}


def classify_line(vendor: str, line: str) -> dict:
    """Returns {"category", "field", "value", "confidence", "source"}
    where source is "learned", "llm", or "error". Never raises - an
    unreachable/unparseable LLM comes back as confidence 0.0 so the caller
    always falls through to the training queue instead of crashing the
    upload or silently guessing."""
    learned = find_learned_match(vendor, line)
    if learned is not None:
        return {**learned, "source": "learned"}

    try:
        result = classify_via_llm(line, vendor)
    except LLMClassificationError:
        return {"category": None, "field": None, "value": None, "confidence": 0.0, "source": "error"}

    return {**result, "source": "llm"}


def is_confident(result: dict) -> bool:
    return result.get("confidence", 0.0) >= CONFIDENCE_THRESHOLD


def is_applicable(result: dict) -> bool:
    """Whether a confident result can be auto-applied straight into the
    schema. Only the 4 dict-shaped categories are safe to key-set into;
    acl_rules (a list) and unclassifiable results always go to review."""
    return result.get("category") in APPLICABLE_CATEGORIES and bool(result.get("field"))
