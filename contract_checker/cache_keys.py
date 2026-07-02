"""Stable, privacy-preserving cache key helpers for session-only caches."""

from __future__ import annotations

import hashlib


_CACHE_SEPARATOR = b"\x00"


def _hash_parts(parts: list[bytes]) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(_CACHE_SEPARATOR)
        digest.update(part)
    return digest.hexdigest()


def ocr_page_cache_key(*, image_bytes: bytes, model: str, prompt_version: str) -> str:
    """Return a stable OCR cache key for an already-redacted prepared page image.

    The key intentionally excludes API keys, raw uploaded images, and filenames.
    """

    if not isinstance(image_bytes, bytes) or not image_bytes:
        raise ValueError("image_bytes must be non-empty bytes")
    return _hash_parts(
        [
            b"ocr_page_cache_v1",
            image_bytes,
            (model or "").strip().encode("utf-8"),
            (prompt_version or "").strip().encode("utf-8"),
        ]
    )


def analysis_cache_key(*, redacted_text: str, model: str, prompt_text: str, schema_version: str) -> str:
    """Return a stable final-analysis cache key for already-redacted contract text."""

    if not redacted_text or not redacted_text.strip():
        raise ValueError("redacted_text must be non-empty")
    return _hash_parts(
        [
            b"analysis_cache_v1",
            redacted_text.encode("utf-8"),
            (model or "").strip().encode("utf-8"),
            (prompt_text or "").encode("utf-8"),
            (schema_version or "").strip().encode("utf-8"),
        ]
    )
