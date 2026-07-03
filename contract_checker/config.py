"""Local configuration helpers for the contract checker MVP.

This module centralizes Gemini API key loading without printing or logging the
key. It is safe to import outside Streamlit and in unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Mapping


GEMINI_API_KEY_NAME = "GEMINI_API_KEY"
API_KEY_SOURCE_STREAMLIT_SECRETS = "streamlit_secrets"
API_KEY_SOURCE_ENVIRONMENT = "environment"
API_KEY_SOURCE_MISSING = "missing"


@dataclass(frozen=True)
class GeminiAPIKeyConfig:
    """Gemini API key value plus non-sensitive source metadata."""

    value: str
    source: str

    @property
    def found(self) -> bool:
        return bool(self.value.strip())


def _coerce_secret_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _load_streamlit_secrets() -> Mapping[str, Any] | None:
    try:
        import streamlit as st
    except Exception:
        return None
    try:
        return st.secrets
    except Exception:
        return None


def load_gemini_api_key_from_local_config(
    *,
    secrets: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> GeminiAPIKeyConfig:
    """Load Gemini API key from Streamlit secrets or environment variables.

    Precedence:
    1. `.streamlit/secrets.toml` via `st.secrets["GEMINI_API_KEY"]`
    2. OS environment variable `GEMINI_API_KEY`

    The returned object contains the key value and a safe source label only. The
    caller must never print the key value.
    """

    resolved_secrets = _load_streamlit_secrets() if secrets is None else secrets
    if resolved_secrets is not None:
        try:
            secret_value = _coerce_secret_value(resolved_secrets.get(GEMINI_API_KEY_NAME))
        except Exception:
            secret_value = ""
        if secret_value:
            return GeminiAPIKeyConfig(value=secret_value, source=API_KEY_SOURCE_STREAMLIT_SECRETS)

    resolved_environ = os.environ if environ is None else environ
    env_value = _coerce_secret_value(resolved_environ.get(GEMINI_API_KEY_NAME))
    if env_value:
        return GeminiAPIKeyConfig(value=env_value, source=API_KEY_SOURCE_ENVIRONMENT)

    return GeminiAPIKeyConfig(value="", source=API_KEY_SOURCE_MISSING)


def api_key_source_label(source: str) -> str:
    """Return a user-facing label without exposing the key value."""

    labels = {
        API_KEY_SOURCE_STREAMLIT_SECRETS: ".streamlit/secrets.toml",
        API_KEY_SOURCE_ENVIRONMENT: "environment variable GEMINI_API_KEY",
        API_KEY_SOURCE_MISSING: "not configured",
        "manual": "manual UI input",
    }
    return labels.get(source, source or API_KEY_SOURCE_MISSING)
