# OCR Project State & Continuity v0

Последнее обновление: 2026-08-10, PR #208, `ocr-geometry-resource-accounting-mode-alignment-v2`.

Активный трек: `serverless-gpu-ocr`.

Следующий bounded-шаг после merge PR #208: `ocr-document-geometry-block-reaudit-v2`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Только он вместе с `docs/OCR_PROJECT_STATE.json` выбирает текущий `next_step_id`; архитектурные документы задают границы и обязательные будущие gates, но не выбирают следующий PR самостоятельно.

## 0. Изменение PR #208

PR #208 — третий и последний bounded corrective после второго focused Codex re-audit document geometry block.

Повторный аудит после PR #205 оставил два resource-contract findings:

1. geometry peak accounting не был консервативным upper bound для preview-analysis phase, потому что не представлял одновременно живущие grayscale/background/NumPy working buffers и temporaries;
2. `LAB` проходил resource allowlist, хотя audited reference runtime не мог надёжно провести этот mode через текущий physical transform conversion path.

Изменение PR #208:

- сохранены существующие hard limits: `32_000_000` source pixels, `8192` maximum source long side и `384 MiB` accounted-memory ceiling;
- `PREVIEW_LONG_SIDE = 1800` перенесён в единый geometry resource contract и используется preview/transform consumers из одного источника;
- accounting разделён на explicit full-resolution transform phase и bounded preview-analysis phase;
- preview-analysis phase получает консервативный reserve `48 bytes` на preview pixel для одновременно живущих PIL/NumPy preview buffers, masks и scratch/headroom;
- transform phase дополнительно учитывает `2 bytes` на preview pixel для L preview + bool mask, которые top-level normalizer удерживает во время full-resolution transform;
- `accounted_peak_bytes` — максимум двух explicit phase estimates, а не только source-pixel formula;
- `LAB` исключён из admitted source modes и fail closed в initial resource guard до `ImageOps.exif_transpose`/conversion;
- другие разрешённые mode contracts и geometry heuristics не изменяются;
- OCR, PII, Android, illumination/shadow, perspective, provider/serverless, Gemini, upload, storage, network и dependencies не входят в PR.

Geometry block после merge PR #208 остаётся frozen. Никакой следующий implementation PR не разрешён до targeted re-audit.

## 1. Focused geometry audits — current status

### Первый focused audit

Audit endpoint:

`6b30b0a66ccebf8efac49b1b368039ca453519cc` — merge PR #202.

Outcome: `FREEZE AFFECTED AREA`.

Findings:

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

Findings и corrective status:

1. **BLOCKING — compact or fragmented disconnected legitimate content could still be cropped away.**
   - Addressed by PR #206 `ocr-disconnected-compact-content-failsafe-v2`.
2. **BLOCKING — accepted-stage validation still permitted impossible crop authorization.**
   - Search-limit `±12°`, line-evidence count/distinctness/bounds and candidate-union consistency addressed by PR #207 `ocr-accepted-stage-contract-validation-v2`.
3. **CORRECTIVE — geometry peak accounting was not a conservative upper bound for preview analysis.**
   - Addressed by PR #208 with explicit phase-aware preview working-set accounting.
4. **CORRECTIVE — resource-supported `LAB` mode was not aligned with current physical transform capability.**
   - Addressed by PR #208 by failing `LAB` closed in the initial resource contract.

Ни один finding не считается окончательно закрытым для geometry freeze только на основании self-review. Весь block должен снова пройти targeted Codex re-audit на актуальном `main` после merge PR #208. Только `BATCH AUDIT CLEAR` разрешает снять freeze.

## 2. Первый блок — document geometry normalization

Текущий contract:

```text
source PIL image
→ validate bounded source dimensions/mode/phase-aware accounted memory
→ EXIF orientation inside preview/transform contracts
→ local-contrast text/ink mask
→ bounded dominant text-angle estimate
→ bounded content-region decision
→ reject wide/compact/fragmented meaningful content outside proposed crop
→ validate accepted search-bound + line-evidence/candidate consistency
→ validate accepted confidence/reasons/sign/safe containment
→ full-resolution deskew + conservative crop only when fully accepted
→ otherwise full-frame fail-safe
→ DocumentGeometryNormalizationResult
```

Компоненты:

| Component | Status |
|---|---|
| Geometry resource budget | Offline Python reference, PR #205; phase-aware preview accounting + mode alignment PR #208 |
| Local-contrast text mask | Offline Python reference, PR #194; shared resource guard PR #205; shared preview contract PR #208 |
| Bounded text-angle estimator | Offline Python reference, PR #195 |
| Content-region bounds/decision | Offline Python reference, PR #196; wide disconnected corrective PR #203; compact/fragmented corrective PR #206 |
| Physical deskew/crop application | Offline Python reference, PR #200; accepted-contract corrective PR #204; shared resource guard PR #205; accepted-contract v2 PR #207; shared preview contract PR #208 |
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

## 3. Следующий шаг — `ocr-document-geometry-block-reaudit-v2`

После merge PR #208 разработка geometry/preprocessing снова останавливается.

Codex должен выполнить cold-start targeted re-audit **только document geometry block** на актуальном `main`, включая исходные implementation PRs #194, #195, #196, #200, #202 и corrective PRs #203–#208.

Re-audit должен заново проверить весь current block, а не только подтвердить PR #208. В частности:

- сохранение disconnected/compact/fragmented legitimate content;
- accepted-stage fail-closed contracts;
- coordinate/EXIF/rotation/crop consistency;
- phase-aware resource accounting и mode allowlist;
- отсутствие новых regressions от correctives;
- достаточность synthetic/adversarial tests для code-level freeze.

Допустимые outcomes:

- `BATCH AUDIT CLEAR` → geometry block можно frozen/закрыть и затем отдельно выбрать следующий product step;
- `CORRECTIVE PR REQUIRED` → исправлять только конкретные defects этого geometry block;
- `FREEZE AFFECTED AREA` → block остаётся frozen.

До результата re-audit не начинать illumination/shadow, OCR, PII, Android, provider/serverless или соседние направления.

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

Следующий audit: `ocr-document-geometry-block-reaudit-v2` после merge PR #208.
