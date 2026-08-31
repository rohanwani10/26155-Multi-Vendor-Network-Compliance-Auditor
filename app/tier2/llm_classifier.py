"""Local Ollama classification for a single unrecognized config line.
Talks to Ollama's REST API directly over httpx (already a dependency for
testing) rather than adding the separate `ollama` PyPI client - one HTTP
POST doesn't need its own SDK. Fully on-prem: no external network calls."""

import json
import os

import httpx

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
# Default model is whatever's already pulled on the target machine, per the
# PRD's own guidance that the exact model is a config swap, not a code
# change (phi3:mini / llama3.1:8b are drop-in alternatives via this env var).
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:4b")

SYSTEM_PROMPT = """You classify a single line from a network device configuration file into a compliance schema.
Categories and example fields:
- management_plane: telnet_enabled, ssh_enabled, ssh_version, mgmt_timeout_seconds
- auth: aaa_enabled, password_min_length, login_banner_configured
- logging: syslog_configured, syslog_servers
- crypto: weak_ciphers_present
- acl_rules: access control entries

Respond with ONLY a JSON object of the form:
{"category": "<one of the categories above>", "field": "<short snake_case field name>", "value": <the extracted value>, "confidence": <float 0.0-1.0>}

If you cannot confidently classify the line, still respond with your best guess but use a confidence below 0.5.

Example:
Line: "set mgmt-timeout 300"
Response: {"category": "management_plane", "field": "mgmt_timeout_seconds", "value": 300, "confidence": 0.85}"""


class LLMClassificationError(RuntimeError):
    """Ollama unreachable or returned something we couldn't parse. Callers
    treat this as "queue for human review", never as a silent guess."""


def classify_via_llm(line: str, vendor: str) -> dict:
    prompt = f'{SYSTEM_PROMPT}\n\nVendor: {vendor}\nLine: "{line}"\nResponse:'
    try:
        response = httpx.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "format": "json", "stream": False},
            timeout=60.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise LLMClassificationError(f"Ollama unreachable at {OLLAMA_HOST}: {exc}") from exc

    raw_output = response.json().get("response", "")
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise LLMClassificationError(f"Unparseable LLM output: {raw_output!r}") from exc

    return {
        "category": parsed.get("category"),
        "field": parsed.get("field"),
        "value": parsed.get("value"),
        "confidence": float(parsed.get("confidence") or 0.0),
    }
