# Mobile ↔ Backend Boundary and Minimal API Contract

Status: architecture contract for the first mobile vertical slice.

This document fixes the privacy boundary and the smallest backend API needed to connect a mobile client to the existing Python analysis core. It is intentionally narrower than a production API design.

## 1. Privacy boundary

The device owns every operation before external OCR:

`raw photo → on-device preprocessing → local privacy-pass / PII detection → user review → physical masking/redaction → prepared redacted image`

Only the prepared redacted image may cross the network boundary.

The backend owns:

`prepared redacted image → external OCR → deterministic post-OCR processing → contract analysis → evidence validation → Russian report`

Hard rules:

- raw photos must never be uploaded to the backend;
- the API must not define a field for raw photos;
- original filenames must not be trusted or persisted because they may contain PII;
- the mobile client should send generated neutral page names such as `page_1.png`;
- the Gemini API key belongs to the backend and is never sent to or entered into the mobile app;
- image bytes, OCR text, redacted text, and model responses must not be written to application logs;
- request bodies must not be captured by debug middleware, tracing payload capture, or error reporting;
- MVP processing is request-scoped and in-memory unless a later persistence design is explicitly approved;
- successful request handling is not proof that all PII was removed. The backend cannot infer privacy safety from the presence of masks alone.

## 2. First-slice API shape

Use one synchronous endpoint for the first vertical slice:

`POST /v1/contracts/analyze-redacted`

Why one endpoint now:

- it proves the mobile privacy boundary end-to-end;
- it reuses the current Python service layer without introducing job infrastructure;
- it keeps auth, history, persistence, resumable uploads, queues, and payments out of the first slice;
- it is easy to split into asynchronous jobs later without changing the on-device privacy boundary.

## 3. Request

Content type:

`multipart/form-data`

Fields:

### `pages`

One or more repeated PNG file parts.

Requirements:

- accepted media type: `image/png`;
- order of multipart parts defines page order;
- filenames are treated as display metadata only and must be normalized server-side;
- the server must not accept a parallel `raw_pages`, `original_pages`, or equivalent field;
- configured page-count and payload-size limits may evolve without changing the v1 semantic contract.

### `privacy_review_confirmed`

Boolean, required, must be `true`.

Meaning: the client states that the local review/redaction step was completed before upload.

This is a workflow gate, not cryptographic proof and not a server-side guarantee that no residual PII exists.

### `client_request_id`

Optional client-generated opaque identifier for idempotency/debug correlation.

Rules:

- must not contain a person name, address, phone number, ID number, filename, or contract text;
- the server may generate its own `request_id` regardless of whether this field is present.

## 4. Backend orchestration

The endpoint should orchestrate existing layers in this order:

1. validate multipart shape and media types;
2. normalize page order and neutral page names;
3. call OCR only with the uploaded redacted PNG bytes;
4. pass OCR text to `process_ocr_text(...)`;
5. stop before final analysis when OCR quality is `poor`;
6. stop before final analysis when text validation is unusable;
7. pass `redacted_text` to `run_contract_analysis(...)`;
8. serialize a mobile-safe response.

Important boundary:

`OCRProcessingResult.raw_ocr_text` is internal request-scoped data. The API must not return it by default, because residual PII may still exist when local masking missed something.

The normal mobile response should use only:

- OCR quality summaries;
- page quality summaries and reshoot hints;
- text validation summary;
- completeness audit;
- validated contract analysis result;
- evidence warnings safe for display/debug.

## 5. Success response

HTTP `200 OK`

Example shape:

```json
{
  "request_id": "opaque-server-id",
  "status": "completed",
  "ocr_quality": {
    "status": "good",
    "score": 86,
    "pages": [
      {
        "page_number": 1,
        "status": "good",
        "score": 84,
        "reshoot_hint_ru": ""
      }
    ]
  },
  "text_validation": {
    "usable": true,
    "completeness": "medium",
    "problems": []
  },
  "completeness_audit": {
    "status": "referenced_documents_need_check",
    "summary_ru": "...",
    "findings": []
  },
  "report": {},
  "evidence_warnings": []
}
```

`report` is the JSON serialization of the existing validated `ContractAuditResult`.

The API adapter should not create a second mobile-specific legal schema unless the current report schema proves unsuitable in real client integration.

## 6. Expected controlled failures

### `400 Bad Request`

Examples:

- missing pages;
- `privacy_review_confirmed` absent or false;
- malformed multipart request.

Stable error codes should include:

- `invalid_request`
- `privacy_review_required`

### `413 Payload Too Large`

Configured page-count or request-size limit exceeded.

Error code:

- `payload_too_large`

### `415 Unsupported Media Type`

A page is not an accepted PNG payload.

Error code:

- `unsupported_page_media_type`

### `422 Unprocessable Entity`

The uploaded redacted pages were processed, but the OCR/text gate blocks legal analysis.

Error codes:

- `ocr_quality_poor`
- `text_unusable`

The response should include safe OCR quality summaries and page reshoot hints when available, but not raw OCR text.

### `502 Bad Gateway`

External AI returned an unusable or malformed response.

Error code:

- `upstream_invalid_response`

Do not expose raw provider responses to the mobile client.

### `503 Service Unavailable`

External AI is temporarily unavailable, rate-limited, or network access failed.

Error codes:

- `upstream_unavailable`
- `upstream_rate_limited`

Do not expose provider credentials, SDK exception dumps, request payloads, or contract snippets.

## 7. Error envelope

All controlled API errors should use one envelope:

```json
{
  "request_id": "opaque-server-id",
  "status": "error",
  "error": {
    "code": "ocr_quality_poor",
    "message_ru": "Качество распознавания слишком низкое для надёжного анализа.",
    "details": {
      "pages": []
    }
  }
}
```

`message_ru` is user-facing. `code` is stable and drives mobile UI behavior. `details` must never contain raw image bytes, raw OCR text, API keys, provider stack traces, or unredacted contract fragments.

## 8. Out of scope for the first slice

Do not add yet:

- user accounts;
- authentication architecture;
- payment flow;
- contract history;
- cloud storage of source pages;
- asynchronous job queues;
- polling endpoints;
- WebSocket progress streaming;
- resumable uploads;
- report sharing;
- Contract Graph API;
- vector retrieval API;
- public API versioning beyond the `/v1/` path.

These may be added only after the privacy-boundary vertical slice works on a real Android device.

## 9. First implementation sequence

1. define request/response Pydantic models for non-file fields and response envelopes;
2. create a minimal FastAPI app with `POST /v1/contracts/analyze-redacted`;
3. wire uploaded redacted pages to the OCR adapter;
4. wire OCR output to `process_ocr_text(...)`;
5. wire validated redacted text to `run_contract_analysis(...)`;
6. add API contract tests using fake OCR/analysis adapters;
7. prove by network inspection that the mobile client sends only redacted PNG pages;
8. only then connect the React Native client.

## 10. Acceptance criteria

The first backend bridge is acceptable when all of the following are true:

- a redacted PNG page can travel from a test client to the endpoint;
- no API field exists for raw photos;
- the Gemini key remains server-side;
- poor OCR blocks final analysis with a controlled response;
- unusable text blocks final analysis with a controlled response;
- successful analysis returns the existing validated report schema;
- raw OCR is not returned in the normal API response;
- logs and error responses contain no image bytes, contract text, OCR text, or API keys;
- the same service layer remains usable by Streamlit and by the API adapter.
