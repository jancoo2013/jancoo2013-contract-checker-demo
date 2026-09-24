# OCR Project State & Continuity v0

Последнее обновление: 2026-09-23, PR #293, `expert-memory-contract-001-statutory-crosschecks-v1` (одобренное владельцем исследовательское исключение после слитого #292).

Активный трек: `expert-memory-development`.

Канонический следующий bounded-шаг: `expert-memory-contract-001-source-family-verification-v1`.

Решение владельца от 2026-09-22: реальные анализы договоров и повторные full-contract прогоны временно приостановлены до создания и независимой проверки качественной базы экспертных знаний. Разрешены локальные синтетические/обезличенные fixture-тесты без внешнего API. PR #281 добавляет экспериментальный Expert Pack v0.1: CORE_PROTOCOL, MECHANISM_PLAYBOOK и 15 синтетических контрастных примеров; эти материалы не являются верифицированной юридической базой. Сохранён уже слитый PR #282 и все его требования контроля Codex. Область OCR, privacy/security, runtime и провайдеров не изменена.

PR #293 — добавлены три датированные, пока НЕ верифицированные специалистом контрпроверки закона для уже обезличенного `contract_001`: настоящее право продления против нового согласия арендодателя (§25יב); обычный, срочный и чрезвычайный ремонт с ограничениями широкого отказа от претензий (§§8–9, 25ח); денежный предел гарантий против общих условий реализации/уведомления/возврата обеспечения (§25י). Поправка о дополнительных лицензированных гарантиях вступает в силу только 30.09.2026. В новой исследовательской карте сохранены точные цитаты, ошибки, даты, исключения §25טו, неопределённость источников и запрет на Gold/training. Исходные PDF не обрабатывались, production и текущая очередь задач не менялись.

PR #292 — второй критический проход по уже обезличенному печатному `contract_001`: пятнадцать взаимосвязанных механизмов с 55 короткими дословными опорами и отдельная проверка последовательности `8.א` → `9.א`. Добавлены опись/возврат вещей (§§3, 9, 12, 14), срок уведомления по арноне от даты подписания (§§3, 5, 6) и совместное чтение общего запрета на проживающих со специальным §24. Ранний выезд (§8), задержка освобождения (§17) и реализация обеспечительного чека (§11) разведены; зачет ремонта (§9б) ограничен неисправностями в ответственности арендодателя, обращением арендатора и неисполнением в разумный срок. Отсутствие `8.ב` не восполняется и может быть особенностью бланка. Это направленная владельцем корректировка, но НЕ юридически проверенный Gold и НЕ обучающие/контрольные метки; семейство оригинала всё еще UNKNOWN, а все ограничения приватности и заморозки внешних моделей остаются.

PR #291 — восемь локально предоставленных PDF проверены без OCR и внешних сервисов: семь разных byte-групп и одна дополнительная точная копия. Подтверждены четыре обезличенных семейства: TF_A объединяет RC01/RC04 как разные захваты одного исполненного договора; TF_B объединяет RC02/RC03/RC05 как редакции одного печатного шаблона; RC06 и RC07 образуют отдельные singleton-семейства TF_C и TF_D. Development закреплён за TF_A/TF_B, независимый test зарезервирован за TF_C/TF_D; все экземпляры одного шаблона остаются в одном cohort. `contract_001` выбран для следующего глубокого экспертного разбора, но его положительное соответствие частной RC-группе остаётся UNKNOWN, поэтому training/cohort use заблокирован до приватного сопоставления. Оригиналы двух прежних обезличенных исследований также остались UNKNOWN. Имена, ID, хеши, страницы, OCR и текст оригиналов не опубликованы.

PR #290 — карта покрытия тринадцати механизмов составлена по уже сохранённым обезличенным исследованиям двух договоров и трёхстраничному Golden Fixture. В десяти семействах у Golden Fixture есть проверяемые номера печатных пунктов; три остальных не установлены в этом обезличенном тексте — это НЕ свидетельство отсутствия в оригиналах. Добавлены семь вопросов на перекрёстное чтение взаимосвязанных пунктов и запреты на поспешные выводы. На момент #290 ни один материал ещё не был соотнесён с анонимной PDF-группой. Юридический Gold, новые реальные анализы через внешние модели, OCR, база данных и runtime не затронуты.

PR #289 — по решению владельца выполнен первый небольшой этап инвентаризации наших реальных договоров. В доступной личной Library обнаружены 14 PDF-записей семи вероятных групп; восемь оригиналов удалось проверить локально по байтам — семь различных и одна идентичная копия. Совпадения других имён/размеров ещё не гарантируют тождество содержания. В GitHub добавлены исключительно обезличенные ID, число страниц и наличие цифрового текстового слоя; оригиналы, названия с персональными сведениями, идентификаторы Library и хеши остаются вне репозитория. Соответствие семи PDF уже имеющемуся Golden Fixture и матрице двух обезличенных договоров ещё не подтверждено. Реальные договоры через внешние модели не прогонялись.

PR #288 — одобренное владельцем исключение из очереди задач: собраны пять различных судебных дел по обеспечительным чекам, с номером дела, датой, ссылкой на доступный текст/индекс, степенью доступности, краткими выводами и возможными ошибками модели (гипотезами, не наблюдёнными сбоями). Два решения вынесены после реформы аренды 2017 года, три — до неё. Оригиналы в судебном реестре и сведения об обжаловании не подтверждены; по одному делу итог не виден в открытом фрагменте. Никакие кейсы не стали юридически проверенными, ни один не подключён к обучению, evaluation или runtime. Полный текст процедуры службы взыскания 2025 года остаётся отдельным неразрешённым вопросом. Заморозка реальных договоров сохраняется.

PR #287 — редакция процедуры взыскания от 29.06.2025 принята как предварительная база по официально индексированным фрагментам. Полный PDF не получен; точная дата подтверждена только именем файла, актуальность и специальные положения для чек-битахон ещё не проверены. Реальные договоры по-прежнему заморожены.

PR #286 — принятую поправку № 3 к §25י сохранили отдельным версионированным источником с точным указанием §24 и §37, а дату вступления оставили реквизитом первоисточника, без отдельного временного предохранителя или запрета связей с ExpertCase. Пакет содержит семь источников, девять ограниченных утверждений и пять неизменённых синтетических кейсов. Источник не включён в runtime и не считается экспертно верифицированным; подлинные байты PDF с сервера Кнессета ещё не сверены с прочитанной репродукцией. Реальные договоры и внешние модели по-прежнему заморожены.

PR #285 — небольшой пакет первоисточников для Expert Memory: шесть официальных источников/указателей с указанием реально прочитанного уровня (исходный закон 2017 года, каталог текущей редакции, явно не действующее само по себе предложение 2026 года, процедура взыскания и два сервиса службы исполнения), восемь строго ограниченных утверждений, ссылки на все пять синтетических ExpertCase и четыре открытых вопроса. Только текст исторической публикации 2017 года непосредственно прочитан полностью по затронутым разделам; индексы других материалов и каталог не считаются проверкой действующего законодательства. Добавлены локальные проверки происхождения, запрета необоснованного статуса экспертной верификации и целостности ссылок в существующий CI. Реальные договоры и внешние модели по-прежнему заморожены.

PR #283 — локальный ExpertCase v1: фиксированная схема, проверка подлинности синтетического источника, механизма и ссылок, пять экспериментальных случаев и регрессионные тесты. Три связанных случая broad realization находятся только в train, два отдельных multi-instrument — только в evaluation. Это внутренний синтетический набор, а не независимый юридический Gold Set; ExpertCase не подключён к runtime или провайдерам. Правило остановки анализов реальных договоров не изменено.

PR #284 — слитое CI-only исключение от 2026-09-22: офлайн-проверки Smart Analysis Corpus и ExpertCase через GitHub Actions, без реальных договоров, провайдеров и новых зависимостей. PR #283 включает это изменение из актуального main; его собственные Python-тесты выполняются в CI отдельно от bootstrap-проверок #284. Трек и запрет реальных анализов не изменены.

PR #282 — governance-only exception: `AGENTS.md` уточняет контроль объёма задач Codex, сохранность тестов и обязательную проверку итогового diff. Активный трек, следующий шаг, код и границы приватности не изменены.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления. Binding architecture/security/privacy documents остаются выше по приоритету; `active_track` и `next_step_id` выбираются state-файлами.

## 1. Provider baseline

Corrective chain #266 → #268 → #269 завершена и слита: bounded retry/routing, fail-closed parsing/schema validation, response-size bounds, run-scoped unavailable-model memory, attempt ledger, redaction/report integrity и terminal lifecycle.

Local provider experiment v6 на 10 synthetic/sanitized security cases дал `705.02s`, `8/10` completed, 14 provider attempts; 3.6 succeeded on 8 cases, 3.5 succeeded on 0/4 fallback attempts. PR #270 added 3.7 for experimental Flash routing while excluding 3.8.

Current real-contract automatic route after PR #279 is bounded rather than an infinite cycle:

```text
gemini-3.6-flash
→ on controlled failure: try gemini-3.7-flash
→ then gemini-3.5-flash
→ daily quota: mark that model unavailable for the current run
→ temporary/unknown 429 with provider Retry-After/retryDelay <= 60s: one bounded retry
→ missing retry timing or provider delay > 60s: stop instead of guessing/waiting
→ retryable provider/network failure: at most one short 5-second retry
→ malformed/schema-invalid model output: no full-cycle retry loop
```

For contract analysis the google-genai SDK-owned HTTP retry loop is disabled (`attempts=1`), so one runner attempt maps to one provider request. The user does not select a model. Routing remains reactive failover based on actual request outcomes, not a server-load percentage API. Authentication/configuration failures remain terminal.

## 2. Real-contract runner and privacy boundary

PR #271 is merged and provides `run_single_contract_analysis.cmd` for one local PDF at a time.

Current flow:

```text
choose exactly one PDF
→ local text-layer extraction
→ remove identity-heavy preamble/header and signature tail
→ redact recurring header-derived party names
→ existing deterministic PII redaction
→ residual-PII + contract-usability gate
→ bounded automatic Gemini Flash routing
→ guarded local structured JSON report
```

Real PDF originals remain local and are never committed. The persisted report does not contain the source filename or raw/sanitized contract text. Image-only/scanned PDFs remain fail-closed and require a future explicitly approved OCR/privacy path. PR #274 does not reopen OCR.

## 3. First real full-contract run

The March–August 2025 text-layer lease was run successfully after PR #271:

- `gemini-3.6-flash` completed on the first attempt;
- provider elapsed time: `35.334s`;
- document quality returned `usable=true`, `completeness=high`;
- local sanitization had already passed the reviewed privacy smoke before the provider call.

The model correctly located many major mechanisms: rent/term, replacement-tenant early exit, security instruments, utilities, repairs, landlord access, holdover sanction, broad fundamental-breach wording and set-off restriction.

The same run exposed important report-control defects:

- the 20,000 NIS security cheque was recognized, but its realization mechanics were underweighted versus amount/market-comparison prose;
- broad fundamental-breach wording was not fully reconciled with the contract's specific 7-day cure for rent arrears;
- AS-IS remained a warning despite related landlord repair/hidden-defect protections;
- the useful 21-day pre-return inspection / 10-day defect-correction procedure was underemphasized while the holdover sanction was surfaced;
- `missing_clauses` drifted into a wishlist such as renewal option/building insurance;
- the model invented unsupported market norms and numeric remediation examples such as 2–3 months, 14 days, 48 hours, and 2,000–3,000 NIS.

Conclusion: the model is useful as a semantic reader, but the final report needs deterministic Question Engine inventory, second-pass cross-clause resolution, materiality/suppression, statutory gating and remediation gating.

## 4. PR #272 corrective scope

PR #272 wires the already-existing deterministic core inventories into the whole-contract model prompt instead of asking the model to choose its own review agenda. The review inventory covers security/enforcement, early exit/replacement tenant, financial sanctions/overlap, condition/AS-IS/defects/repairs, termination/cure/notice, and option/renewal.

Prompt guardrails require:

- a second pass before retaining red/yellow findings;
- complete per-instrument security mechanics, including notice/cure and return;
- reconciliation of broad breach definitions with specific cure rules;
- reconciliation of AS-IS with repair, hidden-defect and ordinary-wear provisions;
- combined analysis of handover protocol, correction period and holdover sanction;
- literal set-off wording to remain separate from statutory effect;
- no unsupported market-practice claims or invented numeric limits/deadlines;
- absence of an optional/wishlist clause not to become a risk automatically.

Until dedicated deterministic/statutory/remediation layers are wired into this local real-contract path, the persisted report additionally suppresses model-owned `proposed_changes`, generic `missing_clauses`, per-risk rewrite requests, and market-comparison prose. Source-grounded clause analysis, risks, questions, unclear fragments and financial facts remain.

Provider route, PII gate, PDF scope, dependencies, permissions and network destinations were unchanged by PR #272.

## 5. Failed same-contract rerun and PR #273 correction

After PR #272 merged, the same March–August 2025 contract was launched again. The runner attempted the configured Flash route once and then stopped with:

```text
All configured Gemini Flash models failed for this contract
```

That behavior did not match the product-owner requirement. PR #273 changed only retry orchestration in the local real-contract runner:

- retryable `GeminiRateLimitError` and `GeminiResponseError` outcomes move to the next model;
- after 3.6, 3.7 and 3.5 have all failed, the runner waits 30 seconds and starts again at 3.6;
- cycles continue until one model returns a valid `ContractAuditResult` or the user stops with Ctrl+C;
- authentication/configuration failures remain terminal;
- console status shows only cycle number, model, safe error class and elapsed seconds;
- the attempt ledger records the cycle for every attempt and is persisted only if a model eventually succeeds;
- no raw provider exception body, API key or contract text is printed.

Prompt, output guardrails, privacy boundary, OCR scope, model list, dependencies, permissions, endpoint set and network destinations were unchanged.

## 6. Successful post-#273 rerun and remaining defects

The same reviewed contract later completed after cyclic routing:

- cycles 1–3: all three configured Flash models returned retryable `GeminiResponseError` outcomes;
- cycle 4: `gemini-3.6-flash` completed successfully in `36.599s`;
- total attempts: `10`;
- no raw contract material from this run is committed.

The #272 guardrails materially improved the semantic result:

- AS-IS was read together with landlord repair/hidden-defect protections and remained `normal`;
- the 21-day pre-return inspection, 10-day correction window and double-daily holdover mechanism were read together;
- invented market comparisons and numeric rewrite suggestions disappeared;
- generic `missing_clauses` and `proposed_changes` were absent;
- the 20,000 NIS security cheque was recognized as having incomplete realization mechanics rather than being treated mainly as a large amount.

Two important gaps remained:

1. the 20,000 NIS security-cheque mechanism produced only a subset of the required questions; completion authority, realization grounds/amount basis, cure details and the cheque-specific return mechanism were not all forced into explicit output;
2. the broad fundamental-breach finding still did not fully reconcile the contract's specific 7-day rent cure/notice mechanics, despite the prompt-only second-pass instruction.

Conclusion: a prompt-only internal inventory is insufficient because a model can silently skip an inventory item or one of its required fields while still returning a schema-valid legacy audit.

## 7. PR #274 explicit Question Engine answer coverage

PR #274 converts the core inventory from an internal checklist into a mandatory structured extraction layer.

Each provider result must now include `question_engine_answers` with:

- exactly one object for every core `question_id`;
- one controlled status: `FOUND`, `NOT_FOUND`, `AMBIGUOUS`, `HANDWRITING_DEPENDENCY`, or `CLAUSE_PRESENT_VALUE_BLANK`;
- a compact positional `values` list whose length and order exactly match that question's declared `answer_fields`;
- source `evidence_block_ids` for non-`NOT_FOUND` answers.

Python validates the extraction before the provider result is accepted. It rejects:

- missing core question IDs;
- duplicate or unknown question IDs;
- the wrong number of positional values;
- `NOT_FOUND` paired with non-null extracted values;
- non-`NOT_FOUND` answers without evidence;
- evidence block IDs that do not exist in the sanitized source evidence set;
- a `FOUND` answer that contains no actual value.

A rejected extraction becomes the existing controlled `GeminiResponseError`, so the provider route can move to the next model without exposing contract text or provider exception bodies.

This PR does not yet make the legacy narrative report a full deterministic `FindingResolution` renderer. Its bounded purpose is to ensure the semantic extraction layer cannot silently omit core Question Engine questions or answer fields. The explicit answers are persisted in the local sanitized report and become the input for later deterministic resolution/materiality logic.

### 7.1 PR #275 local runner warning cleanup

PR #275 is a product-owner-authorized bounded corrective exception while the same-contract rerun remains the canonical next step. It changes only the local CLI's console hygiene:

- replace deprecated `fitz` compatibility import with `pymupdf` in the runner and its focused PDF test;
- raise the known Streamlit bare-mode logger and the intended Google GenAI AFC advisory logger to `ERROR`;
- keep runner retry status, controlled Gemini errors, authentication/configuration failures and other Python warnings/errors visible.

A fresh downloaded `main` showed that only the PyMuPDF warning was actually removed. Streamlit still reinitialized its warning logger after the pre-import assignment, and the Google GenAI logger name used in #275 was incorrect.

### 7.2 PR #276 warning cleanup correction

PR #276 corrects those two concrete causes without changing analysis behavior:

- import Streamlit before applying CLI-only logging thresholds, then set both the `streamlit` parent logger and the specific `streamlit.runtime.scriptrunner_utils.script_run_context` logger to `ERROR`;
- target the actual google-genai logger name `google_genai.models` for the AFC advisory instead of the incorrect `google.genai.models` name;
- keep all runner cycle/status output and controlled failures unchanged.

Provider routing, retry timing, Question Engine schema/prompt/validation, privacy boundary, OCR path, report payload, dependency set, permission set, workflows, endpoint set and network destinations are unchanged.

### 7.3 PR #278 rate-limit cycle backoff

During the post-#274 same-contract rerun, repeated cycles showed that most attempts were failing almost immediately with `GeminiRateLimitError` rather than spending time on model generation. Repeating the same three-model cycle every 30 seconds therefore became counterproductive quota-gate hammering.

PR #278 kept the existing model order and retryable-failure routing but introduced a fixed 300-second delay after a full rate-limit cycle. Follow-up discussion identified that this did not solve the actual problem: when provider request quotas are the limiting resource, changing the delay alone does not bound the number of requests or distinguish daily exhaustion from temporary throttling.

Provider list, Question Engine schema/prompt/validation, privacy boundary, OCR path, report payload, dependencies, permissions, workflows, endpoints and network destinations were unchanged.

### 7.4 PR #279 quota-aware bounded retry

PR #279 replaces the fixed 300-second cooldown and the infinite retry cycle with request-count-aware bounded routing.

Key behavior:

- contract-analysis calls disable google-genai SDK-owned automatic HTTP retries, so one runner attempt maps to one provider request rather than one visible attempt hiding several SDK retries;
- a structured `QuotaFailure` indicating a per-day quota marks only that model unavailable for the current run and it is not retried;
- provider `Retry-After` or `google.rpc.RetryInfo.retryDelay` is used only for one automatic retry and only when the requested delay is at most 60 seconds;
- a 429 without reliable retry timing stops instead of inventing a cooldown;
- a provider delay above 60 seconds stops instead of making the user wait several minutes;
- retryable 5xx/network failures receive at most one short 5-second retry;
- malformed JSON, schema/Question-Engine coverage failures and other non-provider response errors may fall through to the next configured model, but do not start another full cycle;
- authentication/configuration failures remain terminal.

The attempt ledger stores only safe error class plus safe quota scope/retry timing. Raw provider exception bodies, API keys and contract text remain excluded from logs and reports.

This PR does not add another provider, model, dependency, endpoint, permission, workflow or storage path. It does not change Question Engine semantics/schema, the privacy boundary, report payload contract or OCR scope.

## 8. Canonical next step — private source and family verification

`next_step_id = expert-memory-contract-001-source-family-verification-v1`

**Freeze remains:** no new full real-contract external-LLM/OCR/provider calls. No raw private originals, recoverable PII, signed names/IDs, page images, original source names or hashes in GitHub, CI, logs or RAG. Only the already-sanitized three-page printed `contract_001` is available for this step.

**PR #292 delivered:** a second, owner-directed critical pass containing **15** cross-clause mechanisms backed by **55** exact short Hebrew quotes from the sanitized printed source, plus a clause-sequence integrity check. It adds the unverified property inventory, the signature-date trigger for arnona notice, and the special agreed-occupant term; separates early exit, post-term holdover and security realization; and narrows repair set-off to all three written preconditions. `8.ב` is not reconstructed. This research is not an observation of a model failure, an original-court holding or reviewed legal Gold.

**Unresolved:** the original behind the three-page sanitized Golden Fixture is not positively mapped to a private RC group or template family (RC07 alone is excluded as a direct source). The product owner has not verified its full printed transcription. Appendix B, handwritten fields and signatures were excluded from the source record, so their original contents and any amendments are not known. Existing TF_A/TF_B development and TF_C/TF_D reserved independent-test families from #291 remain unchanged; the unlinked Golden Fixture is NOT eligible for training or cohort scoring.

**PR #293 — bounded research exception:** three dated source-scoped and unverified statute-crosscheck hypotheses now cover actual tenant option versus renewed consent (§25יב), regular/urgent/emergency repair and undisclosed defects (§§8–9, 25ח), and financially burdensome security caps versus general realization/notice/return for an ordinary cheque (§25י). The 2026 licensed-provider amendment is future-effective only from 2026-09-30. No legal Gold or production authorization follows from this research.

**Next bounded step:** `expert-memory-contract-001-source-family-verification-v1`. In a separately approved private/local workflow, verify the sanitized transcription and the `8.א` → `9.א` sequence against the source, and try to map the fixture to a confirmed template family without publishing names, IDs, hashes or source text. If the source family remains unknown, keep training/evaluation blocked. Subsequent expert-case generation and legal-source verification are separate tasks.

**Parallel unverified research:** original and appellate checks for the five court decisions; full/current 2025 Enforcement Authority cheque procedure. They cannot be promoted merely because this contract analysis mentions a related mechanism.

**Out of scope:** original PDF upload to repository, provider/model tests on the real contract, new OCR/RAG/database, runtime behavior, legal enforceability verdicts or automatically using this first pass as model Gold.

## 9. Frozen runtime Question Engine architecture

```text
privacy-validated sanitized contract material
→ analysis-completeness / document-type gate
→ deterministic smart core question inventory
→ explicit LLM structured answers for every core question_id
→ Python question/field/evidence coverage validation
→ deterministic conditional follow-ups
→ cross-clause interaction checks
→ bounded novel-issue catch-all
→ Python/schema/evidence/consistency validation
→ statutory comparison where applicable
→ FindingResolution: CONFIRMED / NARROWED / CLEARED
→ materiality / suppression
→ Safe Output
```

Core invariants: handwriting is never guessed; different security instruments remain distinct; missing/blank dependencies are explicit; candidate finding is not final finding; user-facing output does not issue sign/don't-sign advice, court predictions, or categorical enforceability claims without a separately approved deterministic rule.

## 10. Stable recovery anchors

Current smart CORE families: security/enforcement, early exit/replacement tenant, financial sanctions/overlap, condition/AS-IS/defects/damage evidence, termination/cure/notice, option/renewal. Corpus oracle v2 remains an evaluation representation, not production runtime schema.

Statutory anchor: 2017 residential-rental reform effective `2017-09-17`; maintained baseline includes 2026 amendment timing for section `25י`; when freshness/applicability is insufficient, runtime degrades to contract-only analysis.

Frozen OCR anchor: Surya/cloud OCR remains frozen research; Tesseract full-page Hebrew OCR on the target phone remains `NO-GO`; Android geometry/preprocessing work remains deferred unless explicitly reopened.

Last completed Question Engine batch audit marker: 2026-09-08, start `cbbb8e0905c1fda8610260d4046b51952a9f636c`, end `ee66e0063e270abd5eb7992f2be73c89dbec3a5d`, principal PR range `#234–#250`, outcome `CORRECTIVE PR REQUIRED`. Provider audit after #265 is separate and its bounded corrective chain is complete.

## 11. Recovery/work rules

Before a new PR read from current base: `AGENTS.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md`, `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`, both state files, `docs/DOCUMENT_STATUS_INDEX.md`, and `docs/CODEX_WORKFLOW.md`.

Every PR: exactly one Context Gate v1; both state files updated; final checks apply to the exact final head; actual paths exactly match the Context Gate; mandatory final-diff security review; auto-merge disabled.
