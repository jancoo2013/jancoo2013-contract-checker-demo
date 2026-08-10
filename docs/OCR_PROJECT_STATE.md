# OCR Project State & Continuity v0

Последнее обновление: 2026-08-09, PR #206, `ocr-disconnected-compact-content-failsafe-v2`.

Активный трек: `serverless-gpu-ocr`.

Следующий bounded-шаг после merge PR #206: `ocr-accepted-stage-contract-validation-v2`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Только он вместе с `docs/OCR_PROJECT_STATE.json` выбирает текущий `next_step_id`; архитектурные документы задают границы и обязательные будущие gates, но не выбирают следующий PR самостоятельно.

## 0. Изменение PR #206

PR #206 — первый bounded corrective после второго focused Codex re-audit document geometry block.

Повторный аудит показал, что PR #203 закрыл исходные wide disconnected-content cases, но accepted crop всё ещё мог удалить очень короткий или fragmented legitimate content вне dominant crop: например compact page-number-like marks шириной 12/18/22 px и разделённые короткие marks.

Изменение PR #206:

- существующий wide disconnected-line guard PR #203 сохраняется;
- добавлен bounded compact-foreground guard для содержимого вне padded crop candidate;
- compact evidence группируется по близким активным строкам и total foreground, поэтому больше не требует непрерывного horizontal run шириной минимум 2.5% страницы;
- compact/fragmented outside content добавляет `disconnected_content_outside_crop`;
- decision становится `rotation_only`, а существующий physical-transform contract сохраняет полный кадр;
- long narrow vertical artifact остаётся отдельным exemption, чтобы прежний side-noise case не запрещал безопасный crop;
- synthetic coverage включает compact footer widths 4/12/18/22 px, fragmented separated marks и +7° skew;
- crop heuristic вне этого fail-safe, accepted-stage contract validation, resource accounting, OCR, PII, Android, provider/serverless и другие subsystem boundaries не меняются.

Geometry block остаётся frozen. PR #206 не закрывает остальные findings второго re-audit.

## 1. Focused geometry audits — current status

### Первый focused audit

Audit endpoint:

`6b30b0a66ccebf8efac49b1b368039ca453519cc` — merge PR #202.

Outcome: `FREEZE AFFECTED AREA`.

Исходные findings:

1. **BLOCKING — disconnected legitimate content could be cropped away.**
   - Wide/two-column variant corrected by PR #203.
2. **CORRECTIVE — contradictory manually constructed `accepted` stage contracts could authorize physical crop.**
   - Initial contract checks added by PR #204.
3. **CORRECTIVE — inherited 150M source-pixel limit did not prove a practical full-resolution memory budget.**
   - Initial resource contract added by PR #205.

### Второй focused re-audit

Audit endpoint:

`2126f510f9f178e74c9b487693a99af4ef7d42f1` — merge PR #205.

Outcome: `FREEZE AFFECTED AREA`.

Повторный audit подтвердил, что исходные large examples стали безопаснее, но нашёл четыре concrete remaining findings:

1. **BLOCKING — compact or fragmented disconnected legitimate content can still be cropped away.**
   - Corrective: PR #206 `ocr-disconnected-compact-content-failsafe-v2`.
2. **BLOCKING — accepted-stage validation still permits impossible crop authorization.**
   - Accepted `±12°` can pass transform validation although the real estimator rejects search-limit candidates.
   - Accepted bounds can carry empty/unrelated `line_bands` that do not justify the candidate crop.
   - Следующий bounded corrective: `ocr-accepted-stage-contract-validation-v2`.
3. **CORRECTIVE — geometry peak accounting is not yet a conservative upper bound for preview analysis.**
   - Preview grayscale/background/NumPy working buffers are not fully represented by the current accounting formula.
   - Separate later corrective required.
4. **CORRECTIVE — resource-supported `LAB` mode is not aligned with the current physical transform conversion capability.**
   - `LAB` passes the resource allowlist but accepted physical transform later cannot convert it to RGB using the current Pillow path.
   - Separate later corrective required; may be combined with the remaining resource-accounting corrective if scope remains bounded.

Ни один finding не считается окончательно закрытым для geometry freeze только на основании self-review. После всех bounded correctives весь document geometry block должен снова пройти targeted Codex re-audit. Только `BATCH AUDIT CLEAR` разрешает снять freeze.

## 2. Первый блок — document geometry normalization

Текущий contract:

```text
source PIL image
→ validate bounded source dimensions/mode/accounted memory
→ EXIF orientation inside preview/transform contracts
→ local-contrast text/ink mask
→ bounded dominant text-angle estimate
→ bounded content-region decision
→ reject wide/compact/fragmented meaningful content outside proposed crop
→ validate accepted stage-contract consistency
→ full-resolution deskew + conservative crop only when fully accepted
→ otherwise full-frame fail-safe
→ DocumentGeometryNormalizationResult
```

Компоненты:

| Component | Status |
|---|---|
| Geometry resource budget | Offline Python reference, PR #205; second audit found remaining preview-accounting/mode-alignment gaps |
| Local-contrast text mask | Offline Python reference, PR #194; shared resource guard PR #205 |
| Bounded text-angle estimator | Offline Python reference, PR #195 |
| Content-region bounds/decision | Offline Python reference, PR #196; wide disconnected-content corrective PR #203; compact/fragmented corrective PR #206 |
| Physical deskew/crop application | Offline Python reference, PR #200; accepted-contract corrective PR #204; shared resource guard PR #205 |
| End-to-end geometry normalizer | Offline Python integration, PR #202 |

Не входят в этот block и не должны добавляться до его clean re-audit:

- illumination/shadow normalization;
- glare/blur/capture-quality gates;
- perspective correction;
- Android camera/runtime integration;
- OCR execution;
- PII redaction;
- provider/serverless job implementation;
- Gemini/LLM integration;
- report persistence.

## 3. Следующий шаг — `ocr-accepted-stage-contract-validation-v2`

После merge PR #206 разрешён только следующий bounded corrective из второго Codex re-audit.

Цель: закрыть remaining accepted-stage contract gaps без изменения content-region heuristic или resource accounting:

- accepted angle должен быть strictly inside estimator search boundary, поэтому `±12°` не может авторизовать physical crop;
- accepted content-region contract должен содержать достаточное и валидное line evidence;
- candidate bounds должны соответствовать supplied accepted line evidence, а не быть произвольным box;
- impossible/malformed accepted objects должны reject до physical transformation.

Не включать в этот PR preview-memory accounting, LAB mode alignment, новый preprocessing, OCR, Android, PII или provider/serverless work.

После contract-validation v2 остаются отдельные resource/mode correctives из второго audit, затем требуется ещё один targeted geometry re-audit.

## 4. Активная целевая цепочка продукта

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
→ optional persistent storage of the sanitized final report under exact account authorization
```

Tesseract full-page OCR on Samsung A55 remains NO-GO and cannot return as active fallback.

Serverless GPU OCR viability benchmark remains a required future gate. It is not part of the frozen geometry corrective/re-audit sequence.

## 5. Review and merge policy

GitHub Actions остаются best-effort diagnostics и не входят в blocking contour.

Каждый PR требует до Ready/merge recommendation:

1. focused tests на exact final branch version, когда применимо;
2. assistant self-audit scope/diff/state/credentials/raw-data/generated-files;
3. mandatory final-diff security review по `SECURITY.md` с `Security review: PASS`;
4. явное решение владельца продукта о merge.

Individual Codex review перед каждым PR не требуется. Codex используется для целевых/batch audits.

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

Последний focused geometry audit: Codex at `2126f510f9f178e74c9b487693a99af4ef7d42f1`, outcome `FREEZE AFFECTED AREA`.
