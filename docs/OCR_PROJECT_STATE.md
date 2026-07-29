# OCR Project State & Continuity v0

Последнее обновление: 2026-07-29, PR #152, `android-dev-build-v0`.

Активный трек: `local-pii-redaction`.

Единственный следующий шаг: `controlled-pii-reviewer-pilot-v0`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Архитектуру задают `docs/ARCHITECTURE.md` и `docs/CUSTOM_OCR_PIPELINE.md`; точные входы, выходы и proof boundaries отдельных компонентов задают их component contracts. При конфликте обязательных документов работа останавливается до отдельного исправления.

## 0. Изменение PR #152

- По прямому запросу владельца продукта как ограниченное process exception команда `tools/android-dev.ps1` расширена режимом `build` для локальной standalone release-сборки Android APK.
- Build-preflight повторно использует проверки проекта, Expo dependencies, Node.js, JDK 17 и Android SDK, но не требует подключённого телефона; failure останавливает сборку до Expo/Gradle.
- После успешного preflight выполняются `expo prebuild --clean` и Gradle `assembleRelease`; результат публикуется локально как `mobile/pii-reviewer/build-artifact/PII-Pilot-V2.apk` с SHA-256.
- Первый Windows-run подтвердил корректную блокировку Java 21. После временного переключения на Temurin JDK 17 preflight прошёл с итогом `9 passed, 2 warnings, 0 failures`.
- Первая Gradle-попытка выявила, что найденный по стандартному пути Android SDK не передавался Gradle при незаданном `ANDROID_HOME`; исправление создаёт локальный generated `android/local.properties` с `sdk.dir` после prebuild, не меняя системные переменные и не печатая абсолютный путь.
- Generated `mobile/pii-reviewer/android/` и `mobile/pii-reviewer/build-artifact/` исключены из Git. Raw build logs остаются только локально при failure и могут содержать локальные пути.
- После SDK-fix локальная release-сборка на Windows с Temurin JDK 17 успешно завершилась строкой `BUILD READY`; создан `PII-Pilot-V2.apk` с SHA-256 `d50b00b479b8baee7ecd7ef7af09aacae1e5ec162264968cae9f32010639c557`.
- Runtime приложения, privacy boundary, detector/renderer, OCR, зависимости, внешние API, `active_track` и `next_step_id` не меняются.

## 1. Изменение PR #151

- По прямому запросу владельца продукта как ограниченное process exception добавлена read-only команда `tools/android-dev.ps1 doctor` для предварительной диагностики локальной Windows/Android/Expo-среды.
- Команда проверяет расположение mobile-проекта, `package.json`, `app.json`, актуальный Android package, Node.js/npm/npx, JDK 17, `JAVA_HOME`, Android SDK, `ANDROID_HOME`, adb, подключённые устройства, Expo dependencies и наличие Gradle wrapper.
- Скрипт не запускает Metro, Gradle или приложение, не устанавливает APK, не изменяет файлы проекта и не читает договоры, изображения, review packs или PII.
- Серийные номера, модели и другие идентификаторы устройств из `adb devices -l` не выводятся; сохраняется только агрегированное количество готовых или заблокированных устройств.
- Критические ошибки дают exit code `1`; предупреждения о необязательном текущем состоянии, включая отсутствие подключённого устройства или `node_modules`, не считаются падением.
- Первый запуск в Windows PowerShell 5.1 выявил terminating `NativeCommandError` на штатном stderr `java -version`; исправление через `System.Diagnostics.Process` подтверждено повторным полным запуском.
- Повторный запуск выдал итог `9 passed, 2 warnings, 1 failure`: корректно обнаружены Node.js 24 как warning относительно CI Node 22, Java 21 как failure относительно JDK 17, незаданный `ANDROID_HOME` как warning и одно готовое Android-устройство без вывода его идентификаторов.
- Runtime приложения, privacy boundary, detector/renderer, OCR, зависимости, внешние API, `active_track` и `next_step_id` не меняются.

## 2. Изменение PR #150

- По прямому запросу владельца продукта добавлена отдельная Android pilot identity: launcher name `PII Pilot V2`, package ID `com.jancoo.piireviewerpilotv2`, version `0.1.1`, versionCode `2`.
- GitHub Actions собирает новый release APK через Gradle и публикует его как `PII-Pilot-V2.apk`; это отдельное приложение и оно не заменяет старый development build или прежний reviewer APK в эмуляторе.
- Ручная перепаковка существующего APK не считается допустимым build path: такой файл не прошёл Android certificate parsing и отброшен.
- Review-pack schema, detector, renderer, reviewer logic, privacy boundary, зависимости, внешние API и правила обработки данных не меняются.
- `active_track` и `next_step_id` не меняются; corrective PR только разблокирует проверку текущего controlled pilot в эмуляторе.

## 3. Изменение PR #149

- Добавлен `controlled_pii_review_pack_builder_v0`: одна локальная CLI-команда собирает Android review pack из уже нормализованных grayscale page masters.
- Builder последовательно запускает текущие line segmentation, `marker_layout_baseline_v0` и `grayscale_opaque_mask_v0`, копирует byte-identical source masters и проверяет итог существующим Python reviewer core.
- Final pack содержит только требуемые source, prediction, renderer и neutral-line artifacts; временный geometry-only annotation manifest и рабочие файлы не публикуются.
- Существующий output path не перезаписывается; failure очищает sibling staging и не оставляет частичный pack.
- Focused builder tests включены в обязательный `OCR research runtime`; GitHub Actions run #43 прошёл полностью.
- Repository-only cold-start audit после PR #148 завершён с вердиктом `PASS WITH ONE OPERATIONAL BLOCKER`: binding documents, state и Context Gate согласованы, а единственным найденным препятствием была ручная сборка review pack. PR #149 закрывает именно этот operational blocker.
- `active_track` и `next_step_id` не меняются: следующий шаг остаётся реальным controlled human pilot.
- Detector rules, renderer semantics, Android APK, зависимости, внешние API и правила обработки данных не изменены.

## 4. Цель продукта и privacy boundary

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

## 5. Реальное состояние компонентов

| Компонент | Состояние | Доказано | Не доказано |
|---|---|---|---|
| Page boundary + normalization | Python reference v0 | Ограниченный preview, accepted quad/null fallback, bounded grayscale master, hashes и synthetic/fixture tests | Android memory implementation и production capture quality |
| Line segmentation | Python reference v0 | Детерминированные line regions, QA overlays, foreground accounting и fail-closed reasons | PII-классификация и general accuracy |
| Local PII annotation contract | Reference v0 | Closed classes/statuses, immutable image identity, bbox/polygon validation | Human annotations и privacy metrics |
| Local PII detector | `marker_layout_baseline_v0` | Детерминированные candidates без OCR, cloud calls или ground-truth leakage | Реальные recall, complete coverage и over-redaction |
| Local mask renderer | Python reference v0 | Новый grayscale PNG, физическая замена candidate pixels, metadata stripping, deterministic publication | Candidate correctness, Android behavior и production privacy safety |
| Reviewer manifest core | Reference v0 | Три closed finding categories, canonical geometry/JSONL и immutable hashes | Controlled human pilot |
| Review pack builder | `controlled_pii_review_pack_builder_v0` | One-command local assembly, byte-identical sources, exact hashes/bindings, strict line manifest, no-overwrite publication и cleanup покрыты synthetic focused tests и CI | Прогон на реальном договоре и удобство фактической передачи pack |
| Android PII reviewer | Standalone Expo APK | Автономный запуск, pack selection/validation, source/masked switching после repaint, one-tap finding | First-paint source reliability, подтверждённая publication/readback результата, human pilot |
| Android development automation | `doctor` v0 + `build` v0 | Полный Windows PowerShell 5.1 doctor-run; Java 21 fail-closed preflight; Temurin JDK 17 preflight; SDK handoff; успешная локальная release-сборка и SHA-256 APK | `run`, `logs`, `restart` |
| Android detector/renderer | Не реализован | — | On-device automatic detection and masking |
| External OCR handoff | Не подключён | Разрешён только после privacy gate | Безопасность derivative не доказана |

## 6. Synthetic Android smoke: фактические результаты

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

## 7. Активный блокер и pilot input

Единственный product blocker перед metrics, улучшением detector или Android-port — отсутствие controlled human pilot и измеримых ошибок текущего Python baseline:

- `missed_pii`;
- `incomplete_mask`;
- `over_redaction`.

До pilot нельзя утверждать, что current candidates корректны, маски полностью закрывают PII или сохраняют достаточно юридического текста.

У владельца продукта есть repository-external трёхстраничный договор, в котором почти весь текст напечатан, а рукописными остаются только подписи. Он является предпочтительным первым pilot input: небольшой объём отделяет ошибки layout/digit/signature detection от сложностей массового рукописного текста. Сам договор, normalized pages, manifests, derivatives и review result не коммитятся в GitHub и не передаются внешним сервисам.

## 8. Единственный следующий шаг

**`controlled-pii-reviewer-pilot-v0`: локально подготовить review pack из трёхстраничного договора, провести ограниченную проверку человеком, читающим иврит, и подтвердить canonical review JSONL без внешних image/OCR/LLM calls.**

Граница шага:

1. Локально получить normalized grayscale pages существующим page-normalization reference pipeline.
2. Собрать pack одной командой:

```bash
python -m research.hebrew_contract_ocr.pii_review_pack_builder \
  --normalized-dir <normalized-pages-directory> \
  --output-dir <new-review-pack-directory>
```

3. Builder должен завершиться одной строкой `PACK READY`; при ошибке pilot не начинается.
4. Передать на Android только готовую repository-external pack directory.
5. Проверяющий только выбирает одну из трёх категорий и касается строки/существующей маски. Он не транскрибирует текст, не вводит PII, не рисует bbox и не исправляет маски вручную.
6. Завершить все страницы и создать локальный `review-<prediction_sha256>.jsonl` без overwrite.
7. Скопировать result обратно на компьютер и проверить его существующим Python reviewer core против exact source/prediction/derivative hashes.
8. При невозможности собрать pack, сохранить или прочитать result остановить pilot и оформить отдельный bounded corrective PR.
9. Не считать metrics и не менять detector в этом шаге. Следующий отдельный PR после успешного pilot — `local-pii-metrics-v0`.
10. Запрещены Gemini, Google Vision, cloud OCR, LLM image calls, production upload и любые PII values в GitHub/Airtable.

## 9. Правила работы и восстановления новой сессии

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

## 10. Cold-start continuity audit

Каждые 3–5 слитых privacy/OCR PR проводится repository-only cold-start audit.

Audit 2026-07-26 после merge PR #148:

- прочитаны все пять binding sources без использования истории чата;
- current privacy architecture и `controlled-pii-reviewer-pilot-v0` восстановлены однозначно;
- доказанные и недоказанные свойства detector, renderer и Android reviewer разделены корректно;
- Markdown/JSON state, PR template и Context Gate validator согласованы;
- blocking repository conflicts не найдены;
- найден один operational blocker: отсутствие repository-owned one-command review pack builder;
- PR #149 реализует и тестирует этот builder, не меняя product next step.

Следующий cold-start audit требуется после следующих 3–5 слитых privacy/OCR PR либо раньше при конфликте binding documents.

## 11. Формат передачи ограниченной задачи Codex

```text
Источник истины: AGENTS.md + docs/ARCHITECTURE.md + docs/CUSTOM_OCR_PIPELINE.md + оба state-файла.
Задача: <один ограниченный шаг>.
Разрешено менять: <точный список файлов>.
Запрещено: <detours, production integrations, external APIs, data>.
Проверка: <точные tests/local smoke>.
Готовность: draft PR → state update → diff/validation review → ready without auto-merge.
```
