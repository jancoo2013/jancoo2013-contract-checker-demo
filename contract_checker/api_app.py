"""Minimal FastAPI adapter for the first mobile privacy-boundary slice."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Annotated, Protocol
from uuid import uuid4

from fastapi import FastAPI, File, Form
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .api_handler import ContractAnalysisHandler, OCRQualityPoorError, TextUnusableError
from .api_models import (
    APIErrorBody,
    APIErrorResponse,
    AnalyzeRedactedContractResponse,
    AnalyzeRedactedMetadata,
)
from .config import load_gemini_api_key_from_local_config
from .gemini_engine import (
    GeminiAuthenticationError,
    GeminiConfigurationError,
    GeminiRateLimitError,
    GeminiResponseError,
)


_PNG_SIGNATURE = bytes.fromhex("89504E470D0A1A0A")
_CLIENT_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")


@dataclass(frozen=True)
class RedactedPagePayload:
    page_index: int
    filename: str
    image_bytes: bytes


class AnalyzeHandler(Protocol):
    async def __call__(
        self,
        pages: list[RedactedPagePayload],
        metadata: AnalyzeRedactedMetadata,
        request_id: str,
    ) -> AnalyzeRedactedContractResponse: ...


class APIServiceUnavailable(RuntimeError):
    """Raised when the endpoint skeleton has no analysis handler wired yet."""


async def _unwired_handler(
    pages: list[RedactedPagePayload],
    metadata: AnalyzeRedactedMetadata,
    request_id: str,
) -> AnalyzeRedactedContractResponse:
    del pages, metadata, request_id
    raise APIServiceUnavailable("analysis handler is not wired")


def _error_response(
    *,
    request_id: str,
    status_code: int,
    code: str,
    message_ru: str,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    payload = APIErrorResponse(
        request_id=request_id,
        error=APIErrorBody(
            code=code,
            message_ru=message_ru,
            details=details or {},
        ),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def _valid_client_request_id(value: str | None) -> bool:
    if value is None:
        return True
    return bool(value) and len(value) <= 128 and bool(_CLIENT_REQUEST_ID_RE.fullmatch(value))


def _normalize_pages(page_bytes: list[bytes]) -> list[RedactedPagePayload] | None:
    normalized: list[RedactedPagePayload] = []
    for page_index, image_bytes in enumerate(page_bytes):
        if not image_bytes.startswith(_PNG_SIGNATURE):
            return None
        normalized.append(
            RedactedPagePayload(
                page_index=page_index,
                filename=f"page_{page_index + 1}.png",
                image_bytes=image_bytes,
            )
        )
    return normalized


def create_app(handler: AnalyzeHandler | None = None) -> FastAPI:
    """Create the API app with an injectable analysis handler for tests and production wiring."""

    analyze_handler = handler or _unwired_handler
    app = FastAPI(title="Contract Checker API", version="0.1.0")

    @app.post(
        "/v1/contracts/analyze-redacted",
        response_model=AnalyzeRedactedContractResponse,
        responses={
            400: {"model": APIErrorResponse},
            415: {"model": APIErrorResponse},
            422: {"model": APIErrorResponse},
            502: {"model": APIErrorResponse},
            503: {"model": APIErrorResponse},
        },
    )
    async def analyze_redacted_contract(
        pages: Annotated[list[bytes] | None, File()] = None,
        privacy_review_confirmed: Annotated[bool, Form()] = False,
        client_request_id: Annotated[str | None, Form()] = None,
    ) -> AnalyzeRedactedContractResponse | JSONResponse:
        request_id = uuid4().hex

        if not privacy_review_confirmed:
            return _error_response(
                request_id=request_id,
                status_code=400,
                code="privacy_review_required",
                message_ru="Перед отправкой нужно завершить локальную проверку и маскирование личных данных.",
            )
        if not pages:
            return _error_response(
                request_id=request_id,
                status_code=400,
                code="invalid_request",
                message_ru="Не переданы подготовленные страницы договора.",
            )
        if not _valid_client_request_id(client_request_id):
            return _error_response(
                request_id=request_id,
                status_code=400,
                code="invalid_request",
                message_ru="Некорректный client_request_id.",
            )

        try:
            metadata = AnalyzeRedactedMetadata(
                privacy_review_confirmed=True,
                client_request_id=client_request_id,
            )
        except ValidationError:
            return _error_response(
                request_id=request_id,
                status_code=400,
                code="invalid_request",
                message_ru="Некорректные метаданные запроса.",
            )

        normalized_pages = _normalize_pages(pages)
        if normalized_pages is None:
            return _error_response(
                request_id=request_id,
                status_code=415,
                code="unsupported_page_media_type",
                message_ru="Первая версия API принимает только подготовленные PNG-страницы.",
            )

        try:
            return await analyze_handler(normalized_pages, metadata, request_id)
        except OCRQualityPoorError:
            return _error_response(
                request_id=request_id,
                status_code=422,
                code="ocr_quality_poor",
                message_ru="Качество распознавания слишком низкое для надёжного анализа.",
            )
        except TextUnusableError:
            return _error_response(
                request_id=request_id,
                status_code=422,
                code="text_unusable",
                message_ru="Распознанный текст непригоден для надёжного анализа договора.",
            )
        except GeminiRateLimitError:
            return _error_response(
                request_id=request_id,
                status_code=503,
                code="upstream_rate_limited",
                message_ru="Сервис анализа временно перегружен. Повторите попытку позже.",
            )
        except (GeminiAuthenticationError, GeminiConfigurationError, APIServiceUnavailable):
            return _error_response(
                request_id=request_id,
                status_code=503,
                code="upstream_unavailable",
                message_ru="Сервис анализа временно недоступен.",
            )
        except GeminiResponseError:
            return _error_response(
                request_id=request_id,
                status_code=502,
                code="upstream_invalid_response",
                message_ru="Внешний сервис вернул ответ, непригодный для обработки.",
            )

    return app


def create_production_app() -> FastAPI:
    """Create the production API app with the existing server-side Gemini key loader."""

    key_config = load_gemini_api_key_from_local_config()
    return create_app(ContractAnalysisHandler(api_key=key_config.value))


app = create_production_app()
