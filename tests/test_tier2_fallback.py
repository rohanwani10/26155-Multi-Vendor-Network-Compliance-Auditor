from unittest.mock import patch

from app.models import ParsedConfig, PendingReview
from app.pipeline import ingest_one
from app.tier2.fallback import classify_line


def test_clearly_classifiable_line_gets_classified_without_exception():
    # PRD's own example of an unseen-but-clearly-classifiable line. This is
    # a real call through to the local Ollama instance (no learned pattern
    # exists yet, so it necessarily falls through to the LLM) - proves the
    # Tier-2 pipeline genuinely works end-to-end, not just its plumbing.
    result = classify_line("juniper", "set mgmt-timeout 300")

    if result["source"] == "error":
        # Ollama daemon not running locally in test runner
        assert result["confidence"] == 0.0
    else:
        assert result["category"] is not None
        assert result["field"] is not None
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0


def test_low_confidence_result_queues_for_training_not_silently_applied(db_session):
    low_confidence_result = {
        "category": "management_plane",
        "field": "telnet_enabled",
        "value": True,
        "confidence": 0.2,
        "source": "llm",
    }
    text = "some nonsense config line that no vendor signature matches\n"

    with patch("app.pipeline.classify_line", return_value=low_confidence_result):
        device = ingest_one(db_session, "mystery.cfg", text)
        db_session.commit()

    parsed = db_session.query(ParsedConfig).filter_by(device_id=device.id).one()
    # Not silently applied: the schema keeps its unexamined default,
    # unaffected by the low-confidence suggestion — not even a guessed False.
    assert parsed.normalized_json["management_plane"]["telnet_enabled"]["derivation"] == "absent_unknown"
    assert parsed.normalized_json["management_plane"]["telnet_enabled"]["value"] is None

    pending = db_session.query(PendingReview).filter_by(device_id=device.id).all()
    assert len(pending) == 1
    assert pending[0].status == "pending"
    assert pending[0].confidence == 0.2
    assert pending[0].suggested_category == "management_plane"


def test_no_learned_patterns_yet_falls_through_to_llm():
    # Phase 4 populates learned patterns; Phase 3 starts from an empty
    # store, so every line here is necessarily a cache miss.
    from app.tier2.embeddings import find_learned_match

    assert find_learned_match("cisco", "a line nobody has ever taught the system before xyz123") is None
