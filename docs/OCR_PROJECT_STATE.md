# OCR Project State & Continuity v0

Последнее обновление: 2026-08-10, PR #210, `ocr-document-geometry-freeze-criteria-v1`.

Активный трек: `serverless-gpu-ocr`.

Следующий bounded-шаг после merge PR #210: `serverless-gpu-ocr-viability-benchmark-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Только он вместе с `docs/OCR_PROJECT_STATE.json` выбирает текущий `next_step_id`; архитектурные документы задают границы и обязательные будущие gates, но не выбирают следующий PR самостоятельно.

## 0. Изменение PR #210 — code-level freeze первого geometry block

PR #210 не меняет geometry-код. Он добавляет binding component contract:

`docs/DOCUMENT_GEOMETRY_FREEZE_CRITERIA_V1.md`

Документ фиксирует конечные правила code-level freeze после трёх focused Codex audits и corrective PR #203–#209.

Frozen geometry code baseline:

`7fe4bc88df2427ea90442f7b074c3cfe4e0de33a` — merge PR #209.

Freeze contract определяет:

1. **Minimum meaningful-content boundary.** Geometry не обязана считать каждый foreground pixel юридически значимым содержимым. Blocker возникает для line-like/compact/source-edge evidence, которое удовлетворяет текущим bounded meaningful-content rules. Arbitrarily shrinking synthetic marks ниже этого contract не двигают freeze gate автоматически.
2. **Producer/consumer trust boundary.** `TextAngleEstimate` и `ContentRegionBounds` сейчас являются internal in-process contracts, а не внешним serialized/untrusted API. Physical transform обязан валидировать structural invariants, которые влияют на mutation/coordinates, но не обязан дублировать producer semantic scoring только ради forged metric combinations, которые штатный producer не создаёт.
3. **Finite regression set.** Freeze основывается на конечном наборе normal-operation, fail-safe, structural, EXIF/coordinate и resource/mode cases, а не на open-ended поиске всё меньших adversarial thresholds.
4. **Explicit reopen criteria.** Geometry открывается снова только по конкретному in-contract defect: потеря meaningful content, producer-reachable unsafe accepted state, resource/mode violation, EXIF/coordinate defect, real-photo evidence систематического threshold miss, изменение trust boundary/dependency или изменение frozen implementation.
5. **Audit stop rule.** Новый finding actionable только если нарушает freeze contract; запрос “продолжать придумывать всё меньшие edge cases” сам по себе не создаёт corrective backlog.

### Freeze decision

По существующим evidence текущий block удовлетворяет этому finite contract:

- после PR #209 focused geometry suite: 65/65 PASS;
- третий audit отдельно признал phase-aware resource accounting `FIXED`;
- тот же audit признал admitted PIL mode alignment `FIXED`;
- corrective PR #203/#206 закрыли wide и meaningful compact/fragmented disconnected-content loss;
- PR #204/#207 закрыли structural accepted-stage contradictions, которые относятся к mutation contract;
- PR #205/#208 закрыли resource/mode contract;
- PR #209 закрыл concrete source-edge deskew clipping defect, признанный product-relevant после третьего audit.

Оставшиеся в третьем audit sub-threshold micro-content examples (`1×8`, `2×8`, `4×4` и аналогичные) и producer-impossible forged semantic metrics **не требуют ещё одного implementation corrective до code-level freeze** по правилам `DOCUMENT_GEOMETRY_FREEZE_CRITERIA_V1.md`.

Итог: **document geometry normalization block code-level frozen at `7fe4bc88df2427ea90442f7b074c3cfe4e0de33a`.**

Это не production/real-photo certification. Real-photo/product validation остаётся отдельным будущим validation layer и может открыть block только через explicit reopen criteria.

## 1. Focused geometry audits — completed history

### Первый focused audit

Endpoint:

`6b30b0a66ccebf8efac49b1b368039ca453519cc` — merge PR #202.

Outcome: `FREEZE AFFECTED AREA`.

Findings:

1. disconnected legitimate content could be cropped away → wide/two-column corrective PR #203;
2. contradictory manually constructed accepted stage contracts could authorize crop → initial contract validation PR #204;
3. inherited 150M-pixel limit did not prove practical memory bound → initial resource contract PR #205.

### Второй focused audit

Endpoint:

`2126f510f9f178e74c9b487693a99af4ef7d42f1` — merge PR #205.

Outcome: `FREEZE AFFECTED AREA`.

Findings:

1. compact/fragmented meaningful disconnected content → PR #206;
2. accepted search-limit and line-evidence structural gaps → PR #207;
3. preview working-set accounting gap → PR #208;
4. `LAB` admitted-mode mismatch → PR #208.

### Третий focused audit

Endpoint:

`876e49bceb0136af6ee851a2656aaf689d72e545` — merge PR #208.

Outcome: `FREEZE AFFECTED AREA`.

Reverification:

- resource accounting: `FIXED`;
- admitted PIL mode alignment: `FIXED`;
- residual sub-threshold micro-content reported;
- additional manually forged internal semantic combinations reported;
- concrete new blocker: source-edge meaningful content could be clipped by `expand=False` deskew before safety evaluation.

Decision after review:

- source-edge clipping accepted as real product-relevant defect → PR #209;
- sub-threshold micro-content and producer-impossible semantic forgeries moved to explicit freeze-contract decision instead of automatic implementation backlog;
- PR #210 freezes the stop/reopen criteria and closes the open-ended audit loop.

## 2. Первый block — document geometry normalization

Frozen contract:

```text
source PIL image
→ validate bounded source dimensions/mode/phase-aware accounted memory
→ EXIF orientation inside preview/transform contracts
→ local-contrast text/ink mask
→ bounded dominant text-angle estimate
→ bounded content-region decision
→ detect meaningful source-edge foreground clipped by nonzero deskew
→ reject meaningful wide/compact/fragmented content outside proposed crop
→ validate accepted structural search-bound/line-evidence/candidate/safe-box invariants
→ full-resolution deskew + conservative crop only when fully accepted
→ otherwise full-frame fail-safe
→ DocumentGeometryNormalizationResult
```

Components:

| Component | Status |
|---|---|
| Geometry resource budget | Frozen reference; PR #205 + phase-aware/mode corrective PR #208 |
| Local-contrast text mask | Frozen reference; PR #194 + shared resource/preview contracts |
| Bounded text-angle estimator | Frozen reference; PR #195 |
| Content-region bounds/decision | Frozen reference; PR #196 + disconnected correctives #203/#206 + edge-loss guard #209 |
| Physical deskew/crop application | Frozen reference; PR #200 + accepted-contract correctives #204/#207 + resource contracts #205/#208 |
| End-to-end geometry normalizer | Frozen integration; PR #202 + regressions through PR #209 |
| Freeze/stop contract | `docs/DOCUMENT_GEOMETRY_FREEZE_CRITERIA_V1.md`, PR #210 |

Не входят в frozen block:

- illumination/shadow normalization;
- glare/blur/capture-quality gates;
- perspective correction;
- Android camera/runtime integration;
- OCR execution;
- PII redaction;
- provider/serverless job implementation;
- Gemini/LLM integration;
- report persistence.

## 3. Следующий шаг — `serverless-gpu-ocr-viability-benchmark-v1`

После merge PR #210 первый geometry block закрыт на code level и дальнейшая его доработка не является текущим направлением.

Возвращаемся к ранее утверждённому active track: bounded viability benchmark serverless GPU OCR.

Benchmark должен:

1. использовать один OCR candidate через model-neutral worker contract;
2. использовать только synthetic, public или owner-controlled redacted test material;
3. измерить Hebrew text/layout quality, cold start, warm execution, queue delay, total multi-page latency, GPU/VRAM, OOM behavior, billed seconds и estimated cost;
4. подтвердить отсутствие raw page content/raw OCR text в logs и retained result metadata;
5. сохранить scale-to-zero/bounded queue execution;
6. не делать production Android upload, production encryption/key management, PII production masks, Gemini/legal-analysis calls, permanent storage или real-user-data claims.

Target candidate остаётся Surya как первый benchmark candidate, а не production commitment.

## 4. Активная целевая цепочка продукта

```text
raw phone photos
→ client-side capture-quality checks and frozen geometry normalization
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

GitHub Actions остаются best-effort diagnostics и не входят в blocking contour.

Каждый PR требует до Ready/merge recommendation:

1. focused validation на exact final branch version, когда применимо;
2. assistant self-audit scope/diff/state/credentials/raw-data/generated-files;
3. mandatory final-diff security review по `SECURITY.md` с `Security review: PASS`;
4. явное решение владельца продукта о merge.

Individual Codex review перед каждым PR не требуется. Periodic/targeted Codex audit должен иметь заранее ограниченный contract. Frozen geometry reopens only through `docs/DOCUMENT_GEOMETRY_FREEZE_CRITERIA_V1.md`.

## 6. Privacy and security boundary

Restricted raw/transient material может существовать только в user device, encrypted transport, approved encrypted short-lived job storage when needed, volatile authorized worker memory и bounded transient worker files when unavoidable and automatically deleted.

Original images, raw OCR и PII-bearing payload могут входить только в явно approved infrastructure physically located in Israel. Любой неразрешённый endpoint/region должен fail closed до upload/job creation; automatic fallback/retry/replication outside Israel запрещены.

Raw images/raw OCR запрещены в Gemini, general OCR/LLM APIs, logs, analytics, crash reports, GitHub, CI, Airtable и unrelated services. Only sanitized derivatives may proceed to legal analysis.

Final reports не являются zero-retention objects. Persistent storage разрешён только для sanitized analysis/evidence без original images, raw OCR, recoverable PII, secrets или reversible hidden layers и только с exact account-scoped authorization, encryption, deletion и defined backup lifecycle.

Production остаётся blocked до реализации и проверки consent, authentication, report authorization, key lifecycle, approved Israel-only provider behavior, retention/deletion, log scrubbing, cleanup, backup lifecycle, legal review, abuse controls and incident response.

## 7. Правила восстановления и работы

Перед новой privacy/OCR веткой:

1. прочитать current binding sources с `main`, включая `SECURITY.md`;
2. проверить отсутствие overlapping open PRs;
3. опубликовать exact Context Gate v1;
4. менять только declared paths и approved bounded step/corrective;
5. обновить оба state-файла фактическим номером PR;
6. выполнить final validation на exact final head SHA;
7. провести assistant self-audit и отдельный `Security review: PASS`;
8. не merge без явного решения владельца продукта.

Последний полный repository cold-start audit: PR #177 после merge PR #176.

Последний focused geometry audit: Codex at `876e49bceb0136af6ee851a2656aaf689d72e545`, outcome `FREEZE AFFECTED AREA`; concrete source-edge blocker corrected by PR #209; stop/freeze decision formalized by PR #210.

Frozen geometry code baseline: `7fe4bc88df2427ea90442f7b074c3cfe4e0de33a`.

Следующий step после merge PR #210: `serverless-gpu-ocr-viability-benchmark-v1`.
