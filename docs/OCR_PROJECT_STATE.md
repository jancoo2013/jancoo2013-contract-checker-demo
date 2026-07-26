# OCR Project State & Continuity v1

Последнее обновление: 2026-07-26, PR #147 Current Project State v0.

Этот файл хранит только текущее operational-состояние privacy/OCR-направления. Общая картина продукта зафиксирована в `PROJECT_STATE.md`; privacy-инварианты — в `docs/CUSTOM_OCR_PIPELINE.md`; точные интерфейсы и ограничения — в компонентных контрактах.

История разработки и предыдущих аудитов доступна в Git history и PR. Она не дублируется здесь, чтобы новая рабочая сессия не загружала отменённые планы и устаревшие промежуточные решения.

## 0. Последнее изменение

### PR #147 — Current Project State v0

- Идентификатор: `current-project-state-v0`.
- Изменение: добавлен `PROJECT_STATE.md` — краткий снимок действующей цели, архитектуры, состояния OCR/mobile, границ MVP, блокеров и ближайшего порядка работы.
- Дополнительно: этот operational state сокращён до текущих решений и доказательств; история PR и аудитов остаётся в GitHub.
- Проверка: документ сопоставлен с `docs/CUSTOM_OCR_PIPELINE.md`, текущим состоянием компонентов и machine-readable state.
- Влияние: runtime, код, данные, зависимости, OCR, Gemini, внешние API, реальные договоры и PII не изменены.
- Active track: `local-pii-redaction` — без изменений.
- Следующий шаг: `android-reviewer-device-pilot-v0` — без изменений.

## 1. Текущее operational-состояние

```text
active_track: local-pii-redaction
next_step_id: android-reviewer-device-pilot-v0
production_external_image_handoff: blocked
full_local_ocr: paused_research
```

Цель активного направления — обнаруживать и необратимо маскировать PII на устройстве до любой внешней передачи, сохраняя юридически значимый не-PII контент.

Текущий сквозной путь:

```text
фотография страницы
→ локальная геометрическая предобработка
→ локальное обнаружение PII-областей
→ необратимые маски
→ fail-closed privacy validation
→ обезличенный derivative
→ внешний полный OCR
→ вторичная текстовая редакция PII
→ evidence blocks
→ юридический анализ
→ отчёт на русском
```

До завершения controlled human pilot и формальных privacy-метрик производные реальных пользовательских фотографий нельзя отправлять внешнему OCR или LLM.

## 2. Состояние активных компонентов

| Компонент | Состояние | Доказано | Не доказано |
|---|---|---|---|
| Page boundary + normalization | Python reference реализован | Bounded preview/master, safe full-frame fallback, no-upscale, hashes и synthetic/fixture tests | Production Android memory/quality |
| Line segmentation | Python reference, опциональный сигнал | Deterministic manifests, QA overlays, fail-closed geometry gates, atomic publication | PII classification или privacy recall |
| PII annotation contract | Реализован | Closed schemas, immutable identity, geometry, deterministic validation | Human-reviewed evaluation set |
| PII marker/layout baseline | Реализован | Deterministic candidate regions без ground-truth leakage | Достаточный recall на реальных договорах |
| PII mask renderer | Python reference реализован | Candidate pixels физически заменяются в новом grayscale PNG; metadata и reversible layers не переносятся | Полнота candidate boxes и production privacy safety |
| Reviewer manifest core | Реализован | Closed findings, exact provenance, deterministic atomic JSONL | Human pilot и privacy metrics |
| Android reviewer | Pack I/O + standalone APK реализованы | Schema/hash validation, source/masked UI, one-tap findings, CI APK build | Исправленный full device smoke, human pilot, production detector/renderer |
| External OCR handoff | Не подключён | Разрешён только после privacy gate | Безопасность derivative на реальных данных |
| Evidence/layout/legal integration | Не подключена end-to-end | Отдельные текстовые и архитектурные наработки существуют | Production image-to-report flow |

Успешный fixture smoke на одном договоре доказывает целостность pipeline, но не PII recall, generalization или production privacy safety.

## 3. Главный блокер

Главный блокер — отсутствие измеренной production privacy validation.

Пока отсутствуют:

- controlled human reviewer run;
- PII-region recall;
- complete-mask coverage;
- missed-sensitive-area rate;
- over-redaction rate;
- page-level privacy pass rate.

Один пропущенный идентификатор нарушает privacy boundary, поэтому визуально правдоподобные маски и высокая precision сами по себе недостаточны.

## 4. Единственный следующий шаг

**Build the corrected standalone reviewer APK and verify source/masked rendering with the safe one-page synthetic pack in the Android 17 emulator, then repeat the same bounded smoke on Samsung A55 without external image calls.**

Граница шага:

- использовать только repository-external synthetic pack без реальных договоров, текста или PII;
- собрать APK из актуального `main` после PR #146;
- проверить directory selection и pack validation;
- проверить корректное source rendering;
- проверить masked rendering и переключение source/masked;
- после emulator PASS повторить тот же smoke на Samsung A55;
- не запускать human pilot и не сохранять privacy findings;
- не добавлять OCR, Gemini, LLM, network image calls, production upload или Android detector/renderer port;
- фиксировать только PASS/FAIL и технические ошибки без contract text.

Другой privacy/OCR-шаг нельзя начинать без явного решения владельца продукта и синхронного обновления state-файлов.

## 5. Порядок после device smoke

```text
corrected synthetic device smoke
→ controlled human pilot
→ Local PII Detection & Redaction Metrics v0
→ решение: улучшать Python baseline или переносить detector/renderer на Android
→ подтверждение privacy gate
→ внешний OCR handoff
```

Каждый пункт выполняется отдельным ограниченным PR или явно обозначенным repository-external действием.

## 6. Paused recognizer research

Сохранены, но не входят в активный MVP milestone:

- synthetic Hebrew line generator;
- dataset/evaluation contracts;
- Gold candidate and review workflow;
- CTC logical/alignment-order contract;
- recognizer input adapter;
- post-resize и batch memory bounds;
- isolated CPU training runtime.

Отсутствуют neural model, training loop, weights, подтверждённый full-line Gold Set, held-out CER и Android recognizer integration.

Возврат к полному локальному OCR требует отдельного продуктового решения и обновления `PROJECT_STATE.md`, `docs/CUSTOM_OCR_PIPELINE.md`, этого файла и machine-readable state в одном PR.

## 7. Восстановление новой рабочей сессии

До изменения файлов новая сессия должна:

1. Прочитать `AGENTS.md`.
2. Прочитать `PROJECT_STATE.md`.
3. Прочитать `docs/OCR_PROJECT_STATE.json` и этот файл.
4. Для privacy/OCR-задачи прочитать `docs/CUSTOM_OCR_PIPELINE.md`.
5. Читать только контракты компонентов, входящих в scope задачи.
6. Проверить актуальный `main` и открытые PR.
7. Опубликовать один JSON Context Gate:

```json
{
  "context_gate_version": 1,
  "change": "lowercase-kebab-case",
  "allowed_paths": ["exact/path"]
}
```

8. Реализовать только текущий next step либо явно разрешённое исключение.
9. Открыть PR как draft, получить номер и обновить оба state-файла.
10. Проверить diff и validation до ready-for-review.

## 8. Базовые проверки

Для Python-изменений, когда применимо:

```bash
python -m py_compile app.py contract_checker/*.py research/hebrew_contract_ocr/*.py
python -m unittest discover -s tests
```

Для Android reviewer:

```bash
cd mobile/pii-reviewer
npm install
npm test
```

Build/device smoke и repository-external data проверки описываются в компонентном handoff-документе и PR.

## 9. Правило обновления состояния

Каждый PR до ready-for-review обязан изменить:

- `docs/OCR_PROJECT_STATE.md`;
- `docs/OCR_PROJECT_STATE.json`.

Machine-readable state должен:

- увеличить `state_version`;
- записать текущий `last_recorded_pr`;
- записать тот же `last_recorded_change`, что указан в Context Gate;
- сохранить `active_track` и `next_step_id`, если владелец продукта явно не менял направление.

Context Gate проверяет точный набор изменённых файлов и структурную непрерывность state. Он не заменяет тесты, diff review и технический аудит.

Запрещено объявлять качество или production-готовность без воспроизводимой метрики и явно указанной proof boundary.
