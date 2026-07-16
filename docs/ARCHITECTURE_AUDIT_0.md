# Архитектурный аудит 0 и обязательный архитектурный контракт

**Проект:** Israeli Rental Contract Checker  
**Дата аудита:** 2026-07-16  
**Базовая ветка:** `main`  
**Базовый коммит:** `5dddb8d33900bf5ebf840ce218403923451cbe96`  
**Статус документа:** обязательный контракт для дальнейшей разработки

Открытый исследовательский PR #108 не входит в базовый снимок кода. Все правила этого документа применяются к нему и к любым последующим PR до слияния.

---

## 1. Цель аудита

Аудит 0 фиксирует не качество отдельных алгоритмов, а границы системы:

- список модулей;
- ответственность каждого модуля;
- допустимые зависимости;
- структуры входных и выходных данных;
- локальную и облачную зоны;
- жизненный цикл каждого типа данных;
- запрещённые операции.

Главный продуктовый инвариант:

> Исходные изображения договора, исходный OCR-текст и персональные данные не покидают устройство пользователя. В облако разрешено передавать только обезличенные структурированные факты и минимально необходимые обезличенные доказательные фрагменты текста.

Текущий репозиторий содержит рабочие прототипы и исследовательские мосты, которые этому целевому инварианту пока не полностью соответствуют. Они не должны автоматически считаться production-архитектурой.

---

## 2. Итог аудита

### Общая оценка

Текущая кодовая база уже имеет полезные архитектурные швы:

- FastAPI-адаптер отделён от обработчика;
- OCR-постобработка отделена от OCR-провайдера;
- юридический анализ отделён от проверки доказательств;
- Pydantic-схемы запрещают лишние поля;
- исследовательский код расположен отдельно от production-пакета;
- мобильный Tesseract OCR выполняется локально;
- выбранное пользователем изображение не передаётся существующим мобильным transport-тестом.

Но до обработки реальных пользовательских договоров остаются блокирующие архитектурные расхождения.

### Блокирующие расхождения

1. **Текущий backend endpoint принимает PNG-страницы и передаёт их в Gemini OCR.** Даже если страницы предварительно замаскированы, это не соответствует целевой границе «изображения и OCR остаются на устройстве».
2. **`privacy_review_confirmed=true` является заявлением клиента, а не доказательством отсутствия PII.** Сервер проверяет формат и флаг, но не может подтвердить полноту маскирования.
3. **`privacy_assessment.py` считает страницу `redacted`, если существует хотя бы одна маска.** Одна маска не доказывает безопасность всей страницы; этот статус нельзя использовать как разрешение сетевой передачи.
4. **Выбранное изображение копируется в Android cache и явно не удаляется после OCR.** Оно удаляется только при следующем выборе изображения либо системной очистке cache.
5. **Tesseract model скачивается с изменяемого URL ветки `main` и проверяется только по размеру.** Требуется закреплённая версия и проверка SHA-256.
6. **Streamlit-прототип хранит чувствительные данные в `session_state`, включая изображения, OCR-текст, API-ключ и raw Gemini response.** Это допустимо только для закрытого исследования на синтетических/разрешённых данных, не для production.

### Высокие архитектурные риски

1. `app.py` объединяет UI, session state, секреты, OCR, маскирование, анализ и rendering. Это composition prototype, а не допустимый production-модуль.
2. `mobile/App.tsx` объединяет UI, native OCR lifecycle, скачивание модели, image picker, transport и runtime-валидацию API. Для исследовательского spike допустимо; перед пользовательским MVP необходимо разделение.
3. `gemini_engine.py` объединяет два разных cloud boundary: OCR изображений и юридический анализ текста, а также Streamlit cache.
4. API не имеет authentication/rate limiting и проверяет размер после multipart parsing. Публичное развёртывание без ingress-ограничений запрещено.
5. Evidence blocks содержат страницу и текст, но не содержат bbox/строковые координаты, OCR confidence, hash источника и версию преобразований.
6. Мобильный response DTO вручную дублирует backend schema, что создаёт риск незаметного расхождения контрактов.
7. In-memory Gemini analysis cache не имеет TTL и ограничения размера.

---

## 3. Текущие модули и их ответственность

### 3.1. UI и composition roots

| Модуль | Текущая ответственность | Статус |
|---|---|---|
| `app.py` | Streamlit UI, session state, ввод ключа, загрузка изображений, маскирование, OCR flow, анализ и rendering | Legacy/research prototype; запрещено расширять как production core |
| `mobile/App.tsx` | Android research UI, OCR model lifecycle, image picker, local OCR, synthetic backend transport test | Research composition root; требует декомпозиции перед real-user MVP |

### 3.2. Backend API

| Модуль | Ответственность |
|---|---|
| `contract_checker/api_app.py` | HTTP/FastAPI boundary, multipart parsing, request guards, safe HTTP errors, создание production handler |
| `contract_checker/api_models.py` | Версионированные API DTO и запрет лишних полей |
| `contract_checker/api_handler.py` | Оркестрация текущего cloud pipeline: page bytes → Gemini OCR → deterministic post-processing → Gemini analysis → response |

### 3.3. Подготовка изображения и privacy scaffold

| Модуль | Ответственность |
|---|---|
| `contract_checker/image_redaction.py` | Геометрические/manual маски и тестовые предложения строк; не является полноценным PII detector |
| `contract_checker/page_preparation.py` | Применение предоставленных масок и нормализация изображения в PNG; не принимает решение о безопасности экспорта |
| `contract_checker/privacy_assessment.py` | Черновая модель privacy-status; текущая логика недостаточна для production gate |

### 3.4. OCR и детерминированная постобработка

| Модуль | Ответственность |
|---|---|
| `mobile/modules/tesseract-ocr/*` | Android-only model download, image selection/cache copy, local Tesseract OCR |
| `contract_checker/gemini_engine.py` | Текущий временный Gemini OCR изображений и Gemini structured legal analysis |
| `contract_checker/ocr_pipeline.py` | Framework-agnostic OCR quality, повторное text redaction, validation и completeness audit |
| `contract_checker/ocr_quality.py` | Оценка качества OCR на уровне документа и страниц |
| `contract_checker/redaction.py` | Детерминированное удаление типовых PII из текста и безопасный отчёт только со счётчиками |
| `contract_checker/validator.py` | Проверка пригодности и полноты договорного текста |
| `contract_checker/completeness.py` | Поиск ссылок на отсутствующие/дополнительные документы и ограничения комплекта материалов |

### 3.5. Юридический анализ и доказательства

| Модуль | Ответственность |
|---|---|
| `contract_checker/evidence_blocks.py` | Детерминированное разбиение обезличенного текста на evidence blocks |
| `contract_checker/prompt_builder.py` | Формирование prompt на основании обезличенного текста/evidence blocks |
| `contract_checker/analysis_pipeline.py` | Gemini structured analysis + deterministic evidence validation |
| `contract_checker/schemas.py` | Строгие доменные схемы результата анализа |
| `contract_checker/output_validator.py` | Проверка evidence IDs, цитат, страниц и чисел; удаление/понижение неподтверждённых выводов |
| `contract_checker/config.py` | Загрузка server-side Gemini configuration |
| `contract_checker/cache_keys.py` | Детерминированные cache keys без хранения API-ключей |

### 3.6. Исследовательские модули

| Модуль | Ответственность | Ограничение |
|---|---|---|
| `research/handwriting_gate/*` | Dataset preparation, weak supervision, baseline/MIL/LOPO experiments | Никогда не импортируется production-кодом |
| `research/ocr_benchmark/*` | Локальный benchmark Surya/Chandra и нормализация результатов | Не является runtime dependency продукта |
| `tests/*` | Unit/integration/static contracts | Не содержит реальные договоры или PII fixtures |

---

## 4. Целевые production-модули

Следующие логические модули должны существовать как отдельные границы. Они не обязаны быть отдельным классом каждый, но не должны смешивать ответственность.

### 4.1. Локальная Android-зона

| Целевой модуль | Ответственность |
|---|---|
| `document_import` | Получение локального image/PDF URI без сетевой передачи |
| `image_normalization` | Rotation, resize, grayscale/contrast, удаление EXIF, нормализация страниц |
| `handwriting_gate` | Консервативный PASS/BLOCK/UNCERTAIN до анализа; uncertainty всегда блокирует |
| `pii_detection` | Локальные предложения PII-зон; не принимает окончательное решение без review |
| `mask_editor` | Ручное подтверждение, добавление и корректировка масок |
| `privacy_leak_check` | Независимая локальная проверка уже замаскированного результата |
| `local_ocr` | OCR только на устройстве; не знает о network/backend |
| `ocr_postprocess` | RTL normalization, page segmentation, confidence, deterministic cleanup |
| `local_redaction` | Повторное удаление PII из OCR-текста |
| `fact_extractor` | Извлечение дат, сумм, сроков, обеспечений и других простых фактов локально |
| `evidence_builder` | Создание минимальных обезличенных evidence fragments с provenance |
| `export_policy` | Единственная точка, которая может создать cloud-safe request |
| `network_client` | Принимает только тип `SanitizedAnalysisRequest`; не принимает bytes/URI изображений |
| `secure_session_store` | Управляет временными файлами, очисткой и optional encrypted local save |
| `mobile_ui` | Показывает состояние use cases; не вызывает OCR/provider напрямую |

### 4.2. Облачная зона

| Целевой модуль | Ответственность |
|---|---|
| `api_boundary` | Authentication, schema/version validation, size/count limits, safe errors |
| `sanitized_request_guard` | Reject любого поля/контента, не разрешённого cloud contract |
| `contract_fact_normalizer` | Нормализация обезличенных фактов и отношений |
| `contract_graph` | Сущности/отношения договора без PII |
| `rule_engine` | Детерминированные юридические/продуктовые правила |
| `retrieval` | Поиск релевантных норм/шаблонов без загрузки исходного договора |
| `llm_explainer` | Объяснение только на основании sanitized facts/evidence и rule results |
| `evidence_validator` | Проверка каждого вывода по evidence IDs и числам |
| `report_builder` | Формирование безопасного DTO результата |

---

## 5. Допустимые зависимости

### 5.1. Общие правила

1. Зависимости направлены сверху вниз и не образуют циклов.
2. Domain/deterministic модули не импортируют UI framework, FastAPI, Streamlit, React Native, Gemini SDK или Android APIs.
3. UI не содержит OCR, PII, legal rules или network payload assembly.
4. Provider adapters не принимают domain-объекты с raw PII.
5. Research code не импортируется из `contract_checker/`, `mobile/` production runtime или API startup.
6. Типы, пересекающие network boundary, определяются в одной версионированной схеме и валидируются с обеих сторон.

### 5.2. Разрешённое направление локальных зависимостей

```text
mobile_ui
  -> application/use_cases
      -> local privacy/OCR/fact interfaces
          -> native adapters
      -> export_policy
          -> shared sanitized DTO
              -> network_client
```

Запрещено:

```text
native OCR -> network_client
PII detector -> cloud provider
mobile_ui -> Gemini
network_client -> RawPageImage
```

### 5.3. Разрешённое направление backend-зависимостей

```text
api_boundary
  -> analysis_use_case
      -> sanitized_request_guard
      -> fact_normalizer / contract_graph / rule_engine
      -> llm_explainer adapter
      -> evidence_validator
      -> report_builder
```

Запрещено:

```text
LLM adapter -> FastAPI
rule_engine -> Gemini SDK
schemas/domain -> Streamlit
api_boundary -> image OCR provider
```

### 5.4. Допустимые зависимости существующих модулей

- `api_app.py` может зависеть от `api_models.py`, handler interface и safe exception types.
- `api_handler.py` может зависеть от framework-agnostic pipelines, но не от Streamlit.
- `ocr_pipeline.py` может зависеть только от deterministic quality/redaction/validation/completeness modules.
- `analysis_pipeline.py` может зависеть от provider interface, schemas и evidence validator.
- `output_validator.py` может зависеть от schemas и evidence blocks, но не от provider/UI.
- `page_preparation.py` не может принимать решение `safe_to_send`.
- `gemini_engine.py` должен быть разделён на OCR research adapter и legal-analysis adapter до production.

---

## 6. Структуры входных и выходных данных

Все boundary-структуры должны иметь `schema_version`. Не использовать неописанные `dict[str, Any]` между слоями production pipeline.

### 6.1. Локальные чувствительные типы

```text
RawPageImage
- page_id: random local UUID
- local_uri: app-private/local content URI
- bytes: image bytes
- width: int
- height: int
- exif_removed: bool
- sensitivity: RAW_PII
```

```text
NormalizedPageImage
- page_id
- bytes
- width
- height
- transform_metadata
- sensitivity: RAW_PII
```

```text
MaskRegion
- page_id
- bbox: x1, y1, x2, y2
- source: manual | detector
- category: name | id | phone | address | bank | signature | handwriting | unknown
- reviewed_by_user: bool
```

```text
LocalOcrPageResult
- page_id
- raw_text
- mean_confidence
- blocks: OCRBlock[]
- engine_version
- model_hash
- sensitivity: RAW_PII
```

### 6.2. Локальные обезличенные типы

```text
SanitizedEvidenceBlock
- block_id
- page_number
- sanitized_text
- source_bbox | source_line_range
- ocr_confidence
- source_page_hash
- redaction_version
- leak_check_status: PASS
```

```text
ExtractedFact
- fact_id
- type
- normalized_value
- original_sanitized_value
- evidence_block_ids[]
- confidence
- extractor_version
```

```text
SanitizedContractEnvelope
- schema_version
- local_contract_id: random, non-global
- facts[]
- selected_evidence_blocks[]
- page_count
- privacy_gate:
  - handwriting_status: PASS
  - leak_check_status: PASS
  - user_review_confirmed: true
  - detector_versions[]
- sensitivity: CLOUD_ALLOWED
```

### 6.3. Разрешённый cloud request

```text
SanitizedAnalysisRequest
- schema_version
- client_request_id: random request UUID
- locale
- facts[]
- evidence_blocks[]: только минимально необходимые обезличенные фрагменты
- requested_checks[]
```

В запросе отсутствуют:

- `image_bytes`;
- image/PDF URI;
- исходный OCR-текст;
- оригинальные filenames;
- EXIF;
- имя пользователя;
- device ID, advertising ID, phone number;
- API/provider key;
- подписи и рукописные изображения;
- полный договор, если для проверки достаточно выбранных evidence fragments.

### 6.4. Cloud response

```text
ContractAnalysisResponse
- schema_version
- request_id
- status
- normalized_facts[]
- rule_findings[]
- risks[]
- financial_hints[]
- unclear_items[]
- questions[]
- proposed_changes[]
- evidence_warnings[]
```

Каждый юридически значимый вывод обязан содержать `evidence_block_ids[]` либо иметь статус `unclear/unsupported`. Неподтверждённые красные и жёлтые риски не отображаются как установленные факты.

---

## 7. Локальная и облачная зоны

### Zone L0 — raw local sensitive

Содержит:

- фото/PDF;
- EXIF и оригинальные filenames до нормализации;
- подписи, рукописные вставки;
- raw OCR;
- PII detection candidates;
- API key пользователя, если закрытый тест всё ещё существует.

Правила:

- только устройство пользователя;
- app-private storage/cache;
- без telemetry, analytics, crash payload и backup;
- никогда не доступно network module.

### Zone L1 — local sanitized

Содержит:

- замаскированные изображения;
- обезличенный OCR-текст;
- факты;
- evidence blocks;
- privacy/leak-check reports.

Правила:

- замаскированное изображение всё равно считается локальным и не является cloud-safe автоматически;
- cloud-safe статус присваивает только `export_policy` после всех gates;
- сетевой request строится из фактов/фрагментов, а не из изображения.

### Zone C1 — application backend

Разрешено:

- `SanitizedAnalysisRequest`;
- random request ID;
- обезличенные факты и минимальные evidence fragments.

Запрещено:

- contract image/PDF;
- raw OCR;
- PII;
- original filename;
- persistent user/device fingerprint.

### Zone C2 — external LLM/provider

Разрешено передавать только ещё более минимальный subset Zone C1. Backend обязан исключать технические метаданные, не необходимые модели.

### Current research exception

Существующий `/v1/contracts/analyze-redacted` и Gemini image OCR являются временным research bridge. Для реальных пользовательских договоров этот путь должен быть отключён или удалён. Synthetic test asset разрешён, поскольку не содержит пользовательских данных.

---

## 8. Жизненный цикл данных

| Тип данных | Создание | Допустимое хранение | Удаление |
|---|---|---|---|
| Raw image/PDF | При выборе пользователем | Только app-private temporary storage | Сразу после завершения локального OCR/санитизации, при замене документа, clear, logout/session end; не ждать следующего picker action |
| Original filename/EXIF | При импорте | Только до нормализации | Удалить/заменить немедленно |
| Normalized raw page | Локальная preprocessing | Только активная сессия | После создания sanitization artifacts |
| Mask definitions | Во время review | Активная сессия; optional encrypted local project | При удалении проекта/session clear |
| Redacted image | После маскирования | Локально до visual review | После local OCR либо при удалении проекта; не отправлять в cloud |
| Raw OCR text | После local OCR | RAM only, минимальное время | Сразу после создания sanitized text/facts; не логировать и не кешировать |
| Sanitized OCR text | После redaction/leak check | Локально; optional encrypted save | По команде пользователя/политике retention |
| Facts/evidence | После extraction | Локально; разрешены в cloud request при PASS | Cloud copy не сохранять после request completion, кроме явной документированной необходимости |
| API request body | При отправке | In-memory request scope | После ответа; не писать в access/application logs |
| LLM prompt/response | Во время анализа | Без app-level persistent cache по умолчанию | После evidence validation/report assembly |
| Analysis report | После ответа | Локально по выбору пользователя | По удалению проекта/данных |
| API key | Server secret store или закрытый test input | Никогда не в repo/mobile bundle/logs | Удаляется из session state при clear/end; rotation отдельно |
| OCR model | После verified download | App-private persistent files | При uninstall/model update; обновление только через pinned hash |
| Research images/datasets | Локальная research workstation | Только ignored directories | По research retention policy; никогда не commit |

### Обязательная очистка Android cache

`mobile/modules/tesseract-ocr` должен предоставлять явный `clearSelectedImageAsync()` или эквивалент. OCR use case должен удалять временный файл в `finally`, когда preview/retry больше не нужны. Системная очистка cache не считается достаточным lifecycle control.

### Обязательная политика cache

- Запрещён unbounded cache.
- Любой cache с sanitized content имеет TTL, max entries/max bytes и explicit clear.
- Raw image/raw OCR cache запрещён.
- Process-global cache не должен переживать user/session boundary без явной изоляции.

---

## 9. Запрещённые операции

Следующие операции запрещены архитектурно, а не только инструкцией в prompt.

### Privacy и сеть

1. Передавать raw или redacted contract image/PDF во внешний OCR/LLM для production user flow.
2. Определять cloud safety по наличию хотя бы одной маски.
3. Считать boolean `privacy_review_confirmed` достаточной защитой.
4. Создавать network function, принимающую `bytes`, `Blob`, URI или `RawPageImage` договора.
5. Передавать original filename, EXIF, device ID или advertising ID.
6. Логировать request body, OCR text, evidence text, PII, API keys или raw provider response.
7. Добавлять analytics/crash SDK без отдельного privacy audit его payload и defaults.
8. Хранить contract payload в server cache, queue, object storage, vector DB или backups без отдельного утверждённого решения.

### Код и зависимости

9. Вызывать Gemini/provider непосредственно из UI.
10. Импортировать Streamlit/FastAPI/React Native/Gemini SDK в domain/deterministic modules.
11. Импортировать `research/*` в production runtime.
12. Дублировать API DTO вручную без schema compatibility test.
13. Передавать между production слоями невалидированные `dict[str, Any]`, если структура пересекает boundary.
14. Добавлять новый network SDK, OCR SDK или storage SDK без проверки permissions, telemetry и data flow.
15. Скачивать OCR model с mutable branch URL без закреплённого hash/version.
16. Хранить provider/API keys в mobile env (`EXPO_PUBLIC_*`), JS bundle или репозитории.
17. Добавлять автоматический retry, который повторно отправляет contract payload без explicit policy/idempotency.

### Юридический вывод

18. Показывать red/yellow risk без проверяемого evidence block.
19. Выдавать отсутствие пункта как установленный риск, если загружен не полный договор/приложения.
20. Считать Structured Output доказательством истинности вывода.
21. Скрывать OCR uncertainty, handwriting uncertainty или conflicting clauses.
22. Отправлять в LLM больше текста, чем требуется конкретной проверке.
23. Сохранять PII в Contract Graph, vector index или training corpus.

### Работа ИИ с репозиторием

24. Добавлять модуль/зависимость без обновления этого документа, если меняется data flow или boundary.
25. Размещать новую бизнес-логику в `app.py` или `mobile/App.tsx`, кроме временного research UI с явной маркировкой.
26. Создавать альтернативную реализацию redaction/normalization/amount parsing внутри UI или provider adapter.
27. Обходить gate «BLOCK/UNCERTAIN» ради продолжения demo flow.

---

## 10. Решение по текущим компонентам

| Компонент | Решение |
|---|---|
| Streamlit text MVP | Оставить как закрытый legacy/research стенд; не считать production frontend |
| Streamlit image masking | Только тест геометрии на разрешённых данных; raw image доходит до Streamlit server, поэтому production запрещён |
| FastAPI `/analyze-redacted` image endpoint | Пометить research/deprecated; не подключать к real-user mobile flow |
| Gemini image OCR | Сохранить только для controlled benchmark/synthetic tests либо удалить после локального OCR решения |
| Android Tesseract module | Продолжать research; добавить pinned model hash, explicit cache deletion, typed OCR blocks/provenance |
| Deterministic text redaction | Сохранить как defense-in-depth после local OCR |
| OCR quality/validator/completeness | Сохранить как framework-agnostic domain services |
| Evidence validation | Сохранить и усилить coordinates/hash/confidence provenance |
| Contract Graph + rule engine | Добавлять после стабилизации local privacy/OCR pipeline и versioned sanitized DTO |
| Research handwriting/OCR harnesses | Сохранять изолированно; никакой runtime dependency |

---

## 11. Порядок исправления

### До следующего production vertical slice

1. Зафиксировать этот документ как архитектурный контракт.
2. Разделить research и production paths в названиях/README/UI.
3. Изменить privacy status: наличие маски не равно `redacted/safe`; нужен independent leak-check PASS.
4. Добавить explicit deletion lifecycle для выбранных Android images.
5. Закрепить Tesseract model URL/version и SHA-256.

### До отправки первого реального договора в backend

6. Запретить image payload в mobile network client типами и тестами.
7. Создать versioned `SanitizedContractEnvelope` и `SanitizedAnalysisRequest`.
8. Выполнять OCR, text redaction, fact extraction и evidence selection локально.
9. Создать новый backend endpoint только для sanitized facts/fragments.
10. Добавить authentication, ingress limits, rate limits и no-payload logging policy.

### До публичного тестирования

11. Разделить `mobile/App.tsx` на UI/use cases/adapters.
12. Разделить `gemini_engine.py` на отдельные provider adapters; image OCR не подключать к production path.
13. Добавить schema compatibility tests mobile ↔ backend.
14. Добавить privacy lifecycle tests: cache deletion, no image network calls, no PII logs.
15. Добавить threat model и dependency/permission audit.

---

## 12. Definition of Done для архитектурного PR

PR, меняющий pipeline, считается архитектурно допустимым только если:

- указан изменившийся data flow;
- перечислены новые типы данных и sensitivity class;
- доказано, что network boundary не получил raw/image тип;
- добавлены или обновлены boundary tests;
- не возникло reverse/cyclic dependency;
- описан lifecycle новых данных;
- проверены permissions, storage, logs и third-party SDK behavior;
- обновлён этот документ, если изменились модули, зависимости, зоны или запреты.

---

## 13. Минимальные автоматические архитектурные тесты

Следующие тесты должны появиться до real-user flow:

1. Static test: production mobile network code не содержит вызова с selected image URI/Blob/bytes.
2. Type test: `network_client.send()` принимает только `SanitizedAnalysisRequest`.
3. Integration test: selected image проходит local OCR, но network mock получает только facts/evidence.
4. Privacy test: raw filename, ID, phone, email и address отсутствуют в request serialization.
5. Lifecycle test: temporary selected image удалён после clear/success/failure.
6. Model integrity test: неправильный SHA-256 OCR model блокирует установку.
7. Gate test: `UNCERTAIN` и `HAND_MARK_PRESENT` блокируют export.
8. Schema test: mobile request/response совместимы с backend OpenAPI/Pydantic schema.
9. Logging test: exceptions не содержат key, OCR text, image path или provider raw response.
10. Evidence test: unsupported risk удаляется/понижается и не отображается как подтверждённый.

---

## 14. Архитектурный инвариант в одной строке

```text
Raw document -> local privacy gates -> local OCR -> local redaction/facts/evidence -> minimal sanitized request -> cloud rules/LLM explanation -> evidence-validated report
```

Любой путь, в котором изображение договора или raw OCR пересекают network boundary, является research-only и не может использоваться для production user data.
