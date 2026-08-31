from unittest.mock import MagicMock, patch

from app.tier2.cloud_llm import classify_via_cloud_llm
from app.tier2.fallback import classify_line
from app.tier2.llm_classifier import LLMClassificationError


def test_ollama_offline_falls_back_to_cloud_llm(monkeypatch):
    monkeypatch.setenv("CLOUD_LLM_ENABLED", "true")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_mock_key_123")

    cloud_result = {
        "category": "management_plane",
        "field": "telnet_enabled",
        "value": False,
        "confidence": 0.88,
    }

    with patch("app.tier2.fallback.classify_via_llm", side_effect=LLMClassificationError("Ollama offline")), \
         patch("app.tier2.fallback.classify_via_cloud_llm", return_value=cloud_result):
        result = classify_line("cisco", "custom-groq-line disable telnet")

    assert result["source"] == "cloud"
    assert result["category"] == "management_plane"
    assert result["field"] == "telnet_enabled"
    assert result["confidence"] == 0.88


def test_cloud_llm_disabled_defaults_to_error(monkeypatch):
    monkeypatch.setenv("CLOUD_LLM_ENABLED", "false")

    with patch("app.tier2.fallback.classify_via_llm", side_effect=LLMClassificationError("Ollama offline")):
        result = classify_line("cisco", "custom-groq-line disable telnet")

    assert result["source"] == "error"
    assert result["confidence"] == 0.0


def test_classify_via_cloud_llm_groq_response(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_mock_api_key_xyz")
    monkeypatch.setenv("CLOUD_LLM_PROVIDER", "groq")
    monkeypatch.setenv("CLOUD_LLM_MODEL", "llama-3.1-8b-instant")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"category": "auth", "field": "password_min_length", "value": 12, "confidence": 0.95}'
                }
            }
        ]
    }

    with patch("httpx.post", return_value=mock_response) as mock_post:
        res = classify_via_cloud_llm("security passwords min-length 12", "cisco")

    mock_post.assert_called_once()
    assert res["category"] == "auth"
    assert res["field"] == "password_min_length"
    assert res["value"] == 12
    assert res["confidence"] == 0.95
