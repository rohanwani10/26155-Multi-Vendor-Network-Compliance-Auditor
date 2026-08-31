"""Cloud LLM classification module (Groq / OpenAI / OpenAI-compatible REST API).
Called as a fallback when local Ollama is offline or unreachable."""

import json
import os

import httpx

from app.tier2.llm_classifier import SYSTEM_PROMPT


class CloudLLMError(RuntimeError):
    """Raised when the Cloud LLM API call fails or returns unparseable output."""


def is_cloud_llm_enabled() -> bool:
    enabled = os.environ.get("CLOUD_LLM_ENABLED", "false").lower() in ("true", "1", "yes")
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("CLOUD_LLM_API_KEY")
    return enabled and bool(api_key)


def classify_via_cloud_llm(line: str, vendor: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("CLOUD_LLM_API_KEY")
    if not api_key:
        raise CloudLLMError("Cloud LLM enabled but neither GROQ_API_KEY nor CLOUD_LLM_API_KEY is set.")

    provider = os.environ.get("CLOUD_LLM_PROVIDER", "groq").lower()
    default_base_url = (
        "https://api.groq.com/openai/v1"
        if provider == "groq"
        else "https://api.openai.com/v1"
    )
    base_url = os.environ.get("CLOUD_LLM_BASE_URL", default_base_url)
    model = os.environ.get("CLOUD_LLM_MODEL", "llama-3.1-8b-instant")

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f'Vendor: {vendor}\nLine: "{line}"'},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
    }

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise CloudLLMError(f"Cloud LLM API call failed ({url}): {exc}") from exc

    try:
        data = response.json()
        raw_content = data["choices"][0]["message"]["content"]
        parsed = json.loads(raw_content)
    except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
        raise CloudLLMError(f"Invalid JSON response from Cloud LLM: {exc}") from exc

    return {
        "category": parsed.get("category"),
        "field": parsed.get("field"),
        "value": parsed.get("value"),
        "confidence": float(parsed.get("confidence") or 0.0),
    }
