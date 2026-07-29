# OCR Project State & Continuity v0

Последнее обновление: 2026-07-29, PR #156, `android-dev-restart-v0`.

Активный трек: `local-pii-redaction`.

Единственный следующий шаг: `controlled-pii-reviewer-pilot-v0`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Архитектуру задают `docs/ARCHITECTURE.md` и `docs/CUSTOM_OCR_PIPELINE.md`; точные входы, выходы и proof boundaries отдельных компонентов задают их component contracts. При конфликте обязательных документов работа останавливается до отдельного исправления.

## 0. Изменение PR #156

- По прямому запросу владельца продукта как ограниченное process exception команда `tools/android-dev.ps1` расширена режимом `restart`.
- `restart` читает актуальный package из `mobile/pii-reviewer/app.json`, требует ровно одно готовое adb-устройство и блокируется, если package не установлен.
- Команда выполняет `am force-stop`, подтверждает отсутствие процесса, запускает launcher без Metro и подтверждает новый процесс через `pidof`.
- Serial, model, PID и raw adb output не печатаются. APK не собирается и не устанавливается, данные приложения не очищаются, logcat не читается.
- Фактический Windows/Samsung A55 run завершён успешно: приложение остановилось и повторно открылось, команда дошла до `RESTART READY`.
- Runtime приложения, privacy boundary, detector/renderer, OCR, зависимости, внешние API, `active_track` и `next_step_id` не меняются.

## 1. Текущая цель и privacy boundary

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

## 2. Реальное состояние компонентов

| Компонент | Состояние | Доказано | Не доказано |
|---|---|---|---|
| Page boundary + normalization | Python reference v0 | Bounded grayscale master, hashes, synthetic/fixture tests | Android memory implementation и production capture quality |
| Line segmentation | Python reference v0 | Детерминированные regions, QA overlays, fail-closed reasons | PII-классификация и general accuracy |
| Local PII annotation contract | Reference v0 | Closed classes/statuses, immutable identity, geometry validation | Human annotations и privacy metrics |
| Local PII detector | `marker_layout_baseline_v0` | Deterministic candidates без OCR/cloud/ground-truth leakage | Реальные recall, complete coverage и over-redaction |
| Local mask renderer | Python reference v0 | Physical grayscale replacement, metadata stripping, deterministic publication | Candidate correctness, Android behavior и production privacy safety |
| Reviewer manifest core | Reference v0 | Три closed finding categories, canonical geometry/JSONL и hashes | Controlled human pilot |
| Review pack builder | `controlled_pii_review_pack_builder_v0` | One-command assembly, exact bindings, no-overwrite и cleanup покрыты tests/CI | Реальный трёхстраничный pack и фактическая передача |
| Android PII reviewer | Standalone Expo APK | Offline launch, pack validation, source/masked switching, one-tap finding | First-paint reliability, publication/readback result, human pilot |
| Android development automation | `doctor` + `build` + `run` + `logs` + `restart` v0 | Windows PowerShell 5.1 doctor; JDK 17 preflight; SDK handoff; release build; install/launch/process check; process-scoped logs; stop/start/process confirmation на Samsung A55 без Metro | Остаточный риск PII в произвольных error strings |
| Android detector/renderer | Не реализован | — | On-device automatic detection and masking |
| External OCR handoff | Не подключён | Разрешён только после privacy gate | Безопасность derivative не доказана |

## 3. Подтверждённая Android-автоматизация

- PR #151: `doctor` — read-only диагностика Windows/Android/Expo; идентификаторы устройств скрыты.
- PR #152: `build` — standalone release APK; успешная Windows-сборка с Temurin JDK 17, SHA-256 `d50b00b479b8baee7ecd7ef7af09aacae1e5ec162264968cae9f32010639c557`.
- PR #153: `run` — установка и запуск APK без Metro; подтверждено на Samsung A55.
- PR #154: `logs` — process-scoped warning/error snapshot с локальной редакцией чувствительных строк; подтверждено на Samsung A55.
- PR #156: `restart` — остановка, повторный launcher и process confirmation без install/build/data wipe; подтверждено на Samsung A55.

## 4. Synthetic Android smoke

Repository-external одностраничный synthetic pack без договора и PII подтвердил в Pixel 8 / Android 17 emulator:

- standalone APK устанавливается и запускается без Metro;
- pack schemas, paths, hashes, dimensions и bindings проходят validation;
- masked/source switching работает после repaint;
- one-tap finding создаёт finding и page status `fail`.

Оставшиеся ограничения:

- первый source paint иногда показывает градиент до переключения вкладок;
- создание и чтение `review-<prediction_sha256>.jsonl` на компьютере не подтверждено;
- полный synthetic pack smoke на Samsung A55 отложен;
- это не проверка Android automasking, PII recall или privacy safety.

## 5. Активный блокер и pilot input

Единственный product blocker перед metrics, улучшением detector или Android-port — отсутствие controlled human pilot и измеримых ошибок current Python baseline:

- `missed_pii`;
- `incomplete_mask`;
- `over_redaction`.

У владельца продукта есть repository-external трёхстраничный договор, в котором почти весь текст напечатан, а рукописными остаются только подписи. Договор, normalized pages, manifests, derivatives и review result не коммитятся в GitHub и не передаются внешним сервисам.

До pilot нельзя утверждать, что current candidates корректны, маски полностью закрывают PII или сохраняют достаточно юридического текста.

## 6. Единственный следующий шаг

**`controlled-pii-reviewer-pilot-v0`: локально подготовить review pack из трёхстраничного договора, провести ограниченную проверку человеком, читающим иврит, и подтвердить canonical review JSONL без внешних image/OCR/LLM calls.**

Граница шага:

1. Локально получить normalized grayscale pages существующим page-normalization reference pipeline.
2. Собрать pack одной командой:

```bash
python -m research.hebrew_contract_ocr.pii_review_pack_builder \
  --normalized-dir <normalized-pages-directory> \
  --output-dir <new-review-pack-directory>
```

3. Builder должен завершиться строкой `PACK READY`; при ошибке pilot не начинается.
4. Передать на Android только готовую repository-external pack directory.
5. Проверяющий выбирает одну из трёх категорий и касается строки/существующей маски; без транскрипции, ввода PII и ручного bbox.
6. Завершить страницы и создать локальный `review-<prediction_sha256>.jsonl` без overwrite.
7. Скопировать result обратно на компьютер и проверить существующим Python reviewer core против exact hashes.
8. При невозможности собрать pack, сохранить или прочитать result остановить pilot и оформить отдельный bounded corrective PR.
9. Не считать metrics и не менять detector в этом шаге. Следующий отдельный PR после успешного pilot — `local-pii-metrics-v0`.
10. Запрещены Gemini, Google Vision, cloud OCR, LLM image calls, production upload и любые PII values в GitHub/Airtable.

## 7. Recent continuity record

- PR #149 добавил one-command controlled review-pack builder и закрыл operational blocker предыдущего cold-start audit.
- PR #150 закрепил отдельную Android identity `com.jancoo.piireviewerpilotv2`.
- PR #155 зафиксировал repository-only cold-start audit после PR #149–#154 с вердиктом `PASS`.
- Новых repository blockers нет; единственный product blocker остаётся controlled human pilot.

## 8. Правила работы и восстановления

Перед branch creation или изменением файлов новая сессия обязана:

1. Прочитать с base branch `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md`, `docs/OCR_PROJECT_STATE.md`, `docs/OCR_PROJECT_STATE.json`.
2. Проверить согласованность Markdown/JSON state.
3. Прочитать component contracts только изменяемого компонента.
4. Проверить актуальный `main`, PR/branches и отсутствие пересекающейся работы.
5. Опубликовать один Context Gate v1 с точным `allowed_paths`.
6. Выполнить только `next_step_id` либо явно разрешённое ограниченное исключение.
7. Открыть draft PR, получить номер, затем обновить оба state-файла.
8. До Ready for review проверить diff, tests/validation, state continuity и undeclared paths.
9. Не включать auto-merge.

## 9. Cold-start continuity audit

Каждые 3–5 слитых privacy/OCR PR проводится repository-only cold-start audit.

Audit 2026-07-29 после merge PR #154:

- прочитаны все пять binding sources с актуального `main`;
- architecture, state, Context Gate, builder CLI, Android package identity и automation entrypoints согласованы;
- доказанные и недоказанные свойства разделены корректно;
- verdict: `PASS`;
- единственный product blocker — controlled human pilot.

Следующий cold-start audit требуется после следующих 3–5 слитых privacy/OCR PR либо раньше при конфликте binding documents.
