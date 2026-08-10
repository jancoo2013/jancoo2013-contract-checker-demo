# OCR Project State & Continuity v0

Последнее обновление: 2026-08-10, PR #212, `android-geometry-angle-estimator-v1`.

Активный трек: `android-geometry-validation`.

Следующий bounded-шаг после merge PR #212: `android-geometry-full-frame-deskew-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления privacy/OCR-проекта. Архитектурные документы задают обязательные границы, но текущий `next_step_id` выбирается только state-файлами.

## 0. Изменение PR #212 — Android angle-estimator layer

После PR #211 Android validation path имеет локальный bounded grayscale preview. PR #212 добавляет только следующий слой анализа этого preview:

```text
module-owned grayscale preview <= 1800 px
→ validate exact local cache contract
→ bounded local text/ink evidence
→ nearest-neighbor analysis mask <= 900 px
→ fixed projection search from -12° to +12°, step 1°
→ dominant text angle + deskew rotation + confidence
→ accepted/rejected decision + rejection reasons
```

Границы PR #212:

- input только `preview.png`, созданный модулем PR #211 в app cache;
- произвольный внешний file/content URI в angle API не принимается;
- preview long side <= 1800 px и preview pixels <= 1800×1800;
- analysis mask long side <= 900 px;
- search range строго `[-12°, +12°]`, шаг `1°`;
- thresholds/reasons согласованы с frozen Python angle contract;
- Android local-background step использует bounded separable box-background approximation и не заявляет pixel-identical Gaussian parity с Python research reference;
- результат value-free: только angle/confidence/decision/reasons и scalar evidence;
- нет physical rotation;
- нет crop;
- нет UI;
- нет OCR/Tesseract;
- нет network/backend/upload;
- нет новых dependencies/permissions/workflows;
- frozen Python geometry implementation не меняется.

Реальное поведение angle estimator на Samsung A55 этим PR не считается доказанным. Оно проверяется только после добавления physical full-frame deskew и dev validation UI.

## 1. Frozen Python document geometry block

Binding freeze contract:

`docs/DOCUMENT_GEOMETRY_FREEZE_CRITERIA_V1.md`

Frozen geometry code baseline:

`7fe4bc88df2427ea90442f7b074c3cfe4e0de33a` — merge PR #209.

Frozen reference pipeline:

```text
source PIL image
→ bounded source size/mode/resource validation
→ EXIF orientation handling
→ bounded grayscale preview
→ local-contrast text/ink mask
→ bounded text-angle estimate
→ bounded content-region estimate
→ meaningful disconnected-content and deskew edge-loss guards
→ accepted-stage structural validation
→ full-resolution deskew + conservative crop only when fully trusted
→ otherwise full-frame fallback
→ DocumentGeometryNormalizationResult
```

Relevant corrective history:

- #203 / #206: wide and compact/fragmented disconnected-content fail-safes;
- #204 / #207: accepted-stage structural contract validation;
- #205 / #208: bounded resource accounting and supported-mode alignment;
- #209: meaningful source-edge deskew clipping fail-safe;
- #210: finite freeze/reopen contract.

The code-level freeze remains valid while Android validation proceeds. Android/product evidence reopens the frozen Python block only if it satisfies the explicit reopen criteria in `DOCUMENT_GEOMETRY_FREEZE_CRITERIA_V1.md`.

## 2. Android geometry validation sequence

The phone validation implementation is intentionally split before coding each layer.

### Completed

`android-geometry-preview-contract-v1` — PR #211

- local bounded decode;
- EXIF normalization;
- exact <=1800 px grayscale preview;
- no geometry decision.

`android-geometry-angle-estimator-v1` — PR #212

- consumes only the bounded module-owned preview;
- creates bounded text/ink evidence;
- performs fixed ±12° projection search;
- returns angle/confidence/decision/reasons;
- no physical transform.

### Next

`android-geometry-full-frame-deskew-v1`

Apply only a validated `accepted` deskew angle to the local full-resolution image. Preserve the full frame; do not crop. Keep source/resource bounds and EXIF coordinate/sign behavior explicit. Do not add UI/network/OCR.

### Then

`android-geometry-validation-ui-v1`

Small dev UI only:

- choose one local photo;
- show source;
- show full-frame deskew result;
- show angle/confidence/decision/reasons;
- no upload, OCR or persistence beyond bounded app cache.

### Manual gate

Run the final validation APK on the Samsung A55 using real locally held photos. At minimum inspect:

- near-zero skew;
- approximately ±3°;
- approximately ±7°;
- approximately ±10°;
- text close to edges;
- header/footer/page number;
- sparse/signature-like page;
- two-column/asymmetric content where relevant.

Success standard:

- accepted deskew visibly improves alignment without obvious meaningful-content loss;
- uncertain/rejected cases preserve the full frame;
- no photo leaves the device during this validation path;
- concrete product failure is recorded rather than hidden by threshold tuning.

The manual validation result must be recorded before the project returns to serverless OCR work.

## 3. Deferred next product block — `serverless-gpu-ocr-viability-benchmark-v1`

The serverless benchmark remains approved but is temporarily deferred until the Android geometry validation gate above is completed.

When resumed, the benchmark must:

1. use one OCR candidate through a model-neutral worker contract;
2. use only synthetic, public or owner-controlled redacted repository test material;
3. measure Hebrew text/layout quality, cold start, warm execution, queue delay, multi-page latency, GPU/VRAM, OOM behavior, billed seconds and estimated cost;
4. verify absence of raw page content/raw OCR text in logs and retained metadata;
5. preserve scale-to-zero and bounded queue execution;
6. not add production Android upload, production encryption/key management, production PII masks, Gemini/legal-analysis calls, permanent storage or real-user-data claims.

Surya remains the first benchmark candidate, not a production commitment.

## 4. Active target pipeline

```text
raw phone photos
→ client-side capture-quality checks and geometry normalization
→ encryption
→ bounded asynchronous serverless job
→ GPU worker decrypts in volatile memory
→ full-page Hebrew OCR and layout extraction
→ server-side PII detection and irreversible image/text redaction
→ privacy validation
→ anonymized derivative and evidence blocks
→ approved LLM legal-risk analysis
→ Russian report
→ deletion of raw and transient job material
→ optional persistent storage of sanitized final report under exact account authorization
```

Tesseract full-page OCR on Samsung A55 remains NO-GO and cannot return as active fallback.

## 5. Review and merge policy

GitHub Actions are best-effort diagnostics and are not the normal merge gate.

Every PR requires before Ready/merge recommendation:

1. focused validation on the exact final branch version when applicable;
2. assistant final-diff self-audit for scope/state/raw data/credentials/generated files;
3. mandatory `SECURITY.md` review with exactly one `Security review: PASS` or blocking verdict;
4. explicit product-owner merge decision.

Individual Codex review is not required per PR. Codex is used for bounded periodic/targeted audits.

## 6. Privacy and security boundary

Restricted raw/transient material may exist only on the user device, encrypted transport, approved encrypted short-lived job storage when needed, volatile authorized worker memory and bounded transient worker files when unavoidable and automatically deleted.

Original images, raw OCR and PII-bearing payload may enter only explicitly approved infrastructure physically located in Israel. Any unapproved endpoint or region must fail closed before upload/job creation; automatic fallback outside Israel is prohibited.

Raw images/raw OCR are prohibited in Gemini, general OCR/LLM APIs, logs, analytics, crash reports, GitHub, CI, Airtable and unrelated services. Only sanitized derivatives may proceed to legal analysis.

The Android geometry validation sequence is stricter: selected real photos remain local to the device. It adds no network destination and must not log/export page contents.

Production remains blocked until consent, authentication, authorization, key lifecycle, Israel-only provider behavior, retention/deletion, log scrubbing, cleanup, backup lifecycle, legal review, abuse controls and incident response are implemented and verified.

## 7. Recovery/work rules

Before a new privacy/OCR branch:

1. read current binding sources from `main`, including `SECURITY.md`;
2. check overlapping open PRs;
3. publish one exact Context Gate v1 before implementation;
4. implement only the declared bounded step;
5. update both state files after the actual PR number exists;
6. run final validation on the exact final head SHA;
7. perform final-diff self-audit and mandatory security review;
8. do not merge without explicit owner decision.

Do not use the abandoned experimental Android geometry branch as implementation input. Each Android validation layer starts from merged `main` and the immediately preceding bounded contract only.

Last full repository cold-start audit: PR #177 after merge PR #176.

Last focused Python geometry audit: Codex at `876e49bceb0136af6ee851a2656aaf689d72e545`; concrete source-edge blocker corrected by PR #209; finite stop/freeze criteria formalized by PR #210.

Frozen Python geometry code baseline: `7fe4bc88df2427ea90442f7b074c3cfe4e0de33a`.

Current PR: #212 `android-geometry-angle-estimator-v1`.

Next step after merge PR #212: `android-geometry-full-frame-deskew-v1`.
