# OCR Project State & Continuity v0

Последнее обновление: 2026-07-22, PR #142 Android Reviewer APK Artifact v0.

Это каноническая точка восстановления текущего privacy/OCR-проекта. Она отвечает на практические вопросы: что уже сделано, что действительно проверено, что пока только предполагается и какой шаг разрешён следующим.

Архитектурные решения задают `docs/ARCHITECTURE.md` и `docs/CUSTOM_OCR_PIPELINE.md`. Компонентные контракты задают точные входы, выходы и ограничения. Если этот файл расходится с ними, нельзя молча выбирать удобную версию: рабочая сессия должна остановиться, описать конфликт и исправить документы отдельным небольшим PR.

## 0. Последнее изменение

### PR #142 — Android Reviewer APK Artifact v0

- Идентификатор: `android-reviewer-apk-artifact-v0`.
- Изменение: workflow `Mobile reviewer` теперь выполняет native Expo prebuild, Gradle `assembleDebug`, создаёт installable APK и `build-identity.json`, а `DEVICE_PILOT_V0.md` фиксирует проверку артефакта, установку на Samsung A55 и offline device-smoke boundary.
- Проверено: GitHub Actions `Mobile reviewer` run #12 полностью прошёл; Node tests, Expo export, native prebuild, Gradle APK build, identity generation и artifact upload завершились успешно. Скачанный artifact содержал APK размером 163124456 bytes; вычисленный SHA-256 `430c4eeb9d2a701ae435345fbe9ae1239fa40fd391a6ab22598bd0798aee6948` совпал с `build-identity.json`.
- Осталось: после merge нужно использовать artifact из `main`, установить APK на Samsung A55, выполнить offline device smoke и repository-external human pilot; PR artifact привязан к синтетическому pull-request merge SHA и не является финальным pilot build.
- Влияние: поведение приложения, обработка данных, OCR, Gemini image calls, зависимости приложения, внешние API и реальные договоры не изменены; изменены CI-сборка и operational documentation.
- Следующий шаг: `android-reviewer-device-pilot-v0` без изменений.

## 1. Цель продукта

Построить локальный privacy-компонент для фотографий израильских договоров аренды:

- обнаруживать области с личными и идентифицирующими данными;
- необратимо маскировать их на устройстве до любой внешней передачи;
- всегда маскировать адрес арендуемой квартиры как PII;
- сохранять суммы, сроки, номера пунктов и юридически значимый текст, если они не являются PII;
- передавать внешнему OCR/LLM только обезличенный derivative;
- измерять PII recall, полное покрытие масками и over-redaction, а не точность полного локального транскрипта.

Полный project-owned Hebrew OCR больше не является обязательным MVP-компонентом. Существующие recognizer/CTC/Gold/CER наработки сохранены как paused research и не удаляются.

## 2. Кто чем управляет

| Роль | Ответственность |
|---|---|
| Владелец продукта | Выбирает цель и приоритет, подтверждает смену направления, проверяет и сливает PR. Не обязан управлять рабочими сессиями Codex или заново пересказывать им историю проекта. |
| Оркестрирующий ассистент | Выбирает первый незавершённый разрешённый шаг, реализует его самостоятельно либо делегирует ограниченную часть Codex, проверяет diff и тесты, обновляет этот файл в каждом PR и объясняет результат владельцу продукта. |
| Рабочая сессия Codex | Опциональный исполнитель для сложной ограниченной задачи. Восстанавливает контекст только из репозитория, работает в выданных границах и не меняет продуктовую линию самостоятельно. |
| Репозиторий | Долговременная память проекта и источник истины. Решение, существующее только в чате или памяти одной сессии, считается незафиксированным. |

Если для работы нужна сессия Codex, её создание и ввод в контекст — обязанность оркестрирующего ассистента. Владелец продукта не должен вручную переносить контекст между сессиями.

## 3. Текущий сквозной путь

```text
фотография страницы
→ предложение границ листа или сохранение полного кадра
→ геометрическое выравнивание и ограничение разрешения
→ локальное обнаружение PII-областей
→ необратимые маски и fail-closed privacy validation
→ обезличенное изображение/документ
→ внешний полный OCR
→ вторичная текстовая редакция PII
→ evidence blocks
→ юридический анализ и отчёт на русском
```

До утверждения и проверки privacy-дизайна сырые пользовательские фотографии нельзя подключать к production-потоку. Это не запрещает локальные исследования на контролируемых, синтетических или редактированных данных.

## 4. Реальное состояние компонентов

| Компонент | Состояние | Что доказано | Что не доказано |
|---|---|---|---|
| Генератор синтетических строк | Реализован, paused research | Детерминированная генерация, точный synthetic ground truth, локальные шрифты и деградации покрыты кодом и тестами | Синтетика строк сама по себе не доказывает PII-region recall или качество на фотографиях |
| Локальный архив из 170 строк | Существует вне репозитория как `silver`, paused research | Кропы и предварительные подписи могут быть полезны для будущего recognizer research | Это не PII annotation set, не Gold Set и не источник privacy-метрик |
| Gold review workflow | Candidate freeze реализован, paused research | `freeze_gold_candidates.py` фиксирует high-resolution images и pilot/evaluation cohorts до predictions; model-assisted порядок задан `docs/MODEL_ASSISTED_GOLD_TESTING_V0.md` | Не требуется для текущего PII MVP; recognizer, APK, человеческая транскрипция и итоговый full-line Gold Set отсутствуют |
| Dataset & Evaluation Contract v0 | Реализован, paused research | Training builder, charset/CTC ID, split, leakage checks и CER покрыты тестами | Полный-line CER не измеряет безопасность PII-redaction; найденные Gold provenance/leakage defects нужно исправить только перед возможным возобновлением full-OCR track |
| Image Resolution Contract v0 | Реализован и переиспользуется | Зафиксированы preview 1800 px, master 2480×3508, ceiling 4096 px, line height 64 px, запрет искусственного upscale | Параметры ещё не подтверждены на PII detector/annotation workflow и Android memory implementation |
| Нормализатор страницы v0 | Реализован и переиспользуется | Из принятых четырёх углов строит ограниченный grayscale master и удаляет внешние пиксели; при явном fallback сохраняет полный кадр; единый scale не увеличивает ни одну измеренную сторону | Это Python reference, а не Android memory implementation; audit зафиксировал отдельный TOCTOU/atomicity debt |
| Детектор границ страницы v0 | Реализован и переиспользуется | Сомнительная граница не применяется: detector handoff явно выбирает принятый четырёхугольник или полный кадр; `frame_clipped`, mapping preview→source и QA-артефакты покрыты тестами | Один договор не доказывает production-качество; audit зафиксировал отдельный TOCTOU debt |
| Сегментация строк | Reference v0 реализован, опциональный сигнал | Детерминированный fail-closed CLI, atomic publication, manifests, хеши, QA overlays, foreground accounting, mask/table/redaction/ambiguity gates и synthetic tests реализованы | PII detector может использовать строки, зоны или гибрид; сегментация сама по себе не даёт PII-классификацию или mask recall |
| Собственный recognizer | Boundary v0 реализован, paused research | Input adapter, mixed-script CTC decoder/order contract, memory bounds и isolated CPU runtime покрыты focused tests | Neural model, training loop, веса и CER отсутствуют; CRNN больше не является текущим следующим шагом |
| Local PII annotation/evaluation contract | Reference v0 реализован | Непустой JSONL, closed enums, bbox/polygon geometry, strict image identity, single manifest snapshot, same-byte image hash/decode и deterministic report покрыты focused tests | Нет controlled human annotations, detector predictions или измеренных recall/coverage/over-redaction metrics; compressed-byte/pixel resource ceilings остаются отдельным debt |
| Local PII detector | Deterministic marker/layout baseline v0 реализован | Без OCR и ground-truth leakage предлагаются bounded candidate regions; manifest читается один раз, image bytes повторно проверяются при consumption, output детерминирован и сохраняет immutable page identity | Нет controlled recall/coverage/over-redaction metrics, Android implementation или production privacy result |
| Local PII mask renderer | Python reference v0 реализован в PR 135 | Все candidates физически заменяются значением `0` в новом grayscale PNG `L`; удаляются alpha/EXIF/ICC/text metadata; страницы потребляются последовательно; staging derivatives повторно проверяются по фактическим bytes, hashes, dimensions, mode и bbox coverage перед atomic publication; mutation/late/rename failures очищаются и допускают retry | Не доказаны PII recall, корректность candidate boxes, полнота privacy coverage, over-redaction, внешняя передача, Android behavior или production privacy safety; threat model ограничен process-controlled staging |
| Controlled PII reviewer manifest core | Reference v0 реализован | Core связывает exact source/prediction/derivative hashes, проверяет strict top-level и nested candidate schemas, принимает только closed findings `missed_pii`, `incomplete_mask`, `over_redaction` и canonical `xyxy_half_open` bbox, повторно проверяет source/derivative непосредственно перед публикацией и атомарно создаёт deterministic JSONL без перезаписи, PII values, свободного текста, reviewer identity или timestamps | Human pilot run ещё не выполнен; не получены recall, complete-mask-coverage, over-redaction или unsafe-page metrics |
| Android PII reviewer harness | Pack I/O v0 + CI APK artifact реализованы | Android pack binding и no-overwrite output покрыты tests; GitHub Actions run #12 успешно выполнил Expo native prebuild, Gradle `assembleDebug`, identity generation и artifact upload; APK SHA-256 независимо совпал с identity file | APK ещё не установлен на Samsung A55; не выполнены device smoke и real reviewer run; не доказаны Android automasking, PII recall, complete coverage, over-redaction или production privacy safety |
| Внешний OCR handoff | Не подключён | Разрешён только после локальной необратимой редакции и privacy validation | Не доказано, что derivative не содержит PII и не сохраняет восстанавливаемые пиксели |
| RTL/layout и структура пунктов | Не реализованы | Это downstream-задача после обезличенного OCR | Нет кода и измерений reading order |

Успешный локальный прогон preprocessing на текущем девятистраничном договоре является fixture smoke test, а не общей метрикой PII detection или privacy safety.

## 5. Активные блокеры и paused research

1. **Production privacy validation.** Renderer, reviewer-manifest core, Android Pack I/O и CI APK artifact реализованы, но установка на Samsung A55, device smoke и controlled human pilot отсутствуют; измеримые gates не получены. До reviewer run и metrics запрещено отправлять производные пользовательских фотографий внешнему OCR/LLM.

Full-line Gold Set, CER, CRNN, training loop и reviewer transcription APK больше не являются блокерами MVP. Они остаются paused research. Android privacy reviewer harness не является transcription APK: он записывает только геометрию трёх закрытых категорий ошибок и не сохраняет текст или значения PII.

## 6. Переиспользуемая preprocessing-база и paused recognizer research

Контракт `research/hebrew_contract_ocr/LINE_SEGMENTATION_V0.md` и reference-модуль `line_segmenter.py` реализуют Automatic Line Segmentation v0. CLI проверяет normalizer manifest, hashes, grayscale mode и размеры; отказывается перезаписывать непустой output; пишет line PNG, canonical `manifest.jsonl`, explicit `pages.jsonl`, `summary.json` и overlay каждой страницы.

Synthetic tests доказали ровно ограниченные gates v0: ожидаемое число обычных/heading/clause-number bands, top-to-bottom order, vertical IoU не ниже `0.90`, bboxes внутри страницы с положительной площадью, полное foreground accounting, одинаковые manifest bytes и line-image hashes при повторе, strict normalizer schema/type/status validation, exact consumed-byte provenance, decoded-header/pixel-limit checks before load, active Pillow bomb safety, cleanup после поздней ошибки с успешным retry в тот же output, separate geometric/final pass-review/fail propagation и fail-closed reasons для blank page, isolated speck, 6–7 px rule, insufficient/thin/near-edge geometry, close/merged lines, table, external mask, opaque redaction и edge crop. Сегментатор намеренно не объявляет PII или training eligibility.

Контролируемый fixture `different_lease_fullres_rectified_v0` повторно проверен на текущем коде: 9 исходных страниц и detector handoff SHA-256 `5614ea0515b581cf8b53a4cfbe968d6471907ab072ad4f5ac9d8d23ff759e84e`. Текущие normalization manifest и summary имеют SHA-256 `79bb32fa81d62c4a280130a6dba4c5261976a586466c8b2437a7142d69868e46` и `1e5283904b3b184ddcf023588f5b955b458279dce9cd4164168e285b60df3868`; segmentation manifest, page reports и summary — `3e3a395324b24d286a9759f33df29fee4cb944c5e3c8d29ef64dc0976a3d16c4`, `cc60991bcdabfc13feaa6f0cf18c0c9af3b11799f17fd514ea2515b1e5ca07cf` и `237296bafcd978af24e8b30ff70c47b7acfc7574c1dc349b69349585b9971dfe`. Два локальных сквозных прогона завершились без аварии и создали byte-identical normalization/segmentation manifests, summaries, page reports, 269 line images и 9/9 overlays. Получено 269 candidate regions: geometric и final counts совпали — 129 `accepted`, 64 `review`, 76 `reject`. Эти 129 строк прошли только зафиксированные segmentation/resolution gates и не объявлены PII-аннотациями или пригодными для обучения.

`CTC_TEXT_ORDER_V0.md`, `text_order.py`, `recognizer_input.py` и `ctc_decoder.py` разделяют logical Unicode и monotonic CTC alignment order. Standard CTC collapse выполняется до reorder. Поддерживаемый v0 transform обратим для whitespace-separated Hebrew/LTR tokens, сохраняет внутренний порядок digits/Latin и зеркалит парные скобки; чистые LTR lines остаются identity. Token с Hebrew и LTR strong characters без ASCII-space boundary блокируется как неподдерживаемый.

`RECOGNIZER_INPUT_MEMORY_V0.md` фиксирует двухпроходную подготовку: preflight проверяет source metadata и все resulting widths, вычисляет сумму resized arrays и padded tensor и блокирует batch выше 256 MiB до resize. Допустимая ширина 10,923 выведена из high-detail ceiling 4096 px, recognizer height 64 px и minimum accepted text band 24 px. Второй проход повторно проверяет source geometry перед materialization.

Эти recognizer-контракты остаются валидными исследовательскими артефактами, но не определяют текущий MVP milestone.

`PII_ANNOTATION_CONTRACT_V0.md` и `pii_annotations.py` фиксируют immutable page identity, closed PII classes, bbox/polygon annotations, explicit review states и deterministic validation report. Manifest читается и хешируется один раз; image SHA-256 и decode выполняются над одними bytes. Семь focused tests покрывают geometry boundaries, strict integer/enum types, non-empty manifest, duplicate IDs, path traversal/symlink escape, hash mismatch, snapshot mutation и evaluation readiness. Это доказывает только контракт и validator, не качество детектора.

`PII_BASELINE_V0.md` и `pii_baseline.py` реализуют детерминированный marker/layout baseline. Он использует parsed rows из одного validated manifest snapshot, не читает ground-truth regions для predictions, повторно потребляет каждое image как один byte snapshot и пишет canonical prediction JSONL с `xyxy_half_open` bbox. Пять focused tests покрывают byte-identical repeats, in-bounds candidates, `property_address`, signature/right-label/digit cues, no-ground-truth-leakage, manifest mutation и fail-closed input/output guards. Это baseline для будущего сравнения, а не доказательство privacy quality.

`PII_MASK_RENDERER_V0.md` и `pii_mask_renderer.py` реализуют corrected grayscale mask renderer v0. Он последовательно потребляет страницы, ограничивает manifest/source bytes и decoded pixels, создаёт новый PNG `L`, физически заменяет union всех candidate bbox значением `0`, не переносит alpha/EXIF/ICC/text metadata и публикует только полностью проверенный sibling staging directory. Шесть focused tests и отдельные mutation/multipage harnesses подтверждают exact `xyxy_half_open` coverage, order invariance, deterministic bytes, source immutability, derivative/source mutation detection, cleanup и retry после late/final-rename failures. Это доказывает только необратимую замену пикселей для supplied candidates в process-controlled staging threat model, а не качество detector или внешнюю безопасность.

`PII_REVIEWER_PILOT_V0.md` и `pii_reviewer_pilot.py` реализуют deterministic manifest core для Controlled PII Reviewer Validation Pilot v0. Core связывает exact baseline prediction SHA с source/derivative hashes, dimensions и strict top-level/nested candidate schemas, принимает только три closed error categories и canonical `xyxy_half_open` bbox, повторно проверяет фактические page bytes перед publication и атомарно создаёт deterministic JSONL без перезаписи, PII values или свободного текста. Восемь synthetic focused tests покрывают manifest binding, strict integer/nested candidate guards, path/hash/mode failures, closed statuses/categories, geometry bounds, immutable identities, canonical finding IDs, mutation before publication, output-race no-overwrite, deterministic output и cleanup. Это доказывает только формат и core; human validation ещё отсутствует.

`mobile/pii-reviewer` задаёт Android-first Expo Development Build reviewer. Pack I/O v0 читает exact Python prediction/renderer contracts и neutral line-segmentation regions из выбранной локальной директории, проверяет closed schemas, IDs, paths, hashes, geometry, dimensions, grayscale derivative и page order. Verified image bytes копируются в app-private cache до отображения. Reviewer одним касанием выбирает neutral line или существующую mask geometry; результат сохраняется рядом с pack как canonical Python-compatible JSONL без overwrite.

## 7. Единственный следующий шаг

**Build and install a controlled Android reviewer APK, then run the repository-external human pilot on Samsung A55 without external image calls.** Другой privacy/OCR-шаг нельзя начинать без явного изменения этого файла и решения владельца продукта.

Граница задачи:

- собрать installable development APK из `mobile/pii-reviewer` и установить его на Samsung A55;
- подготовить repository-external review pack текущим Python baseline + renderer + line segmentation без помещения реальных страниц или PII в GitHub;
- проверить directory selection, page rendering, source/masked switching, one-tap target binding, navigation and no-overwrite result publication на устройстве;
- Hebrew-capable reviewer отмечает только `missed_pii`, `incomplete_mask`, `over_redaction` или page `pass`; он не транскрибирует, не рисует bbox и не исправляет маски;
- никаких OCR/Gemini/LLM/network image calls, production upload, Android detector/renderer port или privacy claims;
- зафиксировать APK build identity, prediction-manifest SHA-256, device/Android version, количество проверенных страниц и operational failures без PII values или contract text.

После controlled human pilot отдельный PR реализует Local PII Detection & Redaction Metrics v0. Только затем принимается решение: улучшать Python baseline или переносить detector/renderer на Android.

## 8. Протокол восстановления новой сессии

Новая рабочая сессия до изменения кода обязана:

1. Прочитать `AGENTS.md`.
2. Прочитать этот файл.
3. Прочитать `docs/ARCHITECTURE.md` и `docs/CUSTOM_OCR_PIPELINE.md`.
4. Прочитать контракты только тех компонентов, которых касается задача.
5. Проверить текущую ветку, незакоммиченные изменения и актуальный `origin/main`.
6. Опубликовать Context Gate с целью, разрешённым scope, входом, выходом, тестами, запрещёнными detours и SHA binding-документов.
7. Реализовать только раздел «Единственный следующий шаг» либо явно разрешённое владельцем продукта исключение.
8. Открыть PR как draft, получить его номер и обновить этим номером `docs/OCR_PROJECT_STATE.md` и `docs/OCR_PROJECT_STATE.json`.
9. Перевести PR в ready-for-review только после проверки согласованности state-файлов, diff и validation.

Оркестрирующий ассистент независимо проверяет результат. Нельзя принимать формулировку «готово» без просмотра diff и отчёта тестов.

Каждые 3–5 слитых privacy/OCR PR проводится cold-start audit: чистая сессия, которой доступен только репозиторий, должна корректно объяснить архитектуру и состояние, запустить проверки и назвать следующий шаг.

Первый cold-start audit проведён 2026-07-19 до публикации этого файла. Чистая сессия правильно восстановила архитектуру, уровни доказательности, два блокера и Automatic Line Segmentation v0. Найденные ею пробелы в идентификации локального fixture и измеримых gates были исправлены до коммита.

Второй repository continuity audit проведён 2026-07-20 после PR 117–121. Он выявил устаревшее fixture evidence после изменения no-upscale, конфликт full-frame fallback в Image Resolution Contract и неверный per-page `crop_policy`; PR 122 исправил эти связанные несогласованности. Audit также выявил высокий риск partial output: поздняя ошибка сегментатора оставляла уже записанные кропы и блокировала retry. Риск исправлен через sibling staging, cleanup при ошибке и публикацию только полностью собранного результата. Audit состоялся после пяти слитых OCR PR, то есть на два PR позже более строгого локального срока «не позднее третьего»; это зафиксировано как процессная ошибка.

Третий cold-start continuity audit проведён 2026-07-20 после PR 123–128. Он подтвердил candidate freeze, recognizer input boundary и isolated CPU runtime, но выявил blocking global RTL reversal, отсутствие post-resize/batch memory bounds, неполный OCR test command в CI, stale candidate-freeze documentation, несовместимые reviewer/materializer status names и отсутствие гарантии mixed-script строки в pilot. PR 129 устранил stale state, старый low-resolution Gold path и status mapping; следующие corrective PR устранили global RTL reversal и post-resize/batch memory risk через bounded CTC Text Order Contract v0 и Recognizer Input Memory Contract v0.

Четвёртый технический аудит проведён 2026-07-21 после PR 131. Он выявил документационный конфликт, Gold/CER leakage/provenance defects, узкий OCR CI и несколько отдельных atomicity/TOCTOU risks. После этого владелец продукта уточнил архитектурную цель: локальная система нужна для PII-redaction, а не для полного OCR. PR 132 зафиксировал этот продуктовый переход; recognizer-specific findings сохраняются как paused research debt, а не как MVP blocker.

Пятый repository-based technical continuity audit проведён 2026-07-21 после PR 132–134 и на draft PR 135. Он восстановил правильную privacy-архитектуру, но выявил empty-manifest incompatibility, повторное чтение annotation manifest, split image hash/decode snapshot и blocking renderer publication/resource defects. PR 136 закрыл upstream manifest/image findings; corrected head PR 135 закрыл renderer publication TOCTOU, multi-page memory и основные adversarial-test findings.

Шестой repository-based technical audit проведён 2026-07-21 на head `1e4540494bb095aa0e908c853f2c59885697dcfc`. Вердикт: `PASS WITH NON-BLOCKING FINDINGS`. `py_compile` и 6/6 renderer tests прошли; focused suite дал 27 успешных tests и один Windows-only symlink privilege error; full suite дал 310 успешных, 2 skipped и тот же environment error; GitHub Actions run 24 прошёл. Независимые derivative-swap и multipage harnesses подтвердили mutation detection, cleanup/retry, опубликованный SHA и освобождение page payload. Не доказаны PII recall, candidate correctness, complete privacy coverage, over-redaction, external-transfer safety, Android behavior и production privacy safety.

Этот шестой аудит выполнен в существующем рабочем чате. Владелец продукта явно принял repository-based audit как достаточный, после чего PR 135 был переведён в ready-for-review и слит. Технических блокеров renderer не осталось.

После merge PR 137 владелец продукта исправил ошибочное desktop-направление: reviewer должен быть Android-first, а не Streamlit/localhost. В ходе review PR 138 также удалено ручное построение bbox: проверяющий только сообщает тип ошибки и приблизительное место, а геометрию выбирает система из neutral line-segmentation regions или существующих масок. Scaffold не считается real-device validation до сборки и установки APK.

## 9. Формат передачи ограниченной задачи Codex

Codex используется только когда ограниченная задача действительно выигрывает от отдельной рабочей сессии. Формат передачи:

```text
Источник истины: AGENTS.md + docs/OCR_PROJECT_STATE.md.
Задача: <один ограниченный шаг>.
Вход: <точный формат, локальное расположение и проверенный dataset/manifest hash>.
Выход: <точный формат и расположение>.
Разрешено менять: <точный список файлов или компонентов>.
Запрещено: <detours, production-интеграции, внешние API, данные>.
Проверка: <тесты и локальный smoke>.
Готовность: draft PR → state update с номером PR → diff и validation review → ready-for-review без auto-merge.
```

## 10. Воспроизводимые команды

Установка и базовая проверка чистого checkout:

```bash
python -m pip install -r requirements.txt
python -m py_compile app.py contract_checker/*.py research/hebrew_contract_ocr/*.py
python -m unittest discover -s tests
```

Мобильный reviewer:

```bash
cd mobile/pii-reviewer
npm install
npm test
npm run android
```

Локальная подготовка полноразмерных страниц:

```bash
python -m research.hebrew_contract_ocr.page_boundary_detector \
  --input-dir /local/contract_pages \
  --output-dir research/hebrew_contract_ocr/generated/page_boundaries_v0

python -m research.hebrew_contract_ocr.page_normalizer \
  --input-dir /local/contract_pages \
  --corners-json research/hebrew_contract_ocr/generated/page_boundaries_v0/page_corners.json \
  --output-dir research/hebrew_contract_ocr/generated/normalized_pages_v0

python -m research.hebrew_contract_ocr.line_segmenter \
  --input-dir research/hebrew_contract_ocr/generated/normalized_pages_v0 \
  --output-dir research/hebrew_contract_ocr/generated/line_segmentation_v0
```

Для файлов с уже правильной матрицей пикселей и заведомо устаревшим EXIF orientation в обе команды добавляется `--ignore-exif-orientation`. Это нельзя включать по умолчанию.

Синтетические данные, legacy silver review pack, full-line Gold workflow, Gold materialization и CER остаются описаны в `research/hebrew_contract_ocr/README.md`, `docs/MODEL_ASSISTED_GOLD_TESTING_V0.md` и `research/hebrew_contract_ocr/DATASET_CONTRACT_V0.md` как paused recognizer research. CTC alignment/logical order зафиксирован в `research/hebrew_contract_ocr/CTC_TEXT_ORDER_V0.md`; recognizer memory ceilings — в `research/hebrew_contract_ocr/RECOGNIZER_INPUT_MEMORY_V0.md`. Local PII annotations определены в `research/hebrew_contract_ocr/PII_ANNOTATION_CONTRACT_V0.md`; deterministic baseline — в `research/hebrew_contract_ocr/PII_BASELINE_V0.md`.

## 11. Правило обновления состояния

Каждый PR без исключений обязан обновить этот файл и `docs/OCR_PROJECT_STATE.json` в той же ветке до перевода PR в ready-for-review. Это относится к code, documentation, process, audit, corrective и security PR, даже если активное направление, блокеры и следующий продуктовый шаг не изменились.

Минимальная запись для каждого PR:

- номер PR и дата;
- одна ограниченная цель и фактически изменённые компоненты/файлы;
- что проверено или доказано этим PR;
- что осталось недоказанным или не выполненным;
- влияние на runtime, данные, зависимости и внешние API;
- изменился ли `next_step_id`; если нет — это указывается явно.

`docs/OCR_PROJECT_STATE.json` для каждого PR обязан:

- получить новый `state_version`;
- записать текущий номер в `last_recorded_pr`;
- записать стабильный идентификатор изменения в `last_recorded_change`;
- сохранить `active_track` и `next_step_id`, если владелец продукта явно не изменил их.

Одновременно разрешён только один следующий шаг.

Запрещённые признаки потери управляемости:

- важный скрипт или датасет существует только на локальном компьютере без manifest/инструкции;
- константа качества не объяснена контрактом;
- две параллельные реализации выполняют один этап без явно выбранной канонической;
- PR одновременно меняет несколько независимых компонентов;
- качество объявляется без воспроизводимой фиксированной метрики;
- новая сессия требует пересказа старых чатов, чтобы понять задачу;
- сырой договор, PII или реальный текст попадает в репозиторий.

Если появился любой такой признак, следующая работа — восстановление контракта и состояния, а не добавление новой функциональности.
