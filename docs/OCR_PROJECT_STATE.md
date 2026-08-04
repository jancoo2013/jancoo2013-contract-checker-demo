# OCR Project State & Continuity v0

Последнее обновление: 2026-08-04, PR #179, `pii-direct-value-match-provenance-v1`.

Активный трек: `local-pii-redaction`.

Единственный следующий шаг: `pii-direct-value-match-provenance-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Архитектуру задают `docs/ARCHITECTURE.md` и `docs/CUSTOM_OCR_PIPELINE.md`; точные входы, выходы и proof boundaries отдельных компонентов задают их component contracts. При конфликте обязательных документов работа останавливается до отдельного исправления.

## 0. Изменение PR #179

- `adapt_direct_value_match_to_candidate` теперь требует caller-supplied local source text и до evidence/candidate construction повторно запускает `find_direct_value_matches`.
- Candidate создаётся только когда переданный `DirectValueMatch` в точности присутствует среди approved finder results: совпадают PII class, detector ID, start и end.
- Synthetic regressions подтверждают четыре approved direct classes и fail-closed rejection для forged but well-formed offsets, class и detector ID; malformed spans по-прежнему отклоняются structural gate.
- Source text, raw PII value и source offsets не сохраняются и не возвращаются в candidate/evidence output; pixel geometry по character offsets не выводится.
- Focused evidence suite проходит `106/106`, обязательный OCR workflow suite — `179/179`, полный repository suite — `451/451` в изолированной среде с repository-declared dependencies.
- Adapter остаётся reference-only. Detector orchestration, renderer, review pack, Android app/APK, runtime, OCR, pixel classifier, dependencies, external APIs, реальные данные и privacy boundary не изменены.
- По merge-gated workflow `next_step_id` намеренно остаётся `pii-direct-value-match-provenance-v1` до merge PR #179 и нового чтения resulting `main`; следующий detector integration slice в этом PR не выбирается.

### Изменение PR #178

- В `adapt_direct_value_match_to_candidate` добавлена fail-closed structural validation до evidence/candidate construction: `start` и `end` должны быть integer/non-boolean offsets и образовывать ordered non-negative non-empty span `0 <= start < end`.
- Synthetic regressions покрывают boolean, float, negative, empty и reversed spans; malformed `DirectValueMatch` теперь отклоняется исключением и не может получить candidate disposition `auto_mask`.
- Existing finder-produced matches, four approved direct classes, class-mismatched/unapproved detector handling, exact geometry, value-free output, determinism и defensive copies сохраняют прежнее поведение.
- Focused evidence suite проходит `106/106`, обязательный OCR workflow suite — `179/179`, полный repository suite — `451/451` в изолированной среде с repository-declared dependencies.
- Adapter остаётся reference-only. Detector orchestration, renderer, review pack, Android app/APK, runtime, OCR, pixel classifier, dependencies, external APIs, реальные данные и privacy boundary не изменены.
- Structural integrity не доказывает provenance: корректно оформленный вручную `DirectValueMatch` с approved-looking detector ID пока нельзя отличить от результата `find_direct_value_matches`. Следующий bounded step — `pii-direct-value-match-provenance-v1`.

### Audit PR #177 после merge PR #176

- Repository-only cold-start audit выполнен с точного `main` SHA `3f0d5453f256a0fd8e7cddb1c448a7bbbfb5a84f`; до изменения state подтверждены `active_track=local-pii-redaction`, `next_step_id=privacy-ocr-cold-start-audit-v1`, согласованность Markdown/JSON state и отсутствие open PR.
- Полностью сверены binding sources, `docs/CODEX_WORKFLOW.md`, `docs/PII_EVIDENCE_DETECTOR_V1.md`, evidence schema/combiner, direct/marker/visual evidence components и decision adapters, их tests и обязательный OCR workflow. Фактические entrypoints `pii_baseline.py`, `pii_mask_renderer.py`, `pii_review_pack_builder.py`, Android reviewer и Streamlit/manual redaction path проверены отдельно.
- GitHub metadata, Context Gate, changed paths, merge ancestry и final-head workflow evidence проверены для PR #173–#176. Head/merge SHA и successful `OCR research runtime` runs: #173 `3728d63abf43f97ff29d35876504b0961be91268` / `27b1bdb10ed761dc547ebe001e8de49a25b364d5` / run #92; #174 `58688d61ddce0335a8c53d7f6f3b035cddc00cce` / `2abede2b7c018935cd0fdd2dd60c3731b6f4f5f0` / run #95; #175 `59512fc68d1be2b17eab16c5ededb96b2a5b4857` / `3089673b39a8c5d75acd3a333370382684770817` / run #98; #176 `c90b664ca5e0429efefc2e5acda48a7eabafcff7` / `3f0d5453f256a0fd8e7cddb1c448a7bbbfb5a84f` / run #101. Каждый PR менял только declared Context Gate paths.
- Current-main validation: восемь evidence modules проходят `104/104`; полный обязательный OCR workflow suite проходит `177/177`; полный repository suite проходит `449/449` в изолированном `/tmp` environment с repository-declared FastAPI/API dependencies. Базовый Python ожидаемо останавливается только на пяти неизменённых API import errors из-за отсутствующего `fastapi`.
- Class binding, approved detector registries, fail-closed mismatched/unapproved semantics, exact strong-target geometry, value-free outputs и defensive copies подтверждены. Raw images, recoverable PII и unredacted OCR text остаются local; dependencies, external services и privacy boundary не изменены.
- Integration truth не изменилась: новые adapters импортируются только evidence modules и focused tests. Baseline по-прежнему выдаёт old-schema broad-zone `needs_review`; renderer принимает только `marker_layout_baseline_v0`; review-pack builder и Android reviewer используют legacy predictions/reason codes; runtime evidence chain не импортирует.
- **Blocking direct-match integrity defect:** `adapt_direct_value_match_to_candidate` проверяет dataclass type, candidate/evidence identifiers и pixel geometry, но полностью игнорирует `DirectValueMatch.start/end`. На текущем `main` synthetic records с offsets `(-5, -1)`, `(True, False)` и `(20, 10)` при approved phone class/detector и valid bbox каждый возвращают `auto_mask`. Такие records не могут быть результатом `find_direct_value_matches`; malformed source reference не должен авторизовать автоматическую маску.
- Marker-value adapter уже отклоняет negative, boolean, empty/reversed и mismatched source spans; visual adapter повторно валидирует kind/detector/bbox через recorder. Симметричных structural bypasses в этих двух adapters не найдено.
- Verdict: `BLOCKING DIRECT-MATCH INTEGRITY DEFECT`. Audit PR implementation не исправляет. Единственный следующий шаг — bounded synthetic correction `pii-direct-value-match-integrity-v1`; detector/renderer/runtime integration остаётся последующим blocker.
- Не доказано: real PII recall, complete mask coverage, bounded over-redaction, pixel classification handwriting/signatures/stamps, production privacy safety, Android automatic masking, external OCR handoff, cross-contract generalization и controlled human-pilot success.

### Изменение PR #176

- Добавлен dependency-free reference adapter `pii_visual_decision_adapter.py`, который соединяет один caller-prevalidated `VisualSensitiveRegion`, optional marker evidence, существующий visual relation helper и `combine_evidence_into_candidate` через один bounded API.
- `signature`, `initials` и `stamp` сохраняют закрытый visual class; `filled_field` и `handwriting` наследуют конкретный PII class только из approved marker detector. Missing, incompatible или unapproved marker semantics остаются `local_review` и не могут разрешить `auto_mask`.
- Adapter повторно проверяет frozen region через существующий recorder, поэтому вручную подделанные visual kind, detector ID, bbox или image bounds отклоняются до candidate decision. Exact region bbox используется одновременно как candidate и visual evidence geometry.
- Девять synthetic/non-identifying adapter tests вместе с семью существующими evidence modules проходят `104/104`; полный repository suite проходит `449/449` в изолированной среде с repository-declared dependencies.
- OCR workflow теперь явно запускает новый adapter test module. Pixels, text и images не читаются; baseline detector, renderer, review-pack builder, Android app/APK, runtime, OCR, pixel classifier, dependencies, external services, real contracts и privacy boundary не изменены.
- После четырёх implementation PR со времени audit #172 следующий bounded step — обязательный repository-only `privacy-ocr-cold-start-audit-v1`.

### Изменение PR #175

- Добавлен dependency-free reference adapter `pii_marker_value_decision_adapter.py`, который соединяет ровно один существующий `MarkerValueRelation`, его точный `DirectValueMatch`, существующие value-free evidence helpers и `combine_evidence_into_candidate` через один bounded API.
- Adapter проверяет, что relation действительно указывает на переданный direct match: совпадают PII class, direct detector ID и source offsets; отрицательные, булевы, перевёрнутые или несовпадающие spans отклоняются до построения candidate.
- Caller передаёт exact value/candidate geometry, optional marker geometry и image bounds; source offsets используются только для проверки связи и не сохраняются в candidate. Approved class-compatible chain получает `auto_mask`, а несовместимая или неподтверждённая семантика остаётся fail closed.
- Девять synthetic/non-identifying adapter tests вместе с шестью существующими evidence modules проходят `95/95`; полный repository suite проходит `440/440` в изолированной среде с repository-declared API dependencies.
- OCR workflow теперь явно запускает новый adapter test module. Baseline detector, renderer, review-pack builder, Android app/APK, runtime, OCR, pixel classifier, dependencies, external services, real contracts и privacy boundary не изменены.
- `active_track` остаётся `local-pii-redaction`; следующий bounded integration step — `pii-visual-decision-adapter-v0`.

### Изменение PR #174

- Добавлен dependency-free reference adapter `pii_direct_value_decision_adapter.py`, который соединяет ровно один существующий `DirectValueMatch`, `make_direct_value_evidence` и `combine_evidence_into_candidate` через один bounded API.
- Candidate `proposed_class` берётся из `DirectValueMatch`, а одна caller-supplied exact geometry передаётся одновременно как candidate geometry и direct-value evidence geometry; approved class-compatible match получает `auto_mask` через существующий combiner.
- Class-mismatched или unapproved detector semantics fail closed до schema-valid `local_review`; invalid match type, identifiers, geometry и image bounds отклоняются существующими helper/schema gates.
- Adapter не читает text/images/pixels, не выводит pixel geometry из character offsets и не сохраняет raw value или source offsets в candidate; входная geometry defensively copied.
- Восемь synthetic/non-identifying tests покрывают четыре approved direct classes, class mismatch, unknown detector, invalid input, value-free output, deterministic behavior и defensive copies. Шесть focused evidence modules проходят `86/86`, полный repository suite — `431/431` в изолированной среде с repository-declared API dependencies.
- OCR workflow теперь явно запускает новый adapter test module. Baseline detector, renderer, review-pack builder, Android app/APK, runtime, OCR, dependencies, external services, real contracts и privacy boundary не изменены.
- `active_track` остаётся `local-pii-redaction`; следующий bounded integration step — `pii-marker-value-decision-adapter-v0`.

### Изменение PR #173

- Candidate validator получил closed compatibility contract для четырёх существующих direct-value detector IDs, четырёх marker detector IDs, двух relation detector IDs и пяти visual detector semantics.
- `auto_mask` теперь требует, чтобы каждый direct-value strong claim был зарегистрирован и совпадал с candidate `proposed_class`; phone evidence для candidate `email` и произвольный `unapproved-digits-v0` fail closed.
- `marker_to_value` и `marker_to_visual` relations считаются strong только при approved relation detector ID и class-compatible marker/target/candidate semantics; phone marker, связанный с signature visual region, больше не может разрешить `auto_mask`.
- Deterministic combiner сохраняет schema-valid mismatched или unapproved evidence как `local_review`, а не выбрасывает его и не повышает до автоматической маски. Нестроковые detector IDs возвращают validation errors без аварии валидатора.
- Exact synthetic regressions audit PR #172 добавлены в candidate-schema, visual-adapter и decision-combiner suites; пять focused evidence modules проходят `78/78`, полный repository suite — `423/423` в изолированной среде с repository-declared API dependencies.
- Компоненты остаются reference-only: baseline detector, renderer, review-pack builder, Android app/APK, production runtime, OCR, pixel classifier, dependencies, external services, real contracts и privacy boundary не изменены.
- `active_track` остаётся `local-pii-redaction`; следующий bounded integration step — `pii-direct-value-decision-adapter-v0`.

### Audit PR #172 после merge PR #171

- Выполнен repository-only cold-start audit с точного `main` SHA `a95a69101af468f955714e3549ab153ada700be3`; до изменения файлов подтверждены `active_track=local-pii-redaction`, `next_step_id=privacy-ocr-cold-start-audit-v1`, согласованность Markdown/JSON state и отсутствие open PR.
- Полностью прочитаны `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md`, `docs/OCR_PROJECT_STATE.md`, `docs/OCR_PROJECT_STATE.json`, `docs/CODEX_WORKFLOW.md`, `docs/PII_EVIDENCE_DETECTOR_V1.md`, `research/hebrew_contract_ocr/pii_candidate_evidence.py`, `research/hebrew_contract_ocr/pii_direct_patterns.py`, `research/hebrew_contract_ocr/pii_marker_value_relations.py`, `research/hebrew_contract_ocr/pii_visual_sensitive_regions.py`, `research/hebrew_contract_ocr/pii_evidence_decisions.py`, `tests/test_ocr_pii_candidate_evidence.py`, `tests/test_ocr_pii_direct_patterns.py`, `tests/test_ocr_pii_marker_value_relations.py`, `tests/test_ocr_pii_visual_sensitive_regions.py`, `tests/test_ocr_pii_evidence_decisions.py` и `.github/workflows/ocr-research-runtime.yml`.
- Фактические entrypoints проверены непосредственно: `research/hebrew_contract_ocr/pii_baseline.py`, `research/hebrew_contract_ocr/pii_mask_renderer.py`, `research/hebrew_contract_ocr/pii_review_pack_builder.py`, `mobile/pii-reviewer/package.json`, `mobile/pii-reviewer/index.js`, `mobile/pii-reviewer/App.js`, все три `mobile/pii-reviewer/src/*.js`, `app.py` и `contract_checker/image_redaction.py`.
- GitHub metadata, bodies, merge commits, changed paths и final-head workflow evidence проверены для PR #168–#171. Merge/head SHA и successful `OCR research runtime` runs: #168 `7e9ab6a8f46fb1aea924916897297c1fc59390ff` / `ebe7103356105fd78324e0859f6db6ece8aa66a5` / run #78; #169 `84c096e04f076b5627bdeb935f23bec456b3cda4` / `0fc94d459e588a9f09bcdfd78f142c1e747b432a` / run #81; #170 `e9b9cce51f15bcd1cc56f685fb77f61c41512d07` / `5db3671e8eebe3f9c94fe1e425d0122896112e17` / run #84; #171 `a95a69101af468f955714e3549ab153ada700be3` / `2d6069cd52b5d993e02818221ca3d09aac5673a6` / run #88. Все четыре merge commits являются ancestors текущего `main`, а каждый PR менял только свой evidence implementation/test, OCR workflow и оба state-файла.
- Architecture/privacy boundary согласована без конфликта: raw images, recoverable PII и unredacted OCR text остаются local; наружу разрешён только irreversibly anonymized derivative; project-owned full Hebrew OCR остаётся paused research; layout-only facts остаются weak evidence; zone-only evidence не может разрешить `auto_mask`; `marker_layout_baseline_v0` остаётся diagnostic comparator.
- Evidence records и relations имеют строгие поля, identifier/geometry validation, defensive copies и value-free helper outputs. Direct patterns детерминированно отклоняют даты, суммы, clause/notice numbers и generic account/cheque numbers; broken/missing relation endpoints, raw-value fields, missing/broader/conflicting strong geometry и invalid schema fail closed. Weak layout votes, unlinked marker и unlinked visual evidence не дают `auto_mask`; empty evidence даёт `preserve`.
- **Blocking consistency defect:** candidate schema и combiner проверяют только syntactic detector IDs, evidence family, relation endpoint family и geometry, но не связывают strong evidence semantics с `proposed_class`. На base SHA synthetic phone record `direct-israeli-phone-v0` с `proposed_class=email` возвращает `auto_mask`; `marker-phone-v0`, связанный с `visual-evidence-signature-v0`, с `proposed_class=phone` также возвращает `auto_mask`. Произвольный syntactically valid `direct_value` detector ID с совпадающей geometry тоже способен разрешить `auto_mask`. Существующие 71 focused tests и workflow run #88 проходят, потому что class-mismatch/unapproved-detector cases отсутствуют; review PR #171 уже указал direct-value class mismatch, но defect вошёл в merge commit.
- Integration truth: evidence modules импортируются только друг другом, focused tests и OCR workflow. Diagnostic baseline продолжает создавать broad-zone `needs_review` candidates старой schema; renderer принимает только `marker_layout_baseline_v0`; builder вызывает line segmenter → baseline → renderer → reviewer core; Android reviewer принимает старые predictions/reason codes; Streamlit/runtime использует manual/test-only `contract_checker.image_redaction` и не импортирует evidence chain. Следовательно, chain остаётся reference-only и не является working detector, renderer path, Android automasking или production runtime.
- Verdict: `BLOCKING CONSISTENCY DEFECT`. Implementation, tests и workflow не исправляются в этом audit PR. Единственный следующий шаг — bounded synthetic-fixture correction `pii-evidence-class-compatibility-v1`; detector integration остаётся последующим blocker после исправления semantic class binding.
- Доказано repository code/tests: closed schemas/families/dispositions, bounded direct-pattern formats, helper ordering/overlap behavior, value-free/defensive-copy behavior, typed relation endpoints, geometry gates, weak/unlinked fail-closed dispositions, empty-evidence preserve и inclusion всех пяти focused modules в OCR workflow.
- Не доказано: real PII recall, complete mask coverage, bounded over-redaction на real contracts, pixel classification handwriting/signatures/stamps, production privacy safety, Android automatic masking, external OCR handoff, cross-contract generalization и controlled human-pilot success.

### Зафиксированный PR #171

- Добавлен dependency-free reference combiner `pii_evidence_decisions.py`, который принимает только уже schema-compatible candidate geometry и evidence records и детерминированно формирует closed candidate disposition.
- Valid strong direct-value или approved marker relation дают `auto_mask` только при точном совпадении candidate geometry с геометрией каждого strong target evidence; отсутствующая, более широкая или конфликтующая strong geometry направляется в `local_review`.
- Непустые weak-layout, unlinked marker и unlinked visual evidence дают только `local_review` с фиксированной ambiguity reason; пустой evidence list даёт `preserve`. Несколько weak facts не усиливаются до `auto_mask`.
- Schema-invalid evidence, broken/missing relation endpoints, raw-value fields, invalid class и invalid geometry отклоняются существующим candidate validator, а входные geometry/evidence defensively copied.
- Synthetic/non-identifying focused suite для пяти evidence modules проходит `71/71`; полный repository suite проходит `416/416`. Workflow дополнен только explicit module `tests.test_ocr_pii_evidence_decisions`.
- Компонент не извлекает evidence, не читает text/images/pixels, не создаёт маски и не интегрирован в baseline detector, renderer, review pack, Android app/APK или production runtime. Dependencies, network calls, external services и privacy boundary не меняются.
- `active_track` остаётся `local-pii-redaction`; после четырёх evidence PR со времени audit #167 следующий шаг продвигается только на обязательный repository-only `privacy-ocr-cold-start-audit-v1`.

### Зафиксированный PR #170

- Добавлен dependency-free reference component `pii_visual_sensitive_regions.py`, который принимает только caller-prevalidated visual observations закрытых типов `filled_field`, `handwriting`, `signature`, `initials` и `stamp` и фиксирует immutable value-free bbox.
- Компонент fail-closed проверяет visual kind, положительные image dimensions, integer/non-boolean coordinates и полное попадание bbox в изображение; generic table border, underline, strikethrough, printed paragraph и любые неизвестные виды не принимаются.
- `make_visual_relation_evidence` создаёт только schema-compatible `visual_sensitive_region` и `marker_to_visual` relation records с новой копией геометрии и caller-supplied evidence IDs; marker evidence, candidate, disposition и masks не создаются.
- Existing candidate schema принимает сгенерированные visual/relation records только вместе с существующим marker evidence; unlinked visual evidence по-прежнему не может валидировать `auto_mask`.
- Synthetic/non-identifying focused suite для candidate schema, direct patterns, marker relations и visual evidence проходит `59/59`; полный repository suite проходит `404/404`. Workflow дополнен только explicit module `tests.test_ocr_pii_visual_sensitive_regions`.
- Компонент не читает пиксели и не доказывает, что область действительно содержит рукопись, подпись, инициалы, печать или заполненное поле: локальная visual classification остаётся обязанностью будущего upstream detector. OCR, images, real contracts, PII, candidates, decisions, masks, baseline/runtime/review-pack/Android integration, dependencies и external services не меняются.
- `active_track` остаётся `local-pii-redaction`; следующий шаг продвигается только на `pii-evidence-decision-combiner-v0`.

### Зафиксированный PR #169

- Добавлен dependency-free reference component `pii_marker_value_relations.py`, который находит только approved ID, phone, email и Israeli IBAN field markers в уже доступном text fragment и связывает их только с class-compatible `DirectValueMatch` из существующего direct-pattern component.
- Relation принимается только в source order marker → value, в пределах одной строки, при gap не более 16 code points и только из whitespace/ограниченной field punctuation; letters, digits и newline в gap запрещены.
- Marker substrings внутри более длинных Hebrew/Latin/numeric tokens отклоняются; overlapping variants разрешаются в пользу длинного marker, а для одного direct value выбирается только ближайший предшествующий compatible marker.
- `MarkerValueRelation` хранит только PII class, marker/value source offsets и detector IDs; raw/normalized values, hashes, marker text и input fragments не возвращаются и не сохраняются.
- `make_marker_relation_evidence` создаёт только schema-compatible family `marker` и `marker_to_value` relation records, ссылаясь на caller-supplied evidence IDs; direct-value evidence, candidate, disposition и pixel geometry из character offsets не создаются.
- Synthetic/non-identifying focused suite для candidate schema, direct patterns и relations проходит `45/45`; полный repository suite проходит `390/390`. Workflow дополнен только explicit module `tests.test_ocr_pii_marker_value_relations`.
- Компонент не выполняет OCR, не читает изображения, не создаёт candidates или masks и не интегрирован в baseline detector, renderer, review pack, Android app/APK или production runtime. Production correctness, privacy safety и cross-contract generalization не доказаны.
- `active_track` остаётся `local-pii-redaction`; следующий шаг продвигается только на `pii-visual-sensitive-region-evidence-v0`.

### Зафиксированный PR #168

- Добавлен dependency-free reference component `pii_direct_patterns.py`, который ищет high-confidence direct PII value formats только в уже доступном text fragment и возвращает immutable value-free spans исходной строки.
- Поддерживаются ровно четыре класса: bounded email (`direct-email-v0`), Israeli local/`+972` phone (`direct-israeli-phone-v0`), девятизначный Israeli ID с check-digit validation (`direct-israeli-id-v0`) и 23-символьный Israeli IBAN с MOD-97 (`direct-israeli-iban-v0`).
- Bounded spaces/hyphens сохраняются в исходных spans; overlap разрешается детерминированным приоритетом Israeli IBAN → email → Israeli phone → Israeli ID, результат сортируется по source position.
- `make_direct_value_evidence` создаёт совместимую с candidate schema запись family `direct_value` без raw/normalized value, hash, hidden copy или candidate disposition; сгенерированная запись валидирует synthetic `auto_mask` candidate.
- Synthetic focused tests покрывают valid/invalid форматы, ambiguous numeric categories, overlap/order, schema rejection raw-value fields, non-string fail-closed и deterministic non-mutating behavior; combined focused suite проходит `31/31`.
- Workflow `OCR research runtime` дополнен только explicit module `tests.test_ocr_pii_direct_patterns`; dependencies и общий workflow design не меняются.
- Компонент не выполняет OCR, не читает изображения, не создаёт candidates или masks и не интегрирован в baseline detector, renderer, review pack, Android app/APK или production runtime. Production detector, real candidate correctness, privacy safety и cross-contract generalization не доказаны.
- `active_track` остаётся `local-pii-redaction`; следующий шаг продвигается только на `pii-marker-value-relation-v0`.

### Зафиксированный audit PR #167 после merge PR #166

- Выполнен repository-only cold-start audit с `main` SHA `a5dec8d2d5ddda7aafd7f2af972118846ae82bcb`: прочитаны binding architecture/privacy/state/process documents, detector contract, candidate schema/tests, baseline, line segmenter, OCR workflow, Android package и repository-owned Android command wrapper.
- Через GitHub и repository history проверены merged PR #160–#166 и их фактические changed paths; все семь merge commits входят в текущий `main`, пересекающихся open PR до начала работы не было.
- Verdict: `PASS WITH BLOCKERS`. Новая сессия однозначно восстанавливает active path: raw images и recoverable PII остаются local, только irreversibly anonymized derivative может пересечь privacy boundary, full project-owned Hebrew OCR paused, а page position/page role и другие layout facts остаются только weak context и не могут дать zone-only `auto_mask`.
- Изменения PR #160–#166 представлены корректно: geometry-only diagnostics, one-command runner, bounded line expansion и oversized-band guard, evidence-based detector contract, Android command loop, Codex orchestration protocol и evidence-bearing candidate schema присутствуют в `main` и разделены по своим proof boundaries.
- Код PR #166 поддерживает closed dispositions `auto_mask`, `local_review`, `preserve`, families `direct_value`, `marker`, `visual_sensitive_region`, `relation`, `weak_layout_context`, typed relation endpoints и fail-closed запрет weak-layout-only `auto_mask`; focused synthetic suite повторно прошёл `13/13`.
- Candidate schema не импортируется текущим `marker_layout_baseline_v0`, renderer, review-pack builder, Android app или production runtime. OCR workflow содержит `tests.test_ocr_pii_candidate_evidence`; mobile package содержит test entrypoint, а `tools/android-dev.ps1` содержит `doctor`, `build`, `run`, `logs`, `restart`.
- Current-state component table дополнена отдельной schema row. `docs/PII_EVIDENCE_DETECTOR_V1.md` section 9 фиксирует pre-PR-166 migration checkpoint; operational current next step определяется каноническими state-файлами и уже продвинут на `pii-direct-pattern-evidence-v0`.
- Audit обнаружил и исправил устаревшее утверждение component table о непройденном real run: repository-external `2_review_pack` уже был локально прогнан через geometry-only diagnostic до PR #162, охватив 3 страницы, 46 candidates и `66.6%` общей закрытой площади; contract text, images, PII values, IDs, hashes и raw documents не коммитились.
- Доказаны только strict schema validation, synthetic focused tests и обязательный framework-independent CI coverage. Не доказаны production PII detector, Android automatic masking, production privacy safety, controlled human pilot, external OCR handoff и generalization across contracts.
- Оставшиеся blockers: direct-value patterns ещё не реализованы; schema не интегрирована в detector/runtime; новый evidence-based review pack и human/generalization/privacy evaluation не выполнены. Эти blockers не требуют изменения architecture/privacy state в этом audit PR.
- `active_track=local-pii-redaction` и `next_step_id=pii-direct-pattern-evidence-v0` не изменены. Runtime, data handling, dependencies, workflow, Android, OCR, external services и privacy boundary не меняются; application/build/install/device/external-service validation не заявляется.

### Зафиксированный PR #166

- Добавлен dependency-free валидатор строгой schema для evidence-bearing PII candidates с dispositions `auto_mask`, `local_review` и `preserve`; набор `proposed_class` переиспользуется из `pii_annotations.py`.
- Candidate/evidence geometry, identifiers, enums, обязательные и неизвестные поля, duplicate evidence IDs, relation endpoints и integer-координаты проверяются fail-closed; raw text/value не входят в schema.
- `auto_mask` разрешён только для validated `direct_value` evidence либо approved marker-to-value/marker-to-visual relation. Один или несколько `weak_layout_context`, unlinked marker и unlinked visual evidence не могут создать `auto_mask`.
- `local_review` требует хотя бы одну evidence record и непустой `ambiguity_reason`; synthetic focused suite покрывает также `preserve`, broken/self relations, geometry bounds, bool coordinates и deterministic validation.
- Focused validation прошла: `python -m py_compile research/hebrew_contract_ocr/pii_candidate_evidence.py` и `python -m unittest tests.test_ocr_pii_candidate_evidence` (`13/13`).
- Изменение не интегрировано в detector, renderer, review pack, Android app/APK или production runtime; real PII, contracts, images, OCR, network calls, external services и новые dependencies не использовались.
- Следующий шаг — только deterministic direct-value patterns на synthetic/non-identifying fixtures. Production detector, marker recognition и automatic runtime masking ещё не реализованы.

### Зафиксированный PR #165

- По прямому запросу владельца продукта как ограниченное process exception добавлен `docs/CODEX_WORKFLOW.md`, который фиксирует разделение ролей: владелец продукта выбирает направление и решает о merge, управляющий диалог формирует bounded task и независимо аудитит PR, Codex исполняет задачу внутри репозитория и не мержит.
- Постоянные процессные документы больше не должны хранить якобы текущий номер PR, branch, `active_track` или `next_step_id`; эти значения каждый раз читаются из актуальных state-файлов на `main`.
- Зафиксирован точный порядок: binding sources → проверка пересекающихся PR → Context Gate до edits → branch от текущего `main` → focused checks → draft PR → state update после получения номера → финальные проверки на последнем head SHA → diff audit → Ready без auto-merge.
- Финальные claims обязаны ссылаться на base SHA, final head SHA, точные команды, результаты/exit codes и workflow run identifiers; проверки более раннего commit не считаются доказательством итогового diff.
- Самостоятельный failure loop ограничен двумя последовательными исправлениями одной root cause; при смене категории ошибки, speculative fix или расширении scope Codex обязан остановиться.
- Введён явный repository-hygiene gate: без отдельного разрешения нельзя коммитить build directories, APK, artifacts, logs, caches, IDE metadata, temporary scripts/workflows, repository-external reports и lock-file изменения без изменения dependencies.
- Управляющий ассистент не может заявлять, что задача передана Codex или выполняется, если реального Codex invocation не было; при недоступном dispatch публикуется готовый task packet с честным статусом `execution not started`.
- Независимый аудит PR обязан проверить base/head SHA, единственный Context Gate, declared/actual paths, финальные проверки, state consistency, privacy boundary, generated files и auto-merge state до рекомендации merge.
- Изменение документационное/process-only: runtime, detector, renderer, Android reviewer, APK, OCR, dependencies, external APIs, privacy boundary, `active_track` и `next_step_id` не меняются. Application/Android tests не запускались, поскольку исполняемый код не изменён.

### Зафиксированный PR #164

- По прямому запросу владельца продукта как ограниченное process exception в `AGENTS.md` зафиксирован канонический локальный Android-цикл для Codex без ручного копирования кода в Android Studio.
- Для mobile changes теперь явно указаны существующие repository-owned entrypoints: `npm --prefix mobile/pii-reviewer test` и `tools/android-dev.ps1` с командами `doctor`, `build`, `run`, `logs`, `restart`.
- Repository wrappers объявлены основным automation/evidence path вместо Android Studio copy/paste, прямого Gradle или `expo run:android`; низкоуровневая диагностика допустима только в отдельно ограниченной задаче.
- Зафиксирован обязательный failure loop: прочитать output и локальный failure log, определить первую actionable root cause, внести минимальное in-scope исправление, повторить упавшую команду и затем заново прогнать финальные tests/build/device checks на итоговом diff.
- Codex обязан остановиться, если дальнейшее исправление требует новой зависимости, подсистемы, privacy/product decision, destructive device action, недоступного credential/authorized device или расширения scope.
- Средовые ошибки Java, SDK, Node, Gradle и adb нельзя маскировать изменением product code; после toolchain failure повторно запускается `doctor`.
- Device validation нельзя объявлять выполненной без фактического успешного `run`; `logs` используется после runtime failure, а `restart` — только для уже актуального установленного APK.
- Изменение документационное/process-only: runtime приложения, Android-код, зависимости, data handling, OCR, внешние API, privacy boundary, `active_track` и `next_step_id` не меняются.
- Статически подтверждено, что все перечисленные команды существуют в текущих `mobile/pii-reviewer/package.json` и `tools/android-dev.ps1`; Windows/Gradle/adb/Samsung A55 команды в этом PR не запускались, поскольку исполняемый код не изменён.

### Зафиксированный PR #163

- Владелец продукта остановил подгонку fixed page-zone thresholds под один трёхстраничный договор: такой путь не обобщается на другие шаблоны, рукописные поля и расположение реквизитов.
- Добавлен binding contract `docs/PII_EVIDENCE_DETECTOR_V1.md`: положение строки, номер страницы и first/last-page role являются только weak context и никогда не достаточны для `auto_mask`.
- `marker_layout_baseline_v0` заморожен как diagnostic comparator и не считается production detector policy.
- Production candidate должен нести явное evidence: direct value pattern, marker-to-value/field relation либо validated handwriting/signature/stamp signal; zone-only candidate может быть только `local_review` или `preserve`.
- Evaluation делится по целым договорам: страницы одного договора не смешиваются между development и held-out split; известные template families группируются по возможности; contract-specific coordinates и one-off exceptions запрещены.
- Controlled Android reviewer и repository-external pilot не удаляются, но откладываются до появления evidence-bearing candidates: измерять human metrics на заведомо непригодной zone-only policy нецелесообразно.
- Единственный следующий шаг изменён на `pii-candidate-evidence-schema-v0`: строгая candidate/evidence schema и validation, которая технически запрещает zone-only `auto_mask`.
- Runtime, renderer, Android APK, маски существующего pack, зависимости, OCR, внешние API и privacy boundary не меняются.

### Зафиксированный PR #162

- Geometry-only diagnostic на repository-external трёхстраничном review pack измерил 46 mask candidates и `66.6%` фактически закрытой площади: `51.5%`, `70.4%` и `77.9%` по страницам.
- `38/46` candidates (`82.6%`) созданы broad-zone rules, а `30/46` содержат `segmentation_review`; diagnostic не содержал contract text, PII values, image IDs, hashes или изображений и не коммитился.
- Корневая причина крупных масок локализована в line segmentation: sparse foreground мог без ограничения расширять active band через сотни рядов и объединять несколько абзацев до PII classification.
- Sparse-row expansion теперь ограничен тремя рядами сверху и снизу. Одиночная тонкая вертикальная помеха остаётся отдельным rejected noise region и больше не расширяет соседние текстовые строки.
- Неразрешённый foreground band выше `max(180 px, 10% page height)` останавливает segmentation fail-closed с `unresolved oversized foreground band` вместо публикации гигантского candidate.
- Два новых synthetic tests проверяют разделение трёх строк при тонком вертикальном соединителе и fail-closed поведение при широком неразрешимом соединителе; полный line-segmenter suite прошёл `25/25`.
- GitHub Actions `OCR research runtime` run #62 прошёл: CPU training smoke и полный privacy/recognizer suite завершились успешно.
- Existing `2_review_pack` остаётся неизменным и не используется как доказательство исправления. После merge нужно собрать новый repository-external pack в новый output directory и повторить geometry-only diagnostic.
- Detector zone rules, mask expansion, renderer, Android reviewer, зависимости, внешние API, OCR, `active_track` и `next_step_id` не меняются.

### Зафиксированный PR #161

- Добавлен локальный runner `tools/run_pii_mask_diagnostics.py`, который запускает уже существующую geometry-only diagnostic без ручного переключения текущей ветки.
- Runner обновляет только remote ref `origin/main`, создаёт временный detached worktree из актуального `origin/main`, запускает diagnostic и затем удаляет временный checkout.
- Готовый JSON-отчёт создаётся рядом с repository-external review pack; существующий output не перезаписывается.
- Текущая локальная ветка, tracked/untracked файлы рабочего дерева, Android-приложение и телефон не изменяются.
- Runner не декодирует изображения, не читает contract text и не отправляет review pack или report во внешние сервисы.
- Synthetic tests покрывают временный main worktree, отсутствие `git switch`, no-overwrite, cleanup и сохранение файла, появившегося независимо во время failure.
- GitHub Actions `OCR research runtime` run #56 прошёл: CPU training smoke и полный privacy/recognizer suite завершились успешно.
- Реальный `2_review_pack` ещё не прогнан через runner. Detector rules, renderer, Android reviewer, runtime, зависимости, внешние API, OCR, `active_track` и `next_step_id` не меняются.

### Зафиксированный PR #160

- Добавлен локальный CLI `pii_mask_diagnostics_v0` для измерения происхождения и площади текущих масок до изменения detector rules.
- Инструмент читает только готовые `predictions.jsonl`, `renderer/manifest.jsonl` и `line_segmentation/manifest.jsonl`; изображения не декодируются, текст договора не извлекается.
- Отчёт показывает точную долю закрытых пикселей, количество кандидатов по reason code, долю broad-zone rules и коэффициент расширения маски относительно исходной строки.
- В отчёт не попадают image/page IDs, candidate IDs, filenames, paths, hashes, contract text или PII values; страницы обозначаются только порядковыми номерами.
- Output создаётся только как новый файл вне review pack; существующий файл не перезаписывается.
- GitHub Actions `OCR research runtime` run #50 прошёл: CPU training smoke и полный набор из 44 privacy/recognizer tests завершились успешно.
- Реальный трёхстраничный pack ещё не прогнан через diagnostic. Detector rules, candidate schema, renderer semantics, Android reviewer, runtime, внешние API, OCR, `active_track` и `next_step_id` не меняются.

### Зафиксированный PR #159

- После merge PR #156–#158 выполнен обязательный repository-only cold-start audit.
- Повторно сверены `AGENTS.md`, архитектура, privacy/OCR pipeline, оба state-файла, Context Gate, Android package и локальные Android-команды.
- Архитектурного дрейфа не найдено: действующая цепочка остаётся local PII detection → irreversible masking → local validation → только затем approved external OCR.
- Фактическая проверка PR #158 завершена: mobile tests прошли `14/14`, release build завершился `BUILD READY`, установка — `RUN READY`, а Samsung A55 smoke подтвердил корректный первый показ, переключение source/masked и блокировку касаний до загрузки.
- Найдено отставание документации: merged state ошибочно продолжал считать Samsung A55 smoke невыполненным. Этот PR синхронизирует state с фактическим результатом.
- На реальном трёхстраничном pack визуально подтверждено существенное excessive over-redaction: крупные маски закрывают юридически значимые абзацы. Следующий bounded diagnostic внутри текущего pilot должен установить источник расширения каждой маски до изменения detector rules.
- Verdict: `PASS WITH ONE MEASUREMENT BLOCKER`. Privacy boundary и общий пайплайн согласованы; точность текущего detector и причины excessive over-redaction ещё не измерены.
- Runtime, detector, renderer, маски, зависимости, OCR, внешние API, `active_track` и `next_step_id` не меняются.

### Зафиксированный PR #158

- По прямому запросу владельца продукта как ограниченный corrective исправлен первый показ страницы после выбора review pack на Samsung A55.
- `PageCanvas` больше не создаёт `Image` до получения фактического размера области просмотра; после layout изображение монтируется сразу с окончательной геометрией.
- Смена страницы, режима или размера создаёт новый экземпляр изображения, поэтому UI не зависит от случайной Android-перерисовки.
- Пока файл изображения не загрузился, приложение показывает `Загрузка страницы…`, не рисует finding overlays и игнорирует касания по canvas, чтобы исключить ложные отметки по пустому экрану.
- Выбор новой папки всегда возвращает режим `Исходник`, а не сохраняет режим предыдущего pack.
- Изменение ограничено `mobile/pii-reviewer/App.js`; review-pack schema, PNG validation, detector, renderer, маски, категории проверки, сохранение результата, зависимости и внешние вызовы не меняются.
- Локальные mobile tests прошли `14/14`; release build завершился `BUILD READY` с SHA-256 `058da3013726ec187e7e7479319b4e9cfd1dc9a91031cb73740e14940cec9035`; установка завершилась `RUN READY`.
- Samsung A55 smoke успешен: исходник сразу отображается на всех трёх страницах, source/masked switching работает, касания до загрузки игнорируются, локальное сохранение результата завершается без ошибки.
- Копирование и проверка canonical review JSONL на компьютере, а также human pilot остаются следующим этапом.
- Реальные страницы, PII и contract text не коммитятся. `active_track` и `next_step_id` не меняются.

### Зафиксированный PR #157

- Первая попытка открыть готовый repository-external трёхстраничный review pack на Samsung A55 остановилась с общим сообщением `image dimensions mismatch`.
- Локальная проверка exact pack показала, что все три source PNG, три masked PNG и соответствующие manifest rows имеют одинаковые размеры `1974 × 3508`, а SHA-256 совпадают.
- Причина локализована в Android reviewer: размер source проверялся через Android image decoder после cache snapshot, а размер derivative — непосредственно по PNG bytes; integrity check использовал два разных способа измерения.
- PR проверяет оба изображения одинаково — по уже проверенным PNG bytes до создания app-private snapshots — и требует для source и derivative формат 8-bit grayscale PNG.
- При реальном несовпадении ошибка теперь называет page ID, ожидаемый размер и фактический размер конкретного source или derivative.
- Focused Node suite прошёл `7/7`; exact repository-external pack проходит чистый pack loader как три страницы `1974 × 3508`.
- Фактический Samsung A55 smoke успешен: та же папка открывается, доступны исходные и замаскированные версии всех трёх страниц. При первом показе исходник по-прежнему иногда требует переключения `После масок → Исходник`; это отдельный UI/repaint defect и не относится к проверке размеров.
- Publication/readback review JSONL и human pilot остаются недоказанными.
- Реальные страницы, PII и contract text не коммитятся. Detector, renderer, маски, review categories, зависимости, внешние API, OCR, `active_track` и `next_step_id` не меняются.

### Зафиксированный PR #156

- По прямому запросу владельца продукта как ограниченное process exception команда `tools/android-dev.ps1` расширена режимом `restart` для остановки и повторного запуска уже установленного актуального Android package без Metro и без переустановки APK.
- Пользовательский entrypoint остаётся единым; device-specific логика вынесена во внутренний `tools/android-restart.ps1`, поэтому основной PowerShell-файл изменён только в `ValidateSet` и dispatch.
- `restart` читает package из `mobile/pii-reviewer/app.json`, требует ровно одно готовое adb-устройство и блокируется, если package не установлен.
- Команда выполняет `am force-stop`, подтверждает отсутствие процесса, запускает launcher ограниченным `monkey`-вызовом и подтверждает новый процесс через `pidof`.
- Serial, model, PID и raw adb output не печатаются. APK не собирается и не устанавливается, данные приложения не очищаются, logcat не читается.
- Фактический Windows/Samsung A55 run завершён успешно: приложение остановилось и повторно открылось без Metro, команда дошла до `RESTART READY`.
- Runtime приложения, privacy boundary, detector/renderer, OCR, зависимости, внешние API, `active_track` и `next_step_id` не меняются.

### Зафиксированный audit PR #155

- После merge PR #149–#154 выполнен обязательный repository-only cold-start audit без использования истории чата как источника состояния.
- Прочитаны с актуального `main` все пять binding sources; отдельно сверены PR template, trusted Context Gate workflow/validator, Android package identity, automation entrypoints и CLI review-pack builder.
- Текущая privacy-архитектура восстанавливается однозначно: raw contract photos и recoverable PII не покидают устройство; active path остаётся local PII detection → irreversible masking → local validation → только затем approved external OCR.
- `active_track=local-pii-redaction`, `next_step_id=controlled-pii-reviewer-pilot-v0` и next-step summary семантически совпадают в Markdown/JSON state и не конфликтуют с architecture/pipeline contracts.
- `python -m research.hebrew_contract_ocr.pii_review_pack_builder` имеет CLI-entrypoint, fail-closed publication и успешный terminal marker `PACK READY`; ранее заявленный one-command builder существует в `main`.
- Доказанные и недоказанные свойства разделены корректно: Android automasking, реальные privacy metrics, first-paint reliability и publication/readback review JSONL не объявлены доказанными; `restart` также остаётся нереализованным.
- Android automation state соответствует фактическим entrypoints `doctor`, `build`, `run`, `logs`; package identity соответствует `com.jancoo.piireviewerpilotv2`.
- PR template, trusted workflow и `scripts/check_pr_context_gate.py` используют одинаковые Context Gate v1 fields и обязательные state paths.
- Вердикт аудита: `PASS`; новых repository blockers не найдено. Единственный product blocker остаётся прежним — controlled human pilot на repository-external трёхстраничном договоре.
- Runtime, data handling, dependencies, OCR, detector/renderer, внешние API, `active_track` и `next_step_id` не меняются.

## 1. Изменение PR #154

- По прямому запросу владельца продукта как ограниченное process exception команда `tools/android-dev.ps1` расширена режимом `logs` для локального чтения недавних warning/error-сообщений текущего Android package.
- Пользовательский entrypoint остаётся единым; device-specific логика вынесена во внутренний `tools/android-logs.ps1`, поэтому существующие `doctor`, `build` и `run` не перерабатываются.
- `logs` требует ровно одно готовое adb-устройство и уже запущенный процесс актуального package из `mobile/pii-reviewer/app.json`.
- Запрос ограничен process-scoped `logcat --pid`, snapshot-режимом `-d`, уровнем warning/error, последними 200 сообщениями и максимум 120 строками пользовательского вывода.
- Общий системный logcat, live stream, логи других приложений и raw-файл не создаются и не показываются.
- Перед выводом локально редактируются пути, URL, email, UUID, длинные номера, Hebrew-текст, длинные hex-токены и PID-подобные значения; строки ограничены 500 символами.
- Serial, model, PID и raw adb output не печатаются. Это снижает, но не доказывает нулевой риск утечки через произвольный текст ошибок; пользователь не должен публиковать вывод без дополнительного просмотра.
- Фактический Windows/Samsung A55 run завершён успешно: команда дошла до `LOGS READY`, актуальный package и единственное готовое устройство подтверждены, warning/error-строк в выбранном process-scoped окне не найдено; serial и PID в вывод не попали.
- В PR не входят `restart`, clear-logcat, live streaming, экспорт логов, install/build, чтение договоров или review packs, runtime приложения, OCR, detector/renderer, внешние API, `active_track` или `next_step_id`.

## 2. Изменение PR #153

- По прямому запросу владельца продукта как ограниченное process exception команда `tools/android-dev.ps1` расширена режимом `run` для установки и запуска уже собранного standalone APK без Metro.
- Пользовательский entrypoint остаётся единым; device-specific логика вынесена во внутренний `tools/android-run.ps1`, чтобы основной PowerShell-файл не превысил 400 строк.
- `run` использует только существующий локальный `mobile/pii-reviewer/build-artifact/PII-Pilot-V2.apk`, читает актуальный package из `mobile/pii-reviewer/app.json` и не запускает автоматическую сборку.
- Перед изменением устройства требуется ровно одно готовое adb-устройство и отсутствие offline/unauthorized устройств; выбор между несколькими устройствами не выполняется.
- APK устанавливается через `adb install -r`, прежний процесс останавливается, launcher запускается без Metro, после чего `pidof` проверяет наличие процесса приложения.
- Serial, model и raw adb output не печатаются ни при успехе, ни при failure; сохраняются только агрегированные статусы без идентификаторов.
- В PR не входят logcat, `logs`, `restart`, uninstall, data wipe, исправление среды, чтение договоров, review packs или PII.
- Фактический Windows/Samsung A55 run завершён успешно: APK установлен, launcher открыл приложение без Metro, а process confirmation прошёл; устройство и PID в вывод не попали.
- Runtime приложения, privacy boundary, detector/renderer, OCR, зависимости, внешние API, `active_track` и `next_step_id` не меняются.

## 3. Изменение PR #152

- По прямому запросу владельца продукта как ограниченное process exception команда `tools/android-dev.ps1` расширена режимом `build` для локальной standalone release-сборки Android APK.
- Build-preflight повторно использует проверки проекта, Expo dependencies, Node.js, JDK 17 и Android SDK, но не требует подключённого телефона; failure останавливает сборку до Expo/Gradle.
- После успешного preflight выполняются `expo prebuild --clean` и Gradle `assembleRelease`; результат публикуется локально как `mobile/pii-reviewer/build-artifact/PII-Pilot-V2.apk` с SHA-256.
- Первый Windows-run подтвердил корректную блокировку Java 21. После временного переключения на Temurin JDK 17 preflight прошёл с итогом `9 passed, 2 warnings, 0 failures`.
- Первая Gradle-попытка выявила, что найденный по стандартному пути Android SDK не передавался Gradle при незаданном `ANDROID_HOME`; исправление создаёт локальный generated `android/local.properties` с `sdk.dir` после prebuild, не меняя системные переменные и не печатая абсолютный путь.
- Generated `mobile/pii-reviewer/android/` и `mobile/pii-reviewer/build-artifact/` исключены из Git. Raw build logs остаются только локально при failure и могут содержать локальные пути.
- После SDK-fix локальная release-сборка на Windows с Temurin JDK 17 успешно завершилась строкой `BUILD READY`; создан `PII-Pilot-V2.apk` с SHA-256 `d50b00b479b8baee7ecd7ef7af09aacae1e5ec162264968cae9f32010639c557`.
- Runtime приложения, privacy boundary, detector/renderer, OCR, зависимости, внешние API, `active_track` и `next_step_id` не меняются.

## 4. Изменение PR #151

- По прямому запросу владельца продукта как ограниченное process exception добавлена read-only команда `tools/android-dev.ps1 doctor` для предварительной диагностики локальной Windows/Android/Expo-среды.
- Команда проверяет расположение mobile-проекта, `package.json`, `app.json`, актуальный Android package, Node.js/npm/npx, JDK 17, `JAVA_HOME`, Android SDK, `ANDROID_HOME`, adb, подключённые устройства, Expo dependencies и наличие Gradle wrapper.
- Скрипт не запускает Metro, Gradle или приложение, не устанавливает APK, не изменяет файлы проекта и не читает договоры, изображения, review packs или PII.
- Серийные номера, модели и другие идентификаторы устройств из `adb devices -l` не выводятся; сохраняется только агрегированное количество готовых или заблокированных устройств.
- Критические ошибки дают exit code `1`; предупреждения о необязательном текущем состоянии, включая отсутствие подключённого устройства или `node_modules`, не считаются падением.
- Первый запуск в Windows PowerShell 5.1 выявил terminating `NativeCommandError` на штатном stderr `java -version`; исправление через `System.Diagnostics.Process` подтверждено повторным полным запуском.
- Повторный запуск выдал итог `9 passed, 2 warnings, 1 failure`: корректно обнаружены Node.js 24 как warning относительно CI Node 22, Java 21 как failure относительно JDK 17, незаданный `ANDROID_HOME` как warning и одно готовое Android-устройство без вывода его идентификаторов.
- Runtime приложения, privacy boundary, detector/renderer, OCR, зависимости, внешние API, `active_track` и `next_step_id` не меняются.

## 5. Изменение PR #150

- По прямому запросу владельца продукта добавлена отдельная Android pilot identity: launcher name `PII Pilot V2`, package ID `com.jancoo.piireviewerpilotv2`, version `0.1.1`, versionCode `2`.
- GitHub Actions собирает новый release APK через Gradle и публикует его как `PII-Pilot-V2.apk`; это отдельное приложение и оно не заменяет старый development build или прежний reviewer APK в эмуляторе.
- Ручная перепаковка существующего APK не считается допустимым build path: такой файл не прошёл Android certificate parsing и отброшен.
- Review-pack schema, detector, renderer, reviewer logic, privacy boundary, зависимости, внешние API и правила обработки данных не меняются.
- `active_track` и `next_step_id` не меняются; corrective PR только разблокирует проверку текущего controlled pilot в эмуляторе.

## 6. Изменение PR #149

- Добавлен `controlled_pii_review_pack_builder_v0`: одна локальная CLI-команда собирает Android review pack из уже нормализованных grayscale page masters.
- Builder последовательно запускает текущие line segmentation, `marker_layout_baseline_v0` и `grayscale_opaque_mask_v0`, копирует byte-identical source masters и проверяет итог существующим Python reviewer core.
- Final pack содержит только требуемые source, prediction, renderer и neutral-line artifacts; временный geometry-only annotation manifest и рабочие файлы не публикуются.
- Существующий output path не перезаписывается; failure очищает sibling staging и не оставляет частичный pack.
- Focused builder tests включены в обязательный `OCR research runtime`; GitHub Actions run #43 прошёл полностью.
- Repository-only cold-start audit после PR #148 завершён с вердиктом `PASS WITH ONE OPERATIONAL BLOCKER`: binding documents, state и Context Gate согласованы, а единственным найденным препятствием была ручная сборка review pack. PR #149 закрывает именно этот operational blocker.
- `active_track` и `next_step_id` не меняются: следующий шаг остаётся реальным controlled human pilot.
- Detector rules, renderer semantics, Android APK, зависимости, внешние API и правила обработки данных не изменены.

## 7. Цель продукта и privacy boundary

Построить локальный компонент для фотографий израильских договоров аренды, который:

- обнаруживает вероятные области с PII;
- всегда считает адрес арендуемой квартиры PII;
- необратимо заменяет чувствительные пиксели на устройстве;
- сохраняет суммы, сроки, номера пунктов и юридически значимый текст, если они отделимы от PII;
- блокирует внешнюю передачу при неопределённости;
- передаёт внешнему OCR/LLM только проверенный обезличенный derivative.

```text
raw phone photo
→ on-device geometric/image preprocessing
→ on-device PII-region detection
→ irreversible local masks
→ local fail-closed privacy validation
→ anonymized image/document
→ approved external full OCR
→ secondary text redaction
→ evidence blocks
→ legal-risk analysis
→ Russian report
```

До измеримого privacy pilot и metrics запрещено отправлять пользовательские изображения или производные во внешний OCR/LLM.

Полный project-owned Hebrew OCR, recognizer, CRNN, CTC training, Gold и CER остаются paused research и не являются MVP-блокером.

## 8. Реальное состояние компонентов

| Компонент | Состояние | Доказано | Не доказано |
|---|---|---|---|
| Page boundary + normalization | Python reference v0 | Ограниченный preview, accepted quad/null fallback, bounded grayscale master, hashes и synthetic/fixture tests | Android memory implementation и production capture quality |
| Line segmentation | Python reference v0 + giant-band guard | Детерминированные line regions, QA overlays, foreground accounting; bounded sparse-row expansion и unresolved oversized-band fail-closed покрыты synthetic tests | Реальный rebuild нового review pack и повторная over-redaction диагностика |
| Local PII annotation contract | Reference v0 | Closed classes/statuses, immutable image identity, bbox/polygon validation | Human annotations и privacy metrics |
| PII candidate evidence schema | Python reference v1 with closed class binding | Closed dispositions/families, strict identifiers/geometry/relations, approved detector/relation registries, class-compatible strong evidence и fail-closed запрет weak-layout-only/mismatched/unapproved `auto_mask` покрыты synthetic tests | Detector/runtime integration, real candidate correctness и production privacy safety |
| Direct PII value patterns | Python reference v0 | Dependency-free bounded email, Israeli phone, check-digit Israeli ID и MOD-97 Israeli IBAN возвращают original spans и value-free evidence; overlap priority, ambiguous-number rejection и schema compatibility покрыты synthetic tests и обязательным OCR CI | Detector/runtime integration, real correctness, production privacy safety и cross-contract generalization |
| Direct-value decision adapter | Python reference v0 with structural and provenance gates | Один structurally valid `DirectValueMatch` допускается только при exact совпадении class/detector/start/end с approved finder result для caller-supplied local source text; forged records отклоняются до candidate, output остаётся value-free | Upstream local source-text extraction, pixel geometry mapping, detector/runtime integration, real correctness и production privacy safety |
| Marker-to-direct-value relations | Python reference v0 | Approved marker variants, source-level class compatibility, bounded same-line gap, token boundaries, nearest-marker selection, immutable value-free spans и schema-compatible marker/relation evidence покрыты synthetic tests и включены в обязательный OCR CI | Downstream candidate `proposed_class` binding, detector/runtime integration, real correctness, production privacy safety и cross-contract generalization |
| Marker-value decision adapter | Python reference v0 | Один existing `MarkerValueRelation` связывается только с exact class/detector/offset-compatible `DirectValueMatch`; caller-supplied geometry проходит через value-free helpers и class-bound combiner, forged or malformed spans fail closed | Text/image extraction, pixel geometry mapping, detector/runtime integration, real correctness и production privacy safety |
| Visual sensitive-region evidence | Python reference v0 | Closed caller-prevalidated kinds, immutable in-bounds bbox, value-free visual evidence, typed marker-to-visual endpoints и downstream class-compatibility regressions покрыты synthetic tests | Pixel-based visual classification, spatial marker linkage, detector/runtime integration, real correctness и production privacy safety |
| Visual decision adapter | Python reference v0 | Один caller-prevalidated `VisualSensitiveRegion` получает fixed visual class либо approved marker-derived class; exact bbox проходит через visual relation helper и class-bound combiner, missing/mismatched/unapproved marker semantics fail closed | Pixel classification, marker extraction/spatial linkage, detector/runtime integration, real correctness и production privacy safety |
| Evidence decision combiner | Python reference v1 with class-bound strong evidence | Closed deterministic dispositions, schema rejection, exact strong-target geometry, weak/unlinked/mismatched/unapproved local review и empty-evidence preserve покрыты synthetic tests | Evidence extraction, detector/runtime integration, real correctness, production privacy safety и cross-contract generalization |
| Local PII detector | `marker_layout_baseline_v0` | Детерминированные candidates без OCR, cloud calls или ground-truth leakage | Реальные recall, complete coverage и over-redaction |
| Local mask renderer | Python reference v0 | Новый grayscale PNG, физическая замена candidate pixels, metadata stripping, deterministic publication | Candidate correctness, Android behavior и production privacy safety |
| Reviewer manifest core | Reference v0 | Три closed finding categories, canonical geometry/JSONL и immutable hashes | Controlled human pilot |
| Review pack builder | `controlled_pii_review_pack_builder_v0` | One-command local assembly, byte-identical sources, exact hashes/bindings, strict line manifest, no-overwrite publication и cleanup покрыты synthetic focused tests и CI | Удобство фактической передачи pack и human pilot |
| Android PII reviewer | Standalone Expo APK + PR #157 dimensions fix + PR #158 first-paint corrective | Автономный запуск; direct PNG-byte validation; реальный pack открывается на Samsung A55 как 3 страницы; first-paint, loading indicator, touch gate и локальное сохранение результата подтверждены на Samsung A55 | Publication/readback результата на компьютере, human pilot |
| Android development automation | `doctor` v0 + `build` v0 + `run` v0 + `logs` v0 + `restart` v0 | Полный Windows PowerShell 5.1 doctor-run; Java 21 fail-closed preflight; Temurin JDK 17 preflight; SDK handoff; успешная локальная release-сборка; подтверждённые install, launcher, process check, process-scoped warning/error logs и stop/start/process confirmation на Samsung A55 без Metro | Остаточный риск PII в произвольных error strings |
| Mask diagnostics runner | `one-command-pii-mask-diagnostics-v0` | Временный `origin/main` worktree, отсутствие branch switch, sibling no-overwrite report и cleanup покрыты synthetic tests и CI; выполнен real local run на repository-external `2_review_pack`: geometry-only report охватил 3 страницы, 46 candidates и `66.6%` общей закрытой площади; contract text, images, PII values, IDs, hashes и raw documents не коммитились | Повторный run на заново собранном pack после PR #162; correctness evidence-based detector; production privacy safety; generalization across contracts |
| Android detector/renderer | Не реализован | — | On-device automatic detection and masking |
| External OCR handoff | Не подключён | Разрешён только после privacy gate | Безопасность derivative не доказана |

## 9. Synthetic Android smoke: фактические результаты

Использован repository-external одностраничный synthetic pack без договора и PII.

Подтверждено в Pixel 8 / Android 17 emulator:

- standalone APK устанавливается и запускается без Metro;
- локальная директория выбирается;
- pack schemas, paths, hashes, dimensions и bindings проходят validation;
- masked image отображается;
- после переключения `После масок → Исходник` source image отображается корректно;
- касание нейтральной строки создаёт красную рамку;
- page status становится `fail`, findings count становится `1`.

Оставшиеся ограничения:

- создание и чтение `review-<prediction_sha256>.jsonl` на компьютере фактически не подтверждено;
- это не проверка Android automasking, PII recall или privacy safety.

Standalone launch, открытие реального трёхстраничного pack, first-paint, loading/touch gate и локальное сохранение результата на Samsung A55 подтверждены. Копирование review JSONL, exact-hash readback и controlled human pilot остаются недоказанными, но после PR #163 отложены до появления evidence-based candidates и нового review pack.

## 10. Активный блокер и pilot input

Class-binding consistency defect, malformed-span bypass и direct-value provenance закрыты reference-level gates; direct-value, marker-to-value и visual chains проходят через минимальные executable decision adapters. Product blockers остаются прежними: evidence extraction ещё не объединён в detector, upstream local source text не подключён к direct adapter, реальный pixel-based visual classifier не реализован, а `marker_layout_baseline_v0` по-прежнему создаёт broad-zone findings по фиксированным вертикальным зонам и не годится для production metrics или Android automasking.

Human pilot остаётся обязательным позже для `missed_pii`, `incomplete_mask` и `over_redaction`, но сначала candidates должны нести проверяемое evidence и запрещать zone-only `auto_mask`.

У владельца продукта есть repository-external трёхстраничный договор, в котором почти весь текст напечатан, а рукописными остаются только подписи. Из него собран exact review pack; hashes и размеры согласованы, а APK надёжно отображает все три страницы на Samsung A55. Geometry-only diagnostic измерил 46 candidates и `66.6%` закрытой площади; `30/46` candidates содержат `segmentation_review`, что локализовало первичную причину excessive over-redaction в giant line bands. PR #162 добавил bounded sparse-row expansion и fail-closed giant-band guard. PR #163 фиксирует более глубокую причину: fixed page zones применяются ко всем страницам и ведут к переобучению на одном шаблоне. PR #166 добавил evidence-bearing candidate schema, PR #168 — value-free direct-value reference, PR #169 — bounded marker-to-direct-value relations, PR #170 — caller-prevalidated visual-sensitive-region evidence adapter, PR #171 — deterministic decision combiner, PR #174 — direct-value-to-decision reference adapter, PR #175 — marker-value-to-decision reference adapter, а PR #176 — visual-to-decision reference adapter; эта цепочка ещё не интегрирована в baseline или runtime. Старый `2_review_pack` остаётся immutable; новый pack не собирается до следующих evidence-based detector slices. Сам договор, normalized pages, manifests, derivatives, diagnostic output и review result не коммитятся в GitHub и не передаются внешним сервисам.

## 11. Единственный следующий шаг

**`pii-direct-value-match-provenance-v1`: MERGE-GATED — реализован в PR #179 и остаётся каноническим идентификатором до merge и нового чтения resulting `main`.**

Граница шага:

1. Не начинать detector/runtime integration до merge PR #179.
2. После merge заново прочитать binding sources и оба state-файла с resulting `main`.
3. Проверить фактический merged diff, review findings и CI exact final head SHA.
4. Только после этого владелец продукта может явно выбрать первый bounded detector integration slice и обновить `next_step_id` в отдельном PR.
5. До post-merge выбора не добавлять detector orchestration, renderer/review-pack/Android/runtime integration, OCR, pixel classifier, dependencies, external APIs или реальные данные.

## 12. Правила работы и восстановления новой сессии

Перед branch creation или изменением файлов новая сессия обязана:

1. Прочитать с base branch:
   - `AGENTS.md`;
   - `docs/ARCHITECTURE.md`;
   - `docs/CUSTOM_OCR_PIPELINE.md`;
   - `docs/OCR_PROJECT_STATE.md`;
   - `docs/OCR_PROJECT_STATE.json`.
2. Проверить, что Markdown и JSON state согласованы.
3. Прочитать component contracts только изменяемого компонента.
4. Проверить актуальный `main`, существующие PR/branches и отсутствие пересекающейся работы.
5. Опубликовать ровно один Context Gate v1 JSON с точным `allowed_paths`.
6. Выполнить только текущий `next_step_id` либо явно разрешённое владельцем ограниченное исключение.
7. Открыть PR draft, получить номер, затем обновить оба state-файла этим номером.
8. До ready-for-review проверить фактический diff, tests/validation, state continuity и отсутствие undeclared paths.
9. Не включать auto-merge.

Подробная последовательность Codex execution, final-SHA evidence, bounded failure loop, repository hygiene, truthful dispatch и независимый PR-аудит определены в `docs/CODEX_WORKFLOW.md`.

## 13. Cold-start continuity audit

Каждые 3–5 слитых privacy/OCR PR проводится repository-only cold-start audit.

Audit 2026-08-04 после merge PR #176:

- exact base `3f0d5453f256a0fd8e7cddb1c448a7bbbfb5a84f`, merged PR #173–#176, их Context Gate paths, merge ancestry, final-head OCR workflow runs, binding sources, evidence implementations/tests и actual baseline/renderer/builder/Android/runtime entrypoints проверены; open PR до audit отсутствовал;
- Markdown/JSON state, architecture и privacy boundary согласованы; evidence chain остаётся reference-only, а `104/104` focused, `177/177` mandatory OCR и `449/449` full repository tests проходят;
- обнаружен blocking direct-match integrity defect: negative, boolean или reversed `DirectValueMatch.start/end` игнорируются direct-value adapter и могут авторизовать `auto_mask` при valid class/detector/geometry;
- verdict: `BLOCKING DIRECT-MATCH INTEGRITY DEFECT`; implementation не исправляется в audit PR #177;
- selected next step: `pii-direct-value-match-integrity-v1`; detector/renderer/runtime integration и real privacy metrics остаются последующими blockers.

Audit 2026-08-03 после merge PR #171:

- exact base `a95a69101af468f955714e3549ab153ada700be3`, merged PR #168–#171, их merge ancestry, changed paths, final-head OCR workflow runs, binding sources, evidence implementation/tests и actual baseline/renderer/builder/Android/Streamlit entrypoints проверены; open PR до начала работы отсутствовал;
- architecture/privacy boundary и Markdown/JSON state согласованы, evidence chain остаётся reference-only и не интегрирована в baseline, renderer, review pack, Android или runtime;
- обнаружен blocking semantic class-binding defect: syntactically valid strong evidence с matching geometry может дать `auto_mask` для incompatible `proposed_class`, а unapproved direct-value detector ID не отклоняется;
- verdict: `BLOCKING CONSISTENCY DEFECT`; доказанные synthetic/schema свойства отделены от unproved real recall, mask coverage, over-redaction, pixel classification, production safety, Android automasking, external OCR, generalization и human pilot;
- selected next step: `pii-evidence-class-compatibility-v1`; implementation correction не входит в audit PR #172.

Audit 2026-08-03 после merge PR #166:

- прочитаны обязательные repository sources и implementation entrypoints с актуального `main`, отдельно проверены merged PR #160–#166 и отсутствие overlapping open PR;
- Markdown/JSON state согласованы, active architecture и privacy boundary восстанавливаются однозначно, а operational next step остаётся `pii-direct-pattern-evidence-v0`;
- PR #166 schema, focused tests и OCR workflow entry присутствуют и подтверждают fail-closed запрет weak-layout-only `auto_mask`, но schema ещё не интегрирована в baseline, renderer, review pack, Android или runtime;
- component table синхронизирована с существующей reference schema; proven/unproven properties и remaining blockers разделены без production, Android automasking, privacy-safety, human-pilot, external-handoff или cross-contract claims;
- verdict: `PASS WITH BLOCKERS`; blockers — следующие evidence detector slices, integration и последующая real/generalization/privacy evaluation, а не repository-state conflict.

Audit 2026-08-02 после merge PR #158:

- прочитаны все пять binding sources с актуального `main`;
- architecture, pipeline, state, Context Gate, Android package и automation entrypoints согласованы;
- результаты PR #158 подтверждены тестами, release build, install и Samsung A55 smoke;
- найдено только отставание state от фактической device-проверки, исправленное PR #159;
- визуально подтверждён measurement blocker: текущие маски чрезмерно закрывают юридический текст, но источник расширения ещё не измерен;
- verdict: `PASS WITH ONE MEASUREMENT BLOCKER`.

Audit 2026-07-29 после merge PR #154:

- прочитаны все пять binding sources с актуального `main` без использования истории чата как источника состояния;
- current privacy architecture и `controlled-pii-reviewer-pilot-v0` восстановлены однозначно;
- Markdown/JSON state, PR template, trusted workflow и Context Gate validator согласованы;
- фактические builder CLI, Android package identity и automation entrypoints соответствуют state;
- доказанные и недоказанные свойства detector, renderer, Android reviewer и development automation разделены корректно;
- blocking repository conflicts и новые product blockers не найдены;
- verdict: `PASS`; единственный product blocker остаётся controlled human pilot.

Предыдущий audit 2026-07-26 после merge PR #148 завершился `PASS WITH ONE OPERATIONAL BLOCKER`; PR #149 закрыл найденное отсутствие one-command review-pack builder.

Следующий cold-start audit требуется после следующих 3–5 слитых privacy/OCR PR либо раньше при конфликте binding documents.

## 14. Формат передачи ограниченной задачи Codex

Полный обязательный task packet и execution order определены в `docs/CODEX_WORKFLOW.md`.

Минимальный каркас:

```text
Repository/base: <repo and current main SHA>.
Sources of truth: AGENTS.md + docs/ARCHITECTURE.md + docs/CUSTOM_OCR_PIPELINE.md + both state files.
Current state: <active_track and next_step_id read from main>.
Measurable change: <one bounded result>.
Context Gate: <one exact JSON object>.
Allowed paths: <complete exact list>.
Forbidden: <scope, dependencies, privacy, external services, adjacent systems>.
Validation: <focused commands + final checks on final head SHA>.
Failure policy: <bounded correction loop + blockers>.
Ready criteria: draft PR → state update → final-SHA checks → diff audit → Ready without merge/auto-merge.
```
