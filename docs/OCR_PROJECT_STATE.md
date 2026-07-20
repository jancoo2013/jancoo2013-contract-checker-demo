# OCR Project State & Continuity v0

Последнее обновление: 2026-07-20, после mixed-script CTC Text Order Contract v0.

Это каноническая точка восстановления текущего OCR-проекта. Она отвечает на практические вопросы: что уже сделано, что действительно проверено, что пока только предполагается и какой шаг разрешён следующим.

Архитектурные решения по-прежнему задают `docs/ARCHITECTURE.md` и `docs/CUSTOM_OCR_PIPELINE.md`. Компонентные контракты задают точные входы, выходы и ограничения. Если этот файл расходится с ними, нельзя молча выбирать удобную версию: рабочая сессия должна остановиться, описать конфликт и исправить документы отдельным небольшим PR.

## 1. Цель продукта

Построить собственный узкоспециализированный OCR печатных израильских договоров аренды:

- распознавание печатного иврита, цифр, пунктуации и небольших латинских вставок;
- работа на Android без отправки фотографий внешнему OCR-провайдеру;
- собственная компактная модель и собственные веса;
- сохранение координат, RTL-порядка, номеров пунктов и структуры договора;
- передача доказуемых фрагментов юридическому анализатору, а не генерация «правдоподобного» текста.

Surya, Chandra, Tesseract и мультимодальные LLM могут быть только локальными исследовательскими учителями или baseline. Они не входят в готовый продукт.

## 2. Кто чем управляет

| Роль | Ответственность |
|---|---|
| Владелец продукта | Выбирает цель и приоритет, подтверждает смену направления, проверяет и сливает PR. Не обязан управлять рабочими сессиями Codex или заново пересказывать им историю проекта. |
| Оркестрирующий ассистент | Выбирает первый незавершённый разрешённый шаг, реализует его самостоятельно либо делегирует ограниченную часть Codex, проверяет diff и тесты, обновляет этот файл при изменении состояния и объясняет результат владельцу продукта. |
| Рабочая сессия Codex | Опциональный исполнитель для сложной ограниченной задачи. Восстанавливает контекст только из репозитория, работает в выданных границах и не меняет продуктовую линию самостоятельно. |
| Репозиторий | Долговременная память проекта и источник истины. Решение, существующее только в чате или памяти одной сессии, считается незафиксированным. |

Если для работы нужна сессия Codex, её создание и ввод в контекст — обязанность оркестрирующего ассистента. Владелец продукта не должен вручную переносить контекст между сессиями.

## 3. Текущий сквозной путь

```text
фотография страницы
→ предложение границ листа или сохранение полного кадра
→ геометрическое выравнивание и ограничение разрешения
→ локальная обработка приватности по утверждённому дизайну
→ сегментация страницы на строки
→ собственный распознаватель строк
→ RTL-сборка строк и страницы с координатами
→ восстановление пунктов и структуры договора
→ evidence blocks
→ юридический анализ и отчёт на русском
```

До утверждения privacy-дизайна сырые пользовательские фотографии нельзя подключать к production-потоку. Это не запрещает локальные исследования на контролируемых, синтетических или редактированных данных.

## 4. Реальное состояние компонентов

| Компонент | Состояние | Что доказано | Что не доказано |
|---|---|---|---|
| Генератор синтетических строк | Реализован | Детерминированная генерация, точный synthetic ground truth, локальные шрифты и деградации покрыты кодом и тестами | Синтетика сама по себе не доказывает качество на фотографиях |
| Локальный архив из 170 строк | Существует вне репозитория как `silver` | Кропы и предварительные подписи пригодны для bootstrap и диагностики | Это не Gold Set и не источник реальной CER |
| Gold review workflow | Candidate freeze реализован, prediction pack не собран | `freeze_gold_candidates.py` фиксирует high-resolution images и pilot/evaluation cohorts до predictions; model-assisted порядок задан `docs/MODEL_ASSISTED_GOLD_TESTING_V0.md` | Recognizer, APK, человеческая проверка и итоговый Gold Set v0 отсутствуют |
| Dataset & Evaluation Contract v0 | Реализован | Training builder требует непустой test-only Gold, исключает совпадения по source crop/image/text, пишет exclusion artifact и повторно запускает leakage gate; charset/CTC ID, split и CER покрыты тестами | Реального результата CER пока нет без Gold Set и предсказаний нашей модели; один договор доказывает только feasibility, не generalization |
| Image Resolution Contract v0 | Реализован | Зафиксированы preview 1800 px, master 2480×3508, ceiling 4096 px, line height 64 px, запрет искусственного upscale | Эти размеры ещё не подтверждены сравнением нескольких обученных recognizer-вариантов |
| Нормализатор страницы v0 | Реализован | Из принятых четырёх углов строит ограниченный grayscale master и удаляет внешние пиксели; при явном fallback сохраняет полный кадр; единый scale не увеличивает ни одну измеренную сторону | Это Python reference, а не Android memory implementation |
| Детектор границ страницы v0 | Реализован | Сомнительная граница не применяется: detector handoff явно выбирает принятый четырёхугольник или полный кадр; `frame_clipped`, mapping preview→source и QA-артефакты покрыты тестами | Один договор не доказывает production-качество на разных камерах, фонах и ракурсах; full-frame fallback ещё не означает, что границы текста найдены |
| Сегментация строк | Reference v0 реализован | Детерминированный fail-closed CLI с публикацией только полностью собранного output, line/page manifests, хеши, QA overlays, foreground accounting, mask/table/redaction/ambiguity gates и synthetic IoU/order/repeatability tests реализованы; локальный fixture из 9 страниц обработан без аварии | Smoke на одном договоре и synthetic gates не являются общей precision/recall; нет фиксированного human-annotated bbox benchmark и Android implementation |
| Собственный recognizer | Input adapter, mixed-script CTC decoder/order contract и isolated CPU runtime v0 реализованы; neural model отсутствует | CTC collapse выполняется в visual alignment order до reorder; поддержаны pure Hebrew, digits, Latin, clause numbers, punctuation, spaces и mixed `AS-IS`; logical↔alignment round trip и padding/blank/repeat behavior покрыты focused tests | Слитные Hebrew+LTR strong tokens без ASCII-пробела намеренно fail closed; отсутствуют memory bounds, neural architecture, training loop, веса, predictions, Gold CER, latency и размер модели |
| RTL/layout и структура пунктов | Не реализованы | Требование разделено от распознавания символов | Нет кода и измерений reading order |
| Android OCR integration | Не начата | Целевое ограничение on-device зафиксировано | Python reference-код не доказывает мобильную скорость и память |
| Production privacy gate | Не утверждён | Ограничения на внешнюю передачу данных зафиксированы | Подключение сырых фотографий к production заблокировано |

Успешный локальный прогон на текущем девятистраничном договоре является fixture smoke test, а не общей метрикой точности.

## 5. Два независимых блокера

1. **Gold Set v0.** Нужны прогнозы замороженной собственной модели и проверка их точного полного результата человеком, уверенно читающим иврит. Bootstrap recognizer разрешено обучить до Gold только для подготовки этих прогнозов; заявлять реальную CER или превосходство над baseline до held-out проверки запрещено.
2. **Production privacy design.** Пока он не утверждён, запрещено подключать сырые пользовательские фотографии к готовому приложению.

Сегментация строк на контролируемых полноразмерных страницах завершена как offline reference v0. Gold-блокер определяет recognizer-feasibility; privacy-блокер по-прежнему запрещает production-подключение сырых пользовательских фотографий. Mixed-script CTC Text Order Contract v0 устранил глобальное time-axis reversal; неоднозначные слитные Hebrew+LTR tokens теперь явно отклоняются, а не преобразуются в правдоподобный текст.

## 6. Завершённая preprocessing, candidate-freeze и recognizer-boundary база

Контракт `research/hebrew_contract_ocr/LINE_SEGMENTATION_V0.md` и reference-модуль `line_segmenter.py` реализуют Automatic Line Segmentation v0. CLI проверяет normalizer manifest, hashes, grayscale mode и размеры; отказывается перезаписывать непустой output; пишет line PNG, canonical `manifest.jsonl`, explicit `pages.jsonl`, `summary.json` и overlay каждой страницы.

Synthetic tests доказали ровно ограниченные gates v0: ожидаемое число обычных/heading/clause-number bands, top-to-bottom order, vertical IoU не ниже `0.90`, bboxes внутри страницы с положительной площадью, полное foreground accounting, одинаковые manifest bytes и line-image hashes при повторе, strict normalizer schema/type/status validation, exact consumed-byte provenance, decoded-header/pixel-limit checks before load, active Pillow bomb safety, cleanup после поздней ошибки с успешным retry в тот же output, separate geometric/final pass-review/fail propagation и fail-closed reasons для blank page, isolated speck, 6–7 px rule, insufficient/thin/near-edge geometry, close/merged lines, table, external mask, opaque redaction и edge crop. Сегментатор намеренно не объявляет training eligibility.

Контролируемый fixture `different_lease_fullres_rectified_v0` повторно проверен на текущем коде: 9 исходных страниц и detector handoff SHA-256 `5614ea0515b581cf8b53a4cfbe968d6471907ab072ad4f5ac9d8d23ff759e84e`. Текущие normalization manifest и summary имеют SHA-256 `79bb32fa81d62c4a280130a6dba4c5261976a586466c8b2437a7142d69868e46` и `1e5283904b3b184ddcf023588f5b955b458279dce9cd4164168e285b60df3868`; segmentation manifest, page reports и summary — `3e3a395324b24d286a9759f33df29fee4cb944c5e3c8d29ef64dc0976a3d16c4`, `cc60991bcdabfc13feaa6f0cf18c0c9af3b11799f17fd514ea2515b1e5ca07cf` и `237296bafcd978af24e8b30ff70c47b7acfc7574c1dc349b69349585b9971dfe`. Два локальных сквозных прогона завершились без аварии и создали byte-identical normalization/segmentation manifests, summaries, page reports, 269 line images и 9/9 overlays. Получено 269 candidate regions: geometric и final counts совпали — 129 `accepted`, 64 `review`, 76 `reject`. Эти 129 строк прошли только зафиксированные segmentation/resolution gates и не объявлены пригодными для обучения. Все 9 страниц имеют geometric и final `review` status. Единственная upstream resolution review page, P0009, получила `upstream_resolution_review` на всех 14 line rows и page row; её final statuses — 4 `review` и 10 `reject`. PR 119 исправил no-upscale округление: по сравнению с прежним fixture output ширина masters P0002, P0006, P0007 и P0009 уменьшилась на один пиксель, остальные пять master hashes и размеры не изменились. После исправления review-находок среди accepted-кандидатов минимальные наблюдаемые geometry/foreground составили 52 px width, 25 px height и 402 foreground pixels; ранее принятые 9×10, 1507×7, 47×6 и 635×6 artifacts теперь имеют explicit review/reject reasons. Overlays страниц с обычным body text, таблицей, логотипом, плотными закрывающими областями и подписью были выборочно осмотрены. Это fixture QA, не line-detection precision/recall и не OCR accuracy. Реальные страницы, кропы, overlays и manifests не коммитятся.

Gold candidate freeze v0 реализован отдельным fail-closed builder. Он принимает только final/geometric `accepted` строки с upstream resolution `pass`, повторно проверяет потребляемые source fields, provenance, exact PNG hashes, grayscale mode и bbox dimensions, копирует исходные PNG bytes без изменения и до model predictions назначает page-round-robin pilot и held-out evaluation cohorts. На текущем локальном fixture два независимых запуска дали одинаковый manifest SHA-256 `dce33991f8eee55b03c8e4eb26fabd3030e6e6c6907849ae5e4f42cfe9ce2dc2`: из 269 segmentation rows заморожены 129 candidates, 10 pilot и 119 evaluation. Manifest не содержит текста или predictions; это candidate set, не Gold и не доказательство OCR accuracy.

`CTC_TEXT_ORDER_V0.md`, `text_order.py` и `ctc_decoder.py` разделяют logical Unicode и monotonic CTC alignment order. Standard CTC collapse выполняется до reorder. Поддерживаемый v0 transform обратим для whitespace-separated Hebrew/LTR tokens, сохраняет внутренний порядок digits/Latin и зеркалит парные скобки; чистые LTR lines остаются identity. Token с Hebrew и LTR strong characters без ASCII-space boundary блокируется как неподдерживаемый.

## 7. Единственный следующий шаг

**Bound recognizer input resized width and total batch allocation before neural model code.** Другой OCR-шаг нельзя начинать без явного изменения этого файла и решения владельца продукта.

Cold-start audit выявил, что `recognizer_input.py` ограничивает decoded source pixels, но не ограничивает ширину после resize к высоте 64 и не проверяет суммарную float32 allocation перед `np.zeros`. Патологическая узкая и очень высокая или очень широкая строка может пройти source-pixel gate и запросить недопустимый tensor.

Граница задачи:

- вход: `research/hebrew_contract_ocr/recognizer_input.py`, Image Resolution Contract v0 и focused input-adapter tests;
- действие: добавить явный maximum resized width и maximum total batch elements/bytes, вычисляемые и проверяемые до materialization/`np.zeros`;
- выход: fail-closed input adapter с неизменным normal-batch output contract;
- обязательные проверки: точная допустимая граница, oversize single line, aggregate batch overflow, прежний normal batch, widths/targets/padding и deterministic repeated preparation;
- этот шаг не добавляет CRNN, training loop, dependencies, weights, predictions, APK, dataset ingestion или production integration.

После memory bounds отдельными PR последуют minimal CRNN forward с расширением CI, training loop, frozen predictions и reviewer APK. Pilot content stratification нужно исправить до сборки APK. Document-level provenance gate обязателен до подключения старого silver-архива, но не нужен synthetic-only bootstrap.

## 8. Протокол восстановления новой сессии

Новая рабочая сессия до изменения кода обязана:

1. Прочитать `AGENTS.md`.
2. Прочитать этот файл.
3. Прочитать `docs/ARCHITECTURE.md` и `docs/CUSTOM_OCR_PIPELINE.md`.
4. Прочитать контракты только тех компонентов, которых касается задача.
5. Проверить текущую ветку, незакоммиченные изменения и актуальный `origin/main`.
6. Одним абзацем сформулировать цель, разрешённый scope, вход, выход, тесты и запрещённые detours.
7. Реализовать только раздел «Единственный следующий шаг» или остановиться и сообщить о конфликте.

Оркестрирующий ассистент независимо проверяет результат. Нельзя принимать формулировку «готово» без просмотра diff и отчёта тестов.

Каждые 3–5 слитых OCR PR проводится cold-start audit: чистая сессия, которой доступен только репозиторий, должна корректно объяснить архитектуру и состояние, запустить проверки и назвать следующий шаг.

Первый cold-start audit проведён 2026-07-19 до публикации этого файла. Чистая сессия правильно восстановила архитектуру, уровни доказательности, два блокера и Automatic Line Segmentation v0. Найденные ею пробелы в идентификации локального fixture и измеримых gates были исправлены до коммита.

Второй repository continuity audit проведён 2026-07-20 после PR 117–121. Он выявил устаревшее fixture evidence после изменения no-upscale, конфликт full-frame fallback в Image Resolution Contract и неверный per-page `crop_policy`; PR 122 исправил эти связанные несогласованности. Audit также выявил высокий риск partial output: поздняя ошибка сегментатора оставляла уже записанные кропы и блокировала retry. Риск исправлен через sibling staging, cleanup при ошибке и публикацию только полностью собранного результата. Audit состоялся после пяти слитых OCR PR, то есть на два PR позже более строгого локального срока «не позднее третьего»; это зафиксировано как процессная ошибка.

Третий cold-start continuity audit проведён 2026-07-20 после PR 123–128. Он подтвердил candidate freeze, recognizer input boundary и isolated CPU runtime, но выявил blocking global RTL reversal, отсутствие post-resize/batch memory bounds, неполный OCR test command в CI, stale candidate-freeze documentation, несовместимые reviewer/materializer status names и отсутствие гарантии mixed-script строки в pilot. PR 129 устранил stale state, старый low-resolution Gold path и status mapping; следующий corrective PR устранил global RTL reversal через bounded mixed-script CTC Text Order Contract v0. Остальные кодовые исправления остаются отдельными маленькими PR в порядке раздела 7.

Следующий cold-start audit требуется не позднее третьего слитого OCR PR после завершения corrective-серии, либо немедленно при новом конфликте контрактов.

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
Готовность: diff, результаты проверок, ограничения, готовый к review PR без auto-merge.
```

## 10. Воспроизводимые команды

Установка и базовая проверка чистого checkout:

```bash
python -m pip install -r requirements.txt
python -m py_compile app.py contract_checker/*.py research/hebrew_contract_ocr/*.py
python -m unittest discover -s tests
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

Синтетические данные, legacy silver review pack, current Gold workflow, Gold materialization и CER описаны в `research/hebrew_contract_ocr/README.md`, `docs/MODEL_ASSISTED_GOLD_TESTING_V0.md` и `research/hebrew_contract_ocr/DATASET_CONTRACT_V0.md`. CTC alignment/logical order зафиксирован в `research/hebrew_contract_ocr/CTC_TEXT_ORDER_V0.md`.

## 11. Правило обновления состояния

Каждый OCR PR обязан обновить этот файл, если изменились реализованный компонент, доказательство, блокер или следующий шаг. Одновременно разрешён только один следующий шаг.

Запрещённые признаки потери управляемости:

- важный скрипт или датасет существует только на локальном компьютере без manifest/инструкции;
- константа качества не объяснена контрактом;
- две параллельные реализации выполняют один этап без явно выбранной канонической;
- PR одновременно меняет несколько независимых компонентов;
- качество объявляется без воспроизводимой фиксированной метрики;
- новая сессия требует пересказа старых чатов, чтобы понять задачу;
- сырой договор, PII или реальный текст попадает в репозиторий.

Если появился любой такой признак, следующая работа — восстановление контракта и состояния, а не добавление новой функциональности.
