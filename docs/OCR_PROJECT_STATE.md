# OCR Project State & Continuity v0

Последнее обновление: 2026-08-05, PR #190, `serverless-gpu-ocr-architecture-v1`.

Активный трек: `serverless-gpu-ocr`.

Единственный следующий шаг: `serverless-gpu-ocr-viability-benchmark-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Архитектуру задают `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md` и `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`. `docs/VISUAL_PII_LOCALIZATION_V1.md` сохраняет paused local-only alternative. Evidence/masking contract задаёт `docs/PII_EVIDENCE_DETECTOR_V1.md`; машиночитаемое состояние хранится в `docs/OCR_PROJECT_STATE.json`.

## 0. Изменение PR #190

- Владелец продукта явно выбрал encrypted on-demand serverless GPU OCR вместо активной local-only visual localization разработки.
- Former absolute rule `raw photos never leave the device` superseded for this consent-based mode.
- Raw contract pages могут входить только в один approved serverless worker boundary после explicit user consent.
- Worker decrypts input in volatile memory; architecture не является local, zero-access или zero-knowledge processing.
- Raw images и raw OCR запрещены в Gemini, general OCR/LLM APIs, logs, analytics, crash reports, GitHub, CI, Airtable и unrelated services.
- Worker обязан создать sanitized image/text derivative до legal-analysis handoff.
- Raw input, transient plaintext, job keys, temporary files и raw OCR должны удаляться после success или terminal failure согласно verified provider/runtime behavior.
- Для первого benchmark отдельный VPS, Redis, RabbitMQ, MinIO, PostgreSQL и permanent GPU не нужны.
- Surya выбран первым benchmark candidate, но не production dependency.
- `visual-pii-synthetic-baseline-v1` снят с active next step; local visual track сохранён как paused research/fallback.
- PR документационный: worker, credentials, uploads, dependencies, real contracts и Gemini calls не добавлены.

## 1. Активная целевая цепочка

```text
raw phone photos
→ client-side normalization and encryption
→ bounded asynchronous serverless job
→ GPU worker decrypts in volatile memory
→ full-page Hebrew OCR and layout extraction
→ server-side PII detection and irreversible image/text redaction
→ privacy validation
→ anonymized derivative and evidence blocks
→ approved LLM legal-risk analysis
→ Russian report
→ deletion of raw and transient job material
```

Tesseract full-page OCR on Samsung A55 remains NO-GO and cannot return as active fallback.

## 2. Privacy boundary

Raw material may exist only in:

- user device;
- encrypted transport;
- encrypted short-lived job storage when needed;
- volatile authorized worker memory;
- bounded transient worker files only when unavoidable and automatically deleted.

Production remains blocked until separate steps define and verify:

- explicit consent and plain-language disclosure;
- authentication and authorization;
- per-job key lifecycle;
- provider and data-region policy;
- retention and deletion behavior;
- log scrubbing;
- cleanup after success/failure/timeout/cancellation;
- processor terms, privacy policy, and legal review;
- incident response.

Only sanitized derivatives may proceed to Gemini or another legal-analysis model.

## 3. Preserved and paused components

| Component | Status |
|---|---|
| PII classes and evidence contract | Preserved for server-side sanitization |
| Direct-value validators/checksums | Preserved as deterministic evidence |
| `auto_mask / local_review / keep` | Preserved |
| Geometry gates and irreversible mask rules | Preserved |
| Android Tesseract full-page OCR | NO-GO; historical diagnostic only |
| Local visual PII detector | Paused research/fallback |
| Production serverless worker | Not implemented |
| Production encryption/key management | Not implemented |
| Server-side PII sanitizer | Not implemented |
| Privacy validator | Not implemented |
| Legal-analysis handoff | Existing text prototype only; no raw-image integration |

## 4. Cost and latency assumptions

Serverless cost includes:

1. container/model cold start;
2. execution;
3. idle timeout before scale-down;
4. storage/transfer where applicable;
5. failures and retries.

Therefore `model throughput` does not equal end-to-end contract latency or per-contract cost.

Current provider pricing and Surya benchmarks are planning inputs only. The repository must not claim that one contract is processed in fractions of a second until single-job cold and warm measurements exist.

## 5. Единственный следующий шаг

**`serverless-gpu-ocr-viability-benchmark-v1`**.

Bounded scope:

1. one model-neutral serverless-compatible benchmark worker around one OCR candidate;
2. Surya as first candidate unless a blocking license/runtime issue is found before implementation;
3. only synthetic, public, or owner-controlled redacted pages in repository automation;
4. one fixed multi-page Hebrew contract-like packet;
5. output text, reading order, line/block geometry, latency, VRAM, and estimated billed cost;
6. separate cold-start, queue-delay, and warm-execution measurements;
7. inspect logs/results for raw page content and raw OCR leakage;
8. no Android upload, production encryption, real user contracts, production masks, Gemini call, permanent storage, or custom VPS queue.

Provisional go/no-go gate:

- materially usable Hebrew output on held-out contract-like pages;
- stable line/block geometry;
- one ten-page job completes without OOM on an economically acceptable GPU class;
- warm compute cost below `$0.10` per ten-page contract;
- cold and warm latency measured rather than inferred;
- no raw content in logs or retained benchmark metadata;
- licensing and provider retention explicitly verified or recorded unresolved.

These are research gates, not production privacy, accuracy, latency, or cost guarantees.

## 6. Deferred infrastructure

Do not build before the benchmark:

- always-on GPU instances;
- custom VPS API/queue;
- Redis/RabbitMQ;
- MinIO/PostgreSQL/permanent document store;
- production authentication and key mediation;
- consent UI and privacy-policy implementation;
- production PII sanitization;
- billing;
- Gemini/legal-analysis integration.

## 7. Правила восстановления и работы

Перед новой privacy/OCR веткой:

1. прочитать all binding sources с актуального `main`;
2. проверить отсутствие overlapping open PRs;
3. опубликовать exact Context Gate v1;
4. менять только declared paths и approved bounded step;
5. открыть draft PR, затем обновить оба state-файла фактическим номером;
6. выполнить focused tests/benchmarks на exact final head SHA;
7. проверить diff, state continuity, generated files, credentials, raw data и auto-merge;
8. не merge без явного решения владельца продукта.

Последний полный cold-start audit: PR #177 после merge PR #176.
