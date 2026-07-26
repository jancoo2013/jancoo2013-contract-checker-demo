# OCR Project State & Continuity v0

Последнее обновление: 2026-07-26, PR #148, `state-process-alignment-v0`.

Активный трек: `local-pii-redaction`.

Единственный следующий шаг: `controlled-pii-reviewer-pilot-v0`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Архитектуру задают `docs/ARCHITECTURE.md` и `docs/CUSTOM_OCR_PIPELINE.md`; точные входы, выходы и proof boundaries отдельных компонентов задают их component contracts. При конфликте обязательных документов работа останавливается до отдельного исправления.

## 1. Изменение PR #148

- `AGENTS.md` и `.github/pull_request_template.md` приведены к фактически действующему Context Gate v1: один JSON-блок с `context_gate_version`, `change` и точным `allowed_paths`.
- Зафиксирован фактический synthetic Android smoke после PR #146.
- Владелец продукта принял emulator smoke как достаточный для перехода к human pilot и явно отложил повторный ручной synthetic smoke на Samsung A55.
- Следующий шаг изменён с `android-reviewer-device-pilot-v0` на `controlled-pii-reviewer-pilot-v0`.
- Runtime, APK, detector, renderer, зависимости, OCR, Gemini, внешние API и правила обработки данных не изменены.

## 2. Цель продукта и privacy boundary

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

## 3. Реальное состояние компонентов

| Компонент | Состояние | Доказано | Не доказано |
|---|---|---|---|
| Page boundary + normalization | Python reference v0 | Ограниченный preview, accepted quad/null fallback, bounded grayscale master, hashes и synthetic/fixture tests | Android memory implementation и production capture quality |
| Line segmentation | Python reference v0 | Детерминированные line regions, QA overlays, foreground accounting и fail-closed reasons | PII-классификация и general accuracy |
| Local PII annotation contract | Reference v0 | Closed classes/statuses, immutable image identity, bbox/polygon validation | Human annotations и privacy metrics |
| Local PII detector | `marker_layout_baseline_v0` | Детерминированные candidates без OCR, cloud calls или ground-truth leakage | Реальные recall, complete coverage и over-redaction |
| Local mask renderer | Python reference v0 | Новый grayscale PNG, физическая замена candidate pixels, metadata stripping, deterministic publication | Candidate correctness, Android behavior и production privacy safety |
| Reviewer manifest core | Reference v0 | Три closed finding categories, canonical geometry/JSONL и immutable hashes | Controlled human pilot |
| Android PII reviewer | Standalone Expo APK | Автономный запуск, pack selection/validation, source/masked switching после repaint, one-tap finding | First-paint source reliability, подтверждённая publication/readback результата, human pilot |
| Android detector/renderer | Не реализован | — | On-device automatic detection and masking |
| External OCR handoff | Не подключён | Разрешён только после privacy gate | Безопасность derivative не доказана |

## 4. Synthetic Android smoke: фактические результаты

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

- при первом показе source image иногда виден градиент до переключения вкладок; это неблокирующий UI/repaint defect;
- создание и чтение `review-<prediction_sha256>.jsonl` на компьютере фактически не подтверждено;
- полный synthetic pack smoke на Samsung A55 не выполнялся и отложен владельцем продукта;
- это не проверка Android automasking, PII recall или privacy safety.

Standalone launch на Samsung A55 ранее подтверждён, но дополнительные ручные перезагрузки APK/pack для synthetic smoke больше не являются обязательным gate перед controlled pilot.

## 5. Активный блокер

Единственный product blocker перед улучшением detector или Android-port — отсутствие controlled human pilot и измеримых ошибок текущего Python baseline:

- `missed_pii`;
- `incomplete_mask`;
- `over_redaction`.

До pilot нельзя утверждать, что current candidates корректны, маски полностью закрывают PII или сохраняют достаточно юридического текста.

## 6. Единственный следующий шаг

**`controlled-pii-reviewer-pilot-v0`: подготовить один repository-external controlled real-page review pack и провести ограниченную проверку человеком, читающим иврит, без внешних image/OCR/LLM calls.**

Граница шага:

1. Использовать локальные контролируемые страницы; реальные страницы, manifests и результаты не коммитить в GitHub.
2. Локально выполнить текущую цепочку:

```text
normalized pages
→ line segmentation
→ marker_layout_baseline_v0
→ grayscale_opaque_mask_v0
→ Android review pack
```

3. Проверяющий только выбирает одну из трёх категорий и касается строки/существующей маски. Он не транскрибирует текст, не вводит PII, не рисует bbox и не исправляет маски вручную.
4. Завершить все страницы и создать локальный `review-<prediction_sha256>.jsonl` без overwrite.
5. Проверить, что файл читается локальным Python reviewer core и связан с exact source/prediction/derivative hashes.
6. При невозможности сохранить или прочитать результат остановить pilot и оформить отдельный bounded corrective PR.
7. Не считать metrics и не менять detector в этом шаге. Следующий отдельный PR после успешного pilot — `local-pii-metrics-v0`.
8. Запрещены Gemini, Google Vision, cloud OCR, LLM image calls, production upload и любые PII values в GitHub/Airtable.

## 7. Правила работы и восстановления новой сессии

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

## 8. Cold-start continuity audit

Каждые 3–5 слитых privacy/OCR PR проводится repository-only cold-start audit. После merge PR #148 достигается порог трёх слитых PR после последнего независимого audit #144; следующий implementation PR нельзя переводить в ready-for-review без короткого cold-start audit.

Чистая сессия, имеющая только репозиторий, должна:

1. прочитать все пять binding sources;
2. без истории чата объяснить текущую privacy-архитектуру и single next step;
3. отличить доказанное от недоказанного для detector, renderer и Android reviewer;
4. проверить state Markdown/JSON и Context Gate template/validator alignment;
5. запустить применимые repository checks либо объяснить, почему для docs-only состояния application tests не нужны;
6. перечислить blocking findings с точными файлами и не менять код;
7. записать итог audit в следующий privacy/OCR state update.

Исторические audit-отчёты и PR-подробности доступны через Git history; в этом файле сохраняются только действующий протокол и текущие выводы.

## 9. Формат передачи ограниченной задачи Codex

```text
Источник истины: AGENTS.md + docs/ARCHITECTURE.md + docs/CUSTOM_OCR_PIPELINE.md + оба state-файла.
Задача: <один ограниченный шаг>.
Разрешено менять: <точный список файлов>.
Запрещено: <detours, production integrations, external APIs, data>.
Проверка: <точные tests/local smoke>.
Готовность: draft PR → state update → diff/validation review → ready without auto-merge.
```
