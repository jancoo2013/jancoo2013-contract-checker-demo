# OCR Project State & Continuity v0

Последнее обновление: 2026-08-06, PR #201, `security-policy-mandatory-review-v1`.

Активный трек: `serverless-gpu-ocr`.

Следующий bounded-шаг после merge PR #201: `ocr-illumination-shadow-normalization-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Подробная история сохраняется в Git history и описаниях PR.

## 0. Изменение PR #201

- Добавлен корневой `SECURITY.md` как binding security policy для каждой ветки и каждого PR.
- Разделены два класса данных:
  - raw/transient material — исходные страницы, raw OCR, PII-bearing payloads, ключи и временные артефакты; они подлежат bounded zero-retention после завершения или terminal failure;
  - persistable sanitized material — финальные отчёты и sanitized evidence, которые могут храниться для пользователя только при account-scoped authorization, encryption, deletion и defined backup lifecycle.
- Зафиксирован Israel-only fail-closed gate: restricted material разрешено отправлять только на явно allowlisted инфраструктуру физически в Израиле; автоматический fallback, retry или replication в другой регион запрещены.
- Добавлена обязательная final-diff security review для каждого PR, выполняемая в обычном per-PR контуре orchestrating assistant.
- Отдельный Codex review больше не является обязательным условием Ready или merge.
- Codex используется для пакетного аудита накопленных merged-изменений примерно два раза в неделю либо по прямому запросу владельца продукта.
- PR template требует `Security impact`, проверенные области, findings, unverified runtime/provider behavior и ровно один итоговый verdict: `Security review: PASS` или `Security review: BLOCKING FINDINGS`.
- `AGENTS.md` и `docs/CODEX_WORKFLOW.md` делают `SECURITY.md` binding source, запрещают Ready/merge recommendation при blocking security finding и определяют periodic Codex batch audit.
- README кратко поясняет актуальную serverless privacy/security-границу, хранение финальных обезличенных отчётов и отсутствие per-PR Codex gate.
- Runtime, зависимости, network destinations, OCR, Gemini, Android, storage implementation и provider configuration не изменены.
- Documentation-only validation: все семь Context Gate paths существуют и изменены; Markdown/JSON state синхронизированы; `active_track` и `next_step_id` сохранены; application tests не запускались как неприменимые к process/documentation-only diff.
- Runtime/provider claims остаются непроверенными: Israel physical region, provider retention/deletion, cleanup, report authorization, encryption, backup expiry и incident response должны быть реализованы и проверены до production.

### Предыдущее изменение PR #200

- Добавлен offline Python reference-компонент физического deskew/crop полного изображения.
- Входы — `TextAngleEstimate` из PR #195 и `ContentRegionBounds` из PR #196.
- Поворот и crop применяются только при одновременных `angle.accepted` и `bounds.accepted`.
- `rotation_only`, отклонённый угол и `full_frame_fallback` сохраняют полный EXIF-нормализованный кадр без геометрических изменений.
- Preview bounds отображаются в координаты полного разрешения консервативно: `floor` для левой/верхней границы и `ceil` для правой/нижней.
- Проверяются совпадение углов, coordinate space, preview size, границы crop и существующий лимит исходника 150 млн пикселей.
- Противоречивый или повреждённый upstream-контракт вызывает явную ошибку вместо небезопасного transform.
- Focused suite перед созданием PR: 8/8; `py_compile`: PASS.
- Runtime приложения, Android, OCR engine, provider integration, upload, encryption, PII, Gemini и storage не подключены.

## 1. Активная целевая цепочка

```text
raw phone photos
→ client-side capture-quality checks and normalization
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

## 2. Реализованные preprocessing reference-компоненты

| Component | Status |
|---|---|
| Local-contrast text mask | Offline Python reference, PR #194 |
| Bounded text-angle estimator | Offline Python reference, PR #195 |
| Content-region bounds/decision | Offline Python reference, PR #196 |
| Physical deskew/crop application | Offline Python reference, PR #200 |
| Perspective correction | Not implemented in active runtime path |
| Illumination/shadow normalization | Next bounded step |
| Glare/blur quality gates | Not implemented |
| Android realtime capture analyzer | Not implemented |
| Surya quality/geometry oracle | Synthetic oracle implemented, PR #191 |
| Actual Surya GPU/provider viability result | Not measured |

## 3. Review and merge policy

GitHub Actions remain enabled but are no longer part of the blocking contour:

- `validate-context` stays non-required;
- queued, delayed, missing or cancelled runs are best-effort diagnostics;
- an Actions result does not replace per-PR audit or security review.

Every implementation, documentation, test, process, and state PR requires before merge:

1. focused local tests on the exact final branch version when applicable;
2. assistant self-audit of scope, diff, state continuity, credentials, raw data and generated files;
3. a mandatory final-diff security review under `SECURITY.md` with `Security review: PASS`;
4. explicit product-owner merge approval.

An individual Codex review is not required before Ready or merge.

Codex batch-audit policy:

- audit accumulated merged work approximately twice per week or when explicitly requested by the product owner;
- inspect the range since the previous completed audit;
- look for cross-PR integration defects, security/privacy regressions, stale tests, unsupported claims and contract drift;
- pending batch audit does not block ordinary PR merges;
- only a concrete finding or explicit owner freeze blocks the affected work.

## 4. Privacy and security boundary

Restricted raw/transient material may exist only in:

- user device;
- encrypted transport;
- approved encrypted short-lived job storage when needed;
- volatile authorized worker memory;
- bounded transient worker files only when unavoidable and automatically deleted.

Original images, raw OCR and any PII-bearing payload may enter only explicitly approved infrastructure physically located in Israel. Any unapproved endpoint or region must fail closed before upload or job creation. Automatic fallback, retry, replication or disaster-recovery routing outside Israel is prohibited for restricted material.

Raw images and raw OCR remain prohibited in Gemini, general OCR/LLM APIs, logs, analytics, crash reports, GitHub, CI, Airtable and unrelated services. Only sanitized derivatives may proceed to legal analysis.

Final reports are not zero-retention objects. The product may retain all final reports for the authenticated user only when they contain sanitized analysis/evidence and no original images, raw OCR, recoverable PII, secrets or reversible hidden layers. Persistent report operations require exact account-scoped authorization, encryption, user deletion, account deletion, retention and backup-expiry behavior.

Production remains blocked until consent, authentication, report authorization, key lifecycle, approved Israel-only provider behavior, retention/deletion, log scrubbing, cleanup, backup lifecycle, legal review, abuse controls and incident response are separately implemented and verified.

## 5. Следующий шаг — `ocr-illumination-shadow-normalization-v1`

Следующий PR должен добавить только bounded offline reference-нормализацию неравномерного освещения и мягких теней. Он не должен:

- выполнять OCR;
- подключать Android runtime или камеру;
- вызывать внешнего provider;
- отправлять или сохранять изображения;
- менять PII, Gemini, encryption, production storage или security policy.

После него:

```text
glare/blur/capture-quality gates
→ Android realtime capture analyzer
→ controlled real-photo preprocessing validation
→ Surya/provider benchmark
```

## 6. Правила восстановления и работы

Перед новой privacy/OCR веткой:

1. прочитать binding sources с актуального `main`, включая `SECURITY.md`;
2. проверить отсутствие overlapping open PRs;
3. опубликовать exact Context Gate v1;
4. менять только declared paths и approved bounded step;
5. обновить оба state-файла фактическим номером PR;
6. выполнить focused validation на exact final head SHA;
7. провести assistant self-audit и отдельный `Security review: PASS`;
8. не merge без явного решения владельца продукта.

Последний полный cold-start audit: PR #177 после merge PR #176.

Последний periodic Codex batch audit: ещё не проводился после принятия новой cadence-политики PR #201.
