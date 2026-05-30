"""Cloud OCR adapter interfaces for future integrations.

This module intentionally contains no provider SDK calls, API keys, secrets, or
network requests. It defines the shape that the Streamlit demo can use later when
cloud OCR is wired through secure configuration such as Streamlit secrets.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, BinaryIO, Iterable


@dataclass(frozen=True)
class CloudOCRResult:
    """Provider-neutral OCR result returned by a future cloud OCR backend."""

    raw_text: str = ""
    pages: list[dict[str, Any]] = field(default_factory=list)
    ocr_available: bool = False
    error: str | None = "Cloud OCR provider is not configured yet."
    provider: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary for Streamlit and tests."""

        return asdict(self)


def ocr_images_with_cloud_provider(image_files: Iterable[BinaryIO], provider: str) -> dict[str, Any]:
    """Placeholder for future cloud OCR image processing.

    The public demo must not make paid OCR calls or expose API-key fields yet, so
    this adapter currently returns an explicit disabled response while preserving
    the planned contract for later provider-specific implementations.
    """

    # Consume no files and make no network calls. Keeping the argument in the
    # interface makes future implementations a drop-in replacement.
    del image_files
    return CloudOCRResult(provider=provider).to_dict()
