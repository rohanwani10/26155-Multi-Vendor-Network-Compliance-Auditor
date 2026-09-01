from unittest.mock import patch

from app.models import LearnedRule, ParsedConfig, PendingReview
from app.pipeline import ingest_one


def test_training_loop_end_to_end(client, db_session):
    # 1. Ingest a config with an unrecognized line that low-confidence LLM queues for review
    unknown_line = "custom-vendor-cmd disable telnet-access"
    config_text = f"hostname test-router\n{unknown_line}\n"

    with patch("app.tier2.fallback.classify_via_llm") as mock_llm:
        mock_llm.return_value = {
            "category": "management_plane",
            "field": "telnet_enabled",
            "value": False,
            "confidence": 0.40,  # Below 0.75 threshold -> queue for review
        }
        device = ingest_one(db_session, "cisco_device_1.cfg", config_text)
        db_session.commit()


    # Verify PendingReview record was created
    pending = (
        db_session.query(PendingReview)
        .filter(PendingReview.device_id == device.id, PendingReview.raw_line == unknown_line)
        .first()
    )
    assert pending is not None
    assert pending.raw_line == unknown_line
    assert pending.status == "pending"


    # 2. Check /training UI endpoint
    response = client.get("/training")
    assert response.status_code == 200
    pending_items = response.json()
    assert any(item["raw_line"] == unknown_line for item in pending_items)

    # 3. Resolve the item via POST /training/resolve
    resolve_resp = client.post(
        "/training/resolve",
        data={
            "review_id": pending.id,
            "category": "management_plane",
            "field": "telnet_enabled",
            "value": "False",
        },
    )
    assert resolve_resp.status_code == 200
    res_data = resolve_resp.json()
    assert "Successfully resolved" in res_data["message"]


    # 4. Assert LearnedRule created and PendingReview cleared from queue
    assert db_session.query(PendingReview).filter(PendingReview.id == pending.id).first() is None

    learned = db_session.query(LearnedRule).filter(LearnedRule.raw_pattern == unknown_line).first()
    assert learned is not None
    assert learned.category == "management_plane"
    assert learned.field == "telnet_enabled"


    # 5. Assert ParsedConfig schema was re-normalized and updated
    parsed_config = db_session.query(ParsedConfig).filter(ParsedConfig.device_id == device.id).first()
    assert parsed_config.normalized_json["management_plane"]["telnet_enabled"] is False
    assert unknown_line not in parsed_config.normalized_json["unrecognized_lines"]

    # 6. Ingest a SECOND device with the exact SAME line.
    # Assert that classify_via_llm is NOT called (resolved via Chroma embedding match instead).
    with patch("app.tier2.fallback.classify_via_llm") as mock_llm_second:
        device2 = ingest_one(db_session, "cisco_device_2.cfg", config_text)
        db_session.commit()


        mock_llm_second.assert_not_called()

    parsed_config2 = db_session.query(ParsedConfig).filter(ParsedConfig.device_id == device2.id).first()
    assert parsed_config2.normalized_json["management_plane"]["telnet_enabled"] is False
    assert unknown_line not in parsed_config2.normalized_json["unrecognized_lines"]
    assert parsed_config2.parse_tier == 2
    assert parsed_config2.confidence_score is not None and parsed_config2.confidence_score >= 0.9
