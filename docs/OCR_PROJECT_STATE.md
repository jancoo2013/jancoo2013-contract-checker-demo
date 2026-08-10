# OCR Project State & Continuity v0

Последнее обновление: 2026-08-10, PR #209, `ocr-deskew-source-edge-content-failsafe-v1`.

Активный трек: `serverless-gpu-ocr`.

Следующий bounded-шаг после merge PR #209: `ocr-document-geometry-freeze-criteria-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Только он вместе с `docs/OCR_PROJECT_STATE.json` выбирает текущий `next_step_id`; архитектурные документы задают границы и обязательные будущие gates, но не выбирают следующий PR самостоятельно.

## 0. Изменение PR #209

Третий focused Codex audit document geometry block выполнен на `main` SHA:

`876e49bceb0136af6ee851a2656aaf689d72e545` — merge PR #208.

Outcome: `FREEZE AFFECTED AREA`.

Из нового отчёта принят как конкретный product-relevant blocker один дефект: при ненулевом deskew исходный foreground у края страницы может исчезнуть во время preview rotation с `expand=False` ещё до existing crop-safety checks. Аудит воспроизвёл это на source-corner annotation порядка 40×40 px; physical rotation затем повторял потерю.

PR #209 исправляет только этот defect:

- для ненулевого accepted deskew content-region stage выполняет ту же bounded NEAREST preview rotation с `expand=False` и `expand=True`;
- сравнивается retained foreground count;
- если bounded rotation теряет как минимум уже существующий meaningful compact-foreground threshold, добавляется rejection reason `source_edge_content_clipped_by_deskew`;
- crop acceptance блокируется;
- existing `rotation_only` contract приводит physical transform к полному исходному кадру без частичного rotation/crop;
- обычный central skewed document без edge loss остаётся crop-eligible;
- micro-content thresholds не уменьшаются и не переопределяются;
- accepted-stage forged-dataclass semantics не расширяются в этом PR.

Аудит также сообщил два класса adversarial cases, которые **не становятся автоматически следующими implementation PR**:

1. sub-threshold micro-content (`1×8`, `2×8`, `4×4` и аналогичные marks) ниже/на границе текущего meaningful-content heuristic;
2. вручную forged internal stage objects с комбинациями metrics, которые штатные producers не создают.

До отдельного определения stop/freeze contract эти cases считаются предметом product/engineering threshold decision, а не автоматически blocking implementation backlog.

Geometry block остаётся frozen до следующего шага `ocr-document-geometry-freeze-criteria-v1`.

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

### Третий focused re-audit

Audit endpoint:

`876e49bceb0136af6ee851a2656aaf689d72e545` — merge PR #208.

Outcome: `FREEZE AFFECTED AREA`.

Reverification:

- resource accounting: audit verdict `FIXED`;
- admitted PIL mode alignment: audit verdict `FIXED`;
- existing disconnected-content guard: audit found residual sub-threshold micro-content cases;
- accepted-stage validation: audit found additional manually forged internal-state combinations;
- **new concrete blocker:** source-edge content may be clipped by `expand=False` deskew before crop-safety evaluation.

Decision after review of the audit:

- source-edge clipping is accepted as a real product-relevant defect and corrected by PR #209;
- arbitrarily shrinking micro-content probes and producer-impossible forged stage states will not automatically move the freeze gate after every audit;
- before another corrective or adversarial audit, the project must define an explicit freeze/stop contract.

## 2. Первый блок — document geometry normalization

Текущий contract после PR #209:

```text
source PIL image
→ validate bounded source dimensions/mode/phase-aware accounted memory
→ EXIF orientation inside preview/transform contracts
→ local-contrast text/ink mask
→ bounded dominant text-angle estimate
→ bounded content-region decision
→ for nonzero deskew, detect meaningful foreground clipped by bounded preview rotation
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
| Content-region bounds/decision | Offline Python reference, PR #196; wide disconnected corrective PR #203; compact/fragmented corrective PR #206; source-edge deskew-loss guard PR #209 |
| Physical deskew/crop application | Offline Python reference, PR #200; accepted-contract corrective PR #204; shared resource guard PR #205; accepted-contract v2 PR #207; shared preview contract PR #208 |
| End-to-end geometry normalizer | Offline Python integration, PR #202; source-edge full-frame regression coverage PR #209 |

Не входят в этот block и не должны добавляться до его explicit freeze decision:

- illumination/shadow normalization;
- glare/blur/capture-quality gates;
- perspective correction;
- Android camera/runtime integration;
- OCR execution;
- PII redaction;
- provider/serverless job implementation;
- Gemini/LLM integration;
- report persistence.

## 3. Следующий шаг — `ocr-document-geometry-freeze-criteria-v1`

После merge PR #209 **не запускать ещё один open-ended adversarial audit и не начинать новый implementation corrective автоматически**.

Следующий шаг должен зафиксировать bounded code-level freeze contract для geometry block:

1. определить minimum meaningful-content contract: какой foreground считается потенциально значимым документным содержанием, а какой остаётся допустимым шумом/артефактом;
2. определить producer/consumer trust boundary для внутренних dataclasses: какие structural invariants consumer обязан валидировать, а какие producer-impossible metric combinations не являются отдельным blocking surface;
3. определить конечный regression set для code-level freeze: two-column, disconnected header/footer, compact meaningful mark, source-edge deskew clipping, EXIF/coordinate mapping, accepted-stage structural contradictions, resource/mode bounds;
4. запретить moving-goalpost аудит, где размер adversarial mark бесконечно уменьшается после каждого исправления;
5. после фиксации criteria отдельно решить: нужен ли ещё один bounded corrective или текущий geometry block можно frozen/закрыть.

Это decision/contract step. Он не разрешает illumination/shadow, OCR, PII, Android, provider/serverless или соседние implementation направления сам по себе.

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

Serverless GPU OCR viability benchmark remains a required future gate. It is not part of the frozen geometry corrective/freeze-decision sequence.

## 5. Review and merge policy

GitHub Actions остаются best-effort diagnostics и не входят в blocking contour.

Каждый PR требует до Ready/merge recommendation:

1. focused tests на exact final branch version, когда применимо;
2. assistant self-audit scope/diff/state/credentials/raw-data/generated-files;
3. mandatory final-diff security review по `SECURITY.md` с `Security review: PASS`;
4. явное решение владельца продукта о merge.

Individual Codex review перед каждым PR не требуется. Codex используется для целевых/batch audits с заранее ограниченным contract.

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

Последний focused geometry audit: Codex at `876e49bceb0136af6ee851a2656aaf689d72e545`, outcome `FREEZE AFFECTED AREA`.

Следующий step после merge PR #209: `ocr-document-geometry-freeze-criteria-v1`.
