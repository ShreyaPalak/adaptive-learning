"""
LLM Gateway — the ONLY module in the codebase that talks to the LLM API.

Responsibilities: auth/config, request construction, JSON-mode enforcement,
retries with backoff, timeout handling, and metadata-only logging. Callers
get back parsed dicts or a GatewayError — never raw HTTP internals.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger("llm_gateway")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 2


class GatewayError(Exception):
    """Raised for any recoverable-by-the-caller LLM failure. Message is
    always safe to show to the end user (no secrets, no stack traces)."""


@dataclass
class LLMResponse:
    data: dict
    raw_text: str


def _get_api_key() -> str:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise GatewayError(
            "The AI service isn't configured (missing API key). "
            "Please set GROQ_API_KEY in your .env file."
        )
    return key


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t.rsplit("```", 1)[0]
    return t.strip()


def call_llm_json(prompt: str, *, model: str | None = None, max_tokens: int = 3000, temperature: float = 0.4) -> LLMResponse:
    """Send a prompt expecting a single JSON object back. Retries on
    transient failures and malformed JSON. Never logs the prompt or
    response content — only metadata (status, attempt, latency)."""
    api_key = _get_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    last_error: str = ""
    for attempt in range(1, MAX_RETRIES + 2):  # e.g. 3 total tries
        start = time.monotonic()
        try:
            resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.Timeout:
            last_error = "The AI service timed out."
            logger.warning("llm_gateway timeout attempt=%s", attempt)
            time.sleep(min(2 ** attempt, 5))
            continue
        except requests.RequestException:
            last_error = "Could not reach the AI service."
            logger.warning("llm_gateway network_error attempt=%s", attempt)
            time.sleep(min(2 ** attempt, 5))
            continue

        latency = time.monotonic() - start

        if resp.status_code == 401:
            raise GatewayError("The AI service rejected the API key. Check your GROQ_API_KEY.")
        if resp.status_code == 429:
            last_error = "The AI service is rate-limited right now."
            logger.warning("llm_gateway rate_limited attempt=%s latency=%.2f", attempt, latency)
            time.sleep(min(2 ** attempt, 8))
            continue
        if resp.status_code >= 500:
            last_error = "The AI service is temporarily unavailable."
            logger.warning("llm_gateway server_error status=%s attempt=%s", resp.status_code, attempt)
            time.sleep(min(2 ** attempt, 5))
            continue
        if resp.status_code >= 400:
            logger.warning("llm_gateway client_error status=%s attempt=%s", resp.status_code, resp.text[:1000],)
            raise GatewayError(f"The AI service rejected the request ({resp.status_code}). "
        f"Details: {resp.text[:500]}")

        try:
            body = resp.json()
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError):
            last_error = "The AI service returned an unexpected response."
            logger.warning("llm_gateway bad_shape attempt=%s", attempt)
            continue

        cleaned = _strip_code_fences(content)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            last_error = "The AI service returned malformed data."
            logger.warning("llm_gateway bad_json attempt=%s", attempt)
            continue

        logger.info("llm_gateway success attempt=%s latency=%.2f", attempt, latency)
        return LLMResponse(data=parsed, raw_text=cleaned)

    raise GatewayError(last_error or "The AI service failed after multiple attempts. Please try again.")
