# OCR Project State & Continuity v0

Последнее обновление: 2026-07-20, после исправления атомарности output Automatic Line Segmentation v0.

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
| Оркестрирующий ассистент | Выбирает первый незавершённый разрешённый шаг, открывает или перезапускает рабочие сессии Codex, даёт каждой одну ограниченную задачу, проверяет diff и тесты, обновляет этот файл при изменении состояния и объясняет результат владельцу продукта. |
| Рабочая сессия Codex | Восстанавливает контекст только из репозитория, реализует выданный шаг в заданных границах и сообщает входы, выходы, проверки и ограничения. Она не меняет продуктовую линию самостоятельно. |
| Репозиторий | Долговременная память проекта и источник истины. Решение, существующее только в чате или памяти одной сессии, считается незафиксированным. |

Если для работы нужна новая сессия Codex, её создание и ввод в контекст — обязанность оркестрирующего ассистента. Владелец продукта не должен вручную переносить контекст между сессиями.

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
| Сборщик Gold Set v0 | Реализован | Создаёт стратифицированный автономный review pack и принимает только approved/corrected экспорт | Ивритоговорящий проверяющий ещё не сформировал итоговый Gold Set v0 |
| Dataset & Evaluation Contract v0 | Реализован | Training builder требует непустой test-only Gold, исключает совпадения по source crop/image/text, пишет exclusion artifact и повторно запускает leakage gate; charset/CTC ID, split и CER покрыты тестами | Реального результата CER пока нет без Gold Set и предсказаний нашей модели; один договор доказывает только feasibility, не generalization |
| Image Resolution Contract v0 | Реализован | Зафиксированы preview 1800 px, master 2480×3508, ceiling 4096 px, line height 64 px, запрет искусственного upscale | Эти размеры ещё не подтверждены сравнением нескольких обученных recognizer-вариантов |
| Нормализатор страницы v0 | Реализован | Из принятых четырёх углов строит ограниченный grayscale master и удаляет внешние пиксели; при явном fallback сохраняет полный кадр; единый scale не увеличивает ни одну измеренную сторону | Это Python reference, а не Android memory implementation |
| Детектор границ страницы v0 | Реализован | Сомнительная граница не применяется: detector handoff явно выбирает принятый четырёхугольник или полный кадр; `frame_clipped`, mapping preview→source и QA-артефакты покрыты тестами | Один договор не доказывает production-качество на разных камерах, фонах и ракурсах; full-frame fallback ещё не означает, что границы текста найдены |
| Сегментация строк | Reference v0 реализован | Детерминированный fail-closed CLI с публикацией только полностью собранного output, line/page manifests, хеши, QA overlays, foreground accounting, mask/table/redaction/ambiguity gates и synthetic IoU/order/repeatability tests реализованы; локальный fixture из 9 страниц обработан без аварии | Smoke на одном договоре и synthetic gates не являются общей precision/recall; нет фиксированного human-annotated bbox benchmark и Android implementation |
| Собственный recognizer | Не реализован | Charset, синтетический генератор и evaluator готовы | Нет обученных весов, Gold CER, latency и размера модели |
| RTL/layout и структура пунктов | Не реализованы | Требование разделено от распознавания символов | Нет кода и измерений reading order |
| Android OCR integration | Не начата | Целевое ограничение on-device зафиксировано | Python reference-код не доказывает мобильную скорость и память |
| Production privacy gate | Не утверждён | Ограничения на внешнюю передачу данных зафиксированы | Подключение сырых фотографий к production заблокировано |

Успешный локальный прогон на текущем девятистраничном договоре является fixture smoke test, а не общей метрикой точности.

## 5. Два независимых блокера

1. **Gold Set v0.** Нужна посимвольная проверка выбранных реальных строк человеком, уверенно читающим иврит. Пока её нет, запрещено заявлять реальную CER или превосходство нашей модели над baseline.
2. **Production privacy design.** Пока он не утверждён, запрещено подключать сырые пользовательские фотографии к готовому приложению.

Сегментация строк на контролируемых полноразмерных страницах завершена как offline reference v0. Gold-блокер теперь снова определяет следующий шаг recognizer-feasibility; privacy-блокер по-прежнему запрещает production-подключение сырых фотографий.

## 6. Завершённый шаг: Automatic Line Segmentation v0

Контракт `research/hebrew_contract_ocr/LINE_SEGMENTATION_V0.md` и reference-модуль `line_segmenter.py` реализуют единственную ранее разрешённую задачу. CLI проверяет normalizer manifest, hashes, grayscale mode и размеры; отказывается перезаписывать непустой output; пишет line PNG, canonical `manifest.jsonl`, explicit `pages.jsonl`, `summary.json` и overlay каждой страницы.

Synthetic tests доказали ровно ограниченные gates v0: ожидаемое число обычных/heading/clause-number bands, top-to-bottom order, vertical IoU не ниже `0.90`, bboxes внутри страницы с положительной площадью, полное foreground accounting, одинаковые manifest bytes и line-image hashes при повторе, strict normalizer schema/type/status validation, exact consumed-byte provenance, decoded-header/pixel-limit checks before load, active Pillow bomb safety, cleanup после поздней ошибки с успешным retry в тот же output, separate geometric/final pass-review/fail propagation и fail-closed reasons для blank page, isolated speck, 6–7 px rule, insufficient/thin/near-edge geometry, close/merged lines, table, external mask, opaque redaction и edge crop. Сегментатор намеренно не объявляет training eligibility.

Контролируемый fixture `different_lease_fullres_rectified_v0` повторно проверен на текущем коде: 9 исходных страниц и detector handoff SHA-256 `5614ea0515b581cf8b53a4cfbe968d6471907ab072ad4f5ac9d8d23ff759e84e`. Текущие normalization manifest и summary имеют SHA-256 `79bb32fa81d62c4a280130a6dba4c5261976a586466c8b2437a7142d69868e46` и `1e5283904b3b184ddcf023588f5b955b458279dce9cd4164168e285b60df3868`; segmentation manifest, page reports и summary — `3e3a395324b24d286a9759f33df29fee4cb944c5e3c8d29ef64dc0976a3d16c4`, `cc60991bcdabfc13feaa6f0cf18c0c9af3b11799f17fd514ea2515b1e5ca07cf` и `237296bafcd978af24e8b30ff70c47b7acfc7574c1dc349b69349585b9971dfe`. Два локальных сквозных прогона завершились без аварии и создали byte-identical normalization/segmentation manifests, summaries, page reports, 269 line images и 9/9 overlays. Получено 269 candidate regions: geometric и final counts совпали — 129 `accepted`, 64 `review`, 76 `reject`. Эти 129 строк прошли только зафиксированные segmentation/resolution gates и не объявлены пригодными для обучения. Все 9 страниц имеют geometric и final `review` status. Единственная upstream resolution review page, P0009, получила `upstream_resolution_review` на всех 14 line rows и page row; её final statuses — 4 `review` и 10 `reject`. PR 119 исправил no-upscale округление: по сравнению с прежним fixture output ширина masters P0002, P0006, P0007 и P0009 уменьшилась на один пиксель, остальные пять master hashes и размеры не изменились. После исправления review-находок среди accepted-кандидатов минимальные наблюдаемые geometry/foreground составили 52 px width, 25 px height и 402 foreground pixels; ранее принятые 9×10, 1507×7, 47×6 и 635×6 artifacts теперь имеют explicit review/reject reasons. Overlays страниц с обычным body text, таблицей, логотипом, плотными закрывающими областями и подписью были выборочно осмотрены. Это fixture QA, не line-detection precision/recall и не OCR accuracy. Реальные страницы, кропы, overlays и manifests не коммитятся.

## 7. Единственный следующий шаг

**Human verification and materialization of Gold Set v0.** Другой OCR-шаг нельзя начинать без явного изменения этого файла и решения владельца продукта.

Разрешённые владельцем corrective-исключения от 2026-07-20 ограничены передачей `rejected boundary → full frame`, исправлением no-upscale, закрытием Gold/Silver leakage, удалением ложной recognizer eligibility, восстановлением согласованности state/контрактов с фактическим per-page `crop_policy` и устранением partial output после ошибки сегментатора. Они не добавляют новый OCR-компонент; после их слияния единственным следующим шагом остаётся Gold Set v0.

Граница задачи:

- вход: локальный архив из 170 silver rows и автономный Gold review pack, созданный существующим `build_gold_review_pack.py`; перед следующим handoff оркестрирующий ассистент обязан проверить и передать точные локальные пути и hashes;
- действие: человек, уверенно читающий иврит, посимвольно отмечает каждую строку как `approved`, `corrected`, `excluded` или оставляет `pending`; teacher label никогда не принимается автоматически;
- выход: локальный `gold_accepted_v0.jsonl`, затем materialized ignored `gold_v0` через существующий `dataset_contract.py`;
- проверка: принимаются только `approved`/`corrected`, все изображения и тексты проходят charset/hash/schema validation, Gold остаётся только `test`; последующая сборка training обязана получить этот Gold, исключить source/image/text matches и завершиться чистым leakage gate;
- реальные кропы, тексты, review exports и Gold manifest не коммитятся;
- этот шаг не тренирует recognizer, не измеряет CER без predictions нашей модели, не вызывает внешний OCR/API и не меняет приложение.

Это ручной verification gate, а не задача, которую Codex может честно завершить самостоятельно. Если qualified reviewer или локальный review pack недоступен, состояние остаётся заблокированным; нельзя подменять проверку teacher agreement, визуальной правдоподобностью или LLM-транскрипцией.

## 8. Протокол восстановления новой сессии

Новая рабочая сессия до изменения кода обязана:

1. Прочитать `AGENTS.md`.
2. Прочитать этот файл.
3. Прочитать `docs/ARCHITECTURE.md` и `docs/CUSTOM_OCR_PIPELINE.md`.
4. Прочитать контракты только тех компонентов, которых касается задача.
5. Проверить текущую ветку, незакоммиченные изменения и актуальный `origin/main`.
6. Одним абзацем сформулировать цель, разрешённый scope, вход, выход, тесты и запрещённые detours.
7. Реализовать только раздел «Единственный следующий шаг» или остановиться и сообщить о конфликте.

Оркестрирующий ассистент независимо проверяет результат сессии. Нельзя принимать формулировку «готово» без просмотра diff и отчёта тестов.

Каждые 3–5 слитых OCR PR проводится cold-start audit: чистая сессия, которой доступен только репозиторий, должна корректно объяснить архитектуру и состояние, запустить проверки и назвать следующий шаг.

Первый cold-start audit проведён 2026-07-19 до публикации этого файла. Чистая сессия правильно восстановила архитектуру, уровни доказательности, два блокера и Automatic Line Segmentation v0. Найденные ею пробелы в идентификации локального fixture и измеримых gates были исправлены до коммита.

Второй repository continuity audit проведён 2026-07-20 после PR 117–121. Он выявил устаревшее fixture evidence после изменения no-upscale, конфликт full-frame fallback в Image Resolution Contract и неверный per-page `crop_policy`; PR 122 исправил эти связанные несогласованности. Audit также выявил высокий риск partial output: поздняя ошибка сегментатора оставляла уже записанные кропы и блокировала retry. Риск исправлен через sibling staging, cleanup при ошибке и публикацию только полностью собранного результата. Audit состоялся после пяти слитых OCR PR, то есть на два PR позже более строгого локального срока «не позднее третьего»; это зафиксировано как процессная ошибка. Следующий cold-start audit требуется не позднее третьего слитого OCR PR после PR 122.

## 9. Обязательный формат передачи задачи Codex

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

Синтетические данные, review pack, Gold materialization и CER описаны в `research/hebrew_contract_ocr/README.md` и `research/hebrew_contract_ocr/DATASET_CONTRACT_V0.md`.

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
