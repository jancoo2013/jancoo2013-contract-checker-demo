"""Provider-neutral Cloud OCR interfaces for future integrations.

This module intentionally contains no provider SDK calls, API keys, secrets, or
network requests. It defines the shape that the Streamlit demo can use later when
cloud OCR is wired through secure configuration such as Streamlit secrets.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, BinaryIO, Iterable


SUPPORTED_CLOUD_OCR_PROVIDERS = {
    "not_configured": "Cloud OCR ещё не подключён",
    "google_vision": "Google Cloud Vision OCR",
    "azure_vision": "Azure AI Vision Read OCR",
}


@dataclass(frozen=True)
class CloudOCRPageResult:
    """Provider-neutral OCR result for a single uploaded page/image."""

    page_index: int
    filename: str
    raw_text: str = ""
    blocks: list[dict[str, Any]] = field(default_factory=list)
    success: bool = False
    error: str | None = None
    provider: str = "not_configured"
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary for Streamlit and tests."""

        return asdict(self)


@dataclass(frozen=True)
class CloudOCRContractResult:
    """Provider-neutral OCR result for a whole contract/document."""

    raw_text: str = ""
    pages: list[CloudOCRPageResult] = field(default_factory=list)
    success: bool = False
    error: str | None = None
    provider: str = "not_configured"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary for Streamlit and tests."""

        return asdict(self)


@dataclass(frozen=True)
class CloudOCRResult:
    """Backward-compatible disabled OCR result used by older callers/tests."""

    raw_text: str = ""
    pages: list[dict[str, Any]] = field(default_factory=list)
    ocr_available: bool = False
    error: str | None = "Cloud OCR provider is not configured yet."
    provider: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary for Streamlit and tests."""

        return asdict(self)


def combine_cloud_ocr_pages(pages: list[CloudOCRPageResult]) -> str:
    """Combine page texts with explicit Russian page separators."""

    page_sections = []
    for page in pages:
        page_text = page.raw_text.strip()
        page_sections.append(
            f"--- СТРАНИЦА {page.page_index}: {page.filename} ---\n{page_text}"
        )
    return "\n\n".join(page_sections).strip()


def get_provider_status(provider: str) -> dict[str, Any]:
    """Return current public-demo configuration status for a Cloud OCR provider."""

    provider_label = SUPPORTED_CLOUD_OCR_PROVIDERS.get(provider, provider)
    return {
        "configured": False,
        "provider": provider,
        "provider_label": provider_label,
        "message": (
            f"{provider_label}: секреты/API-ключи не настроены. "
            "Для включения Cloud OCR нужно добавить ключи в Streamlit secrets; "
            "ключи нельзя хранить в GitHub."
        ),
    }


def _uploaded_filename(image_file: Any, fallback_index: int) -> str:
    """Return a stable display name for an uploaded file-like object."""

    name = getattr(image_file, "name", "")
    return str(name) if name else f"page-{fallback_index}.jpg"


def _not_configured_result(
    image_files: Iterable[BinaryIO], provider: str, message: str
) -> CloudOCRContractResult:
    """Build a disabled provider result without reading files or making network calls."""

    pages = [
        CloudOCRPageResult(
            page_index=index,
            filename=_uploaded_filename(image_file, index),
            provider=provider,
            success=False,
            error=message,
        )
        for index, image_file in enumerate(image_files, start=1)
    ]
    return CloudOCRContractResult(
        raw_text=combine_cloud_ocr_pages(pages),
        pages=pages,
        success=False,
        error=message,
        provider=provider,
    )


def ocr_with_google_vision(image_files: Iterable[BinaryIO]) -> CloudOCRContractResult:
    """Disabled Google Cloud Vision OCR stub for the public demo."""

    return _not_configured_result(
        image_files,
        provider="google_vision",
        message=(
            "Провайдер Google Cloud Vision пока не настроен. "
            "Нужно добавить ключ в Streamlit secrets."
        ),
    )


def ocr_with_azure_vision(image_files: Iterable[BinaryIO]) -> CloudOCRContractResult:
    """Disabled Azure AI Vision Read OCR stub for the public demo."""

    return _not_configured_result(
        image_files,
        provider="azure_vision",
        message=(
            "Провайдер Azure AI Vision пока не настроен. "
            "Нужно добавить ключ в Streamlit secrets."
        ),
    )


def ocr_images_with_cloud_provider(
    image_files: Iterable[BinaryIO], provider: str
) -> dict[str, Any]:
    """Backward-compatible placeholder for future cloud OCR image processing."""

    if provider == "google_vision":
        result = ocr_with_google_vision(image_files)
        return result.to_dict()
    if provider == "azure_vision":
        result = ocr_with_azure_vision(image_files)
        return result.to_dict()

    # Consume no files and make no network calls. Keeping the argument in the
    # interface makes future implementations a drop-in replacement.
    del image_files
    return CloudOCRResult(provider=provider).to_dict()
