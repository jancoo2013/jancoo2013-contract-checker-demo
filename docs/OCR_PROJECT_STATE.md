# OCR Project State & Continuity v0

Последнее обновление: 2026-10-06, PR #318, `expert-memory-real-contract-eval-observation-2026-10-06`.

Версия состояния: `privacy-ocr-2026-10-06-167`.

Активный трек: `expert-memory-development`.

Канонический следующий bounded-шаг: `expert-memory-complete-real-contract-evaluation-v1`.

PR #318 — зафиксированы результаты ручного реального прогона Expert Memory от 2026-10-06 и смена исследовательского направления по решению владельца. Synthetic blind evaluation из PR #313–#315 не выполняется как следующий канонический model-quality шаг; существующие synthetic fixtures остаются историческими исследовательскими артефактами и не удаляются. В ручном тесте полного приватного трёхстраничного договора Gemini 3.1 Pro Pass 1 Router дал широкое покрытие, но показал последовательный сдвиг привязки содержания к соседним номерам пунктов и over-routing. Pass 2 с полным договором + неизменённым Router + текущими Core Protocol / Mechanism Map / Concept Lexicon самостоятельно исправил существенную часть ошибок Router, восстановил основные механизмы, сохранил отсутствующее приложение как unresolved и обнаружил два внутренних печатных несоответствия. При этом остались две критичные ошибки: source-clause drift в районе §§9–10 и перенос правила возврата между двумя по-разному названными обеспечительными инструментами несмотря на собственный unresolved; также выявлена ссылка relation на несуществующий mechanism_id. Это закрепляет необходимость отдельных инвариантов source-clause identity, unresolved object identity и graph-reference validity. Pass 3 на 3.1 Pro не завершён: лимит модели закончился, интерфейс автоматически переключился на 3.5 Flash и предыдущий контекст оказался недоступен; это фиксируется как process-observation, а не как качество Flash. Точное model/version теперь считается контролируемой переменной, а разговорная память не должна быть единственным носителем состояния между проходами. По решению владельца будущая ручная оценка должна начинаться с полного реального договора целиком, без синтетической подмены и без семантической нарезки; рукопись остаётся заблокированной. Это не меняет production privacy/security: raw contract, raw OCR и recoverable PII по-прежнему запрещены в GitHub/CI/downstream runtime LLM по SECURITY.md. Следующий шаг — формализовать и выполнить воспроизводимый complete-real-contract full-document evaluation protocol, сохраняя в репозитории только обезличенные наблюдения и метрики.

PR #315 — сняты два методических блокера перед blind synthetic evaluation без добавления нового retrieval-слоя. Для Run A зафиксирован один неизменяемый stock-baseline prompt. Для Pass 2/3 v1 введено детерминированное правило ALL-CONTEXT: модель снова получает весь синтетический договор, полный текущий Mechanism Map и полный Concept Lexicon; Router Pass 1 оценивается отдельно и не может лишить семантический проход нужного знания. Router-scoring упрощён до невзвешенного подсчёта missing/unsupported families; деление ожидаемых меток на critical/noncritical в v1 не вводится. Содержимое synthetic lease, expected Router families, 21 critical fact, 17 cross-clause checks, prohibited inferences, runtime, privacy boundary и real-contract corpus не изменены. Следующее действие — фактически выполнить Run A на выбранной базовой модели в свежем контексте и сохранить ответ без исправлений, затем тем же model/version выполнить Run B.

PR #314 — внесён source-evidence gate в стратегию Expert Memory и уточнён blind synthetic protocol: модельные цитаты остаются кандидатами, существенные факты для рабочего вывода требуют независимой сверки с доступным источником и локатором; стадия чтения оценивается отдельно от Router и связей. Зафиксирована ограниченная ручная диагностика RC07 со слов владельца для Gemini 3.1 Pro: ошибки PDF-ответа и третьего прохода, а также улучшение отдельного PNG-ответа без приписывания причины формату. Печатный приватный источник не публикуется; наблюдение не становится Gold или обучающей меткой. Sealed synthetic reference и runtime не менялись, внешняя модель в PR не вызывалась. Канонический `next_step_id` остаётся прежним; scored taught-pipeline run пока требует заранее фиксированного правила выбора модулей/связанных пунктов, а взвешенная оценка Router — явной разметки критичности ожидаемых меток.

PR #313 — подготовлен свежий blind synthetic lease fixture для текущего шага `expert-memory-router-blind-synthetic-evaluation-v1`. Добавлен полностью синтетический ивритский договор без реальных сторон/адресов/реквизитов/подписей/сырого OCR, отдельный sealed reference JSON и операторский протокол stock-baseline vs taught-pipeline. Договор содержит 22 пункта + приложенный synthetic Annex A и намеренно отсутствующий в test package Annex B; механизмы включают definitions/document precedence, claimed letting authority, split payment channels, service-account registration/evidence, condition/repairs/recovery/setoff, use/occupancy/access/alterations, tenant replacement and landlord transfer, two distinct security instruments, option with external CPI dependency, insurance branching, breach-specific vs general cure, vacating/pre-return protocol/left-behind property/holdover and dispute forum. Sealed reference фиксирует 21 critical fact, expected Router families по пунктам, required concepts/temporal roles, 17 cross-clause checks, prohibited inferences и scoring weights. Внешняя модель в этом PR не вызывалась; gold нельзя передавать тестируемой модели. `next_step_id` остаётся прежним до фактического baseline/taught run и scoring.

PR #312 — выполнен второй проход по `Concept Lexicon`: v0.2 сверена с Foundation Core, Mechanism Map v0.2, recurring Question Engine inventory, Expert Pack examples/playbook и текущими обезличенными/печатными mechanism packets. Исправлены ошибки типов: `LETTING_ENTITLEMENT_CLAIM` и `CONDITION_ACKNOWLEDGMENT` теперь `ASSERTION`, `LEASE_TERM` — `TEMPORAL_STRUCTURE`, `DEFECTS_LIST`/`PROPERTY_INVENTORY`/`CONDITION_PROTOCOL` — `DOCUMENT`, `DISPUTE_FORUM` — договорная `RELATION` с отдельной внешней проверкой эффекта. `TRANSFER_RESTRICTION` перенесён из M05 в M06. Добавлены семь понятий, которых не хватало для точного покрытия: `CONTRACT_DEFINITION`, `USE_OCCUPANCY_RULE`, `LANDLORD_TRANSFER_RULE`, `LEFT_BEHIND_PROPERTY_RULE`, `SERVICE_ACCOUNT_REGISTRATION`, `EVIDENCE_PRODUCTION_OBLIGATION`, `EXTERNAL_FINANCIAL_FRAMEWORK`. Текущий teaching set: 54 top-level concepts + 10 temporal roles; все 30 исторических IDs сохранены. SECURITY, Router, extraction/runtime schema, Gold, statutory authority и privacy boundaries не менялись. Канонический следующий шаг `expert-memory-router-blind-synthetic-evaluation-v1` не изменён.

PR #311 — добавлена третья учебная часть Expert Memory: `Concept Lexicon v0.2`. Она объединяет исходные 30 кандидатов понятий, текущие SECURITY-карточки, решения `DOCUMENT_REFERENCE`/`REPAIR_COST_RECOVERY` и различия, найденные аудитом Mechanism Map v0.2, в текущий компактный набор из 47 top-level concepts и 10 reusable temporal roles. Для каждого понятия задаются `kind`, определение, essential slots, relations, `do_not_confuse` и evidence boundary; `TENANT_REPAIR_RECOVERY` сохранён как исторический subtype общего `REPAIR_COST_RECOVERY`, `INSTITUTIONAL_GUARANTEE` включён в SECURITY без новой Router-family. Добавлены явные понятия для ролей/объекта/основания сдачи, статуса и связей документов, payment channel, external value linkage, condition protocol, alterations/improvements, generalized termination, set-off и dispute forum. Learning Strategy и Mechanism Map синхронизированы: knowledge hierarchy теперь `Foundation Core → Mechanism Map → Concept Lexicon → detailed modules/examples → verified legal overlays`, при этом operational pass 1 остаётся компактным, а pass 2 загружает только релевантный slice лексикона. Старый 30-concept inventory остаётся историческим research snapshot. Это документационный исследовательский слой, не Router schema, не extraction schema, не Gold, не runtime и не правовой источник; канонический следующий шаг `expert-memory-router-blind-synthetic-evaluation-v1` не изменён.

PR #310 — выполнен второй проход по карте механизмов Expert Memory с сопоставлением против текущего обезличенного/печатного корпуса и recurring inventory. v0.1 в целом правильно покрывала жизненный цикл аренды, но недостаточно явно представляла четыре структуры: (1) право/полномочие сдающей стороны и внешние title/proceeding dependencies; (2) статус/версию документа, entire-agreement, supersession, written-change и incorporation; (3) сквозные денежные последствия — проценты, индексацию, компенсацию, collection/repair costs, set-off и overlap нескольких денежных heads; (4) договорный forum/adjudication mechanism (court/arbitration/Beit Din) как часть текста договора, отдельно от внешней процессуальной действительности. Карта обновлена до v0.2; добавлены M12 `Monetary remedies, sanctions, set-off, and overlap` и M13 `Dispute forum and adjudication clauses`, усилены M00–M11, connectors и retrieval clusters. По текущему изученному корпусу каждому существенному печатному механизму теперь есть явное место; универсальная полнота для всех израильских договоров не утверждается. Router schema, Gold, runtime, statutory authority, provider use и канонический следующий шаг `expert-memory-router-blind-synthetic-evaluation-v1` не изменены.

PR #309 — добавлен второй учебный слой Expert Memory: функциональная карта механизмов жилой аренды между Foundation Core и Router. Карта описывает рамку договора/стороны/объект, срок и продление, арендную плату, прочие денежные обязанности, состояние/ремонт/ущерб, использование/доступ/изменения, передачу/замену/досрочный выход, обеспечения, нарушение/уведомление/исправление/расторжение, возврат/освобождение/holdover, страхование/ответственность и сквозные уведомления/доказательства/ссылки. Для каждого механизма зафиксированы функция, ключевые вопросы, Router-support и границы смешения. Отдельно закреплено, что механизм не равен Router-label: Router — слой индексирования/retrieval, NOTICE и OTHER сквозные, а один механизм может требовать нескольких семей. Добавлены cross-mechanism connectors и примерная selective-retrieval map для второго прохода. Это не новый Router schema, не Gold, не правовой источник и не runtime-правило; канонический следующий шаг `expert-memory-router-blind-synthetic-evaluation-v1` не изменён.

PR #308 — по решению владельца зафиксирована экспериментальная стратегия обучения/контекстного инструктирования Expert Memory от общего к частному и компактное Foundation Core. Базовое ядро объясняет договор как связанную систему механизмов, вводит проверку полноты страниц и прямо указанных приложений до сильных выводов, различает отсутствие факта и нехватку данных, сохраняет границы нечитаемого текста/рукописи, определения и ссылки, временную логику, право/обязанность/разрешение/запрет, четыре слоя доказательств и явную неопределённость. Рабочий порядок: Foundation Core → первый структурный Router-проход без оценки риска → второй проход с подгрузкой только релевантных механизмов → третий проход сверки связанных пунктов → финальный completeness audit. Router рассматривается как индекс/слой retrieval, а не как фундамент онтологии; полный разрастающийся «учебник» не должен подаваться модели целиком в каждом запросе. Это документальная исследовательская гипотеза, не обучение весов, не Gold, не новый Router family, не runtime-схема и не правовой источник. Активный трек и канонический следующий шаг `expert-memory-router-blind-synthetic-evaluation-v1` не изменены.

PR #307 — bounded statutory/Expert Memory exception. The 2026 section 25y institutional-guarantee amendment is recorded as in force from 2026-09-30 without expert-review or runtime promotion. `INSTITUTIONAL_GUARANTEE` is a subtype inside Router family `SECURITY`; personal guarantees, security cheques and promissory notes remain distinct, and unknown tenant financial outlay leaves cap applicability unresolved. Focused regressions cover provider classes, date and provenance. The canonical next step is unchanged.

PR #306 — отдельно сохранена обезличенная исследовательская заметка по вручную присланному ответу второго прохода Gemini на RC07. Связь §§6/13 была показана модели в примере формата; выводы о поздней отправке уведомления, автоматическом освобождении при замене и удержании обеспечительного чека весь срок выходят за пределы печатных опор. Пропуски связей отмечены без подсчёта точности. Полный промпт и точная версия модели неизвестны, оригинал и рукопись не опубликованы; Router, рабочие вопросы, исторический пакет RC07, Gold, обучение, внешний provider/runtime и канонический следующий шаг не меняются.

PR #305 — по решению владельца ассистент, отвечающий за PR, может слить авторизованное ограниченное изменение без повторной команды владельца после сверки финального diff, обязательных проверок CI, обоих state-файлов и итогового security review. Отдельный исполнитель оставляет решение ассистенту-организатору; явный запрет владельца или блокирующая находка останавливает merge. GitHub auto-merge остаётся выключенным. Продуктовый шаг, границы данных и безопасность не меняются.

PR #304 — по поручению владельца ассистент визуально сверил три исходные фотографии с обезличенным `contract_001`: последовательность `8.א` → `9.א`, печатное содержание §12 и выбранные существенные опоры §§3, 4, 9, 11, 17, 21, 24 подтверждены без обнаруженного существенного расхождения. Это не удостоверение каждого символа, содержимого недоступного приложения или рукописи. Добавлен исследовательский первый проход Router по 43 блокам обезличенного текста: множественные семейства, сохраняющий содержание `OTHER`, техническое исключение подписей, шесть связей для повторного чтения и офлайн-проверка полноты структурированного ответа. Проход сделал тот же ассистент, знакомый с договором и онтологией: независимого теста модели, показателя точности, Gold или разрешения обучения нет. Прямое тождество с архивным RC PDF и каноническая связь с TF_C остаются UNKNOWN; следующий шаг — новый слепой синтетический тест Router с отдельной проверкой ошибок, без внешнего прогона реального договора.

PR #303 — приватная локальная OCR-сверка трёх исходных фотографий с обезличенным `contract_001` дала высокую уверенность в соответствии источника и поддержала печатную последовательность `8.א` → `9.א` без промежуточного напечатанного `8.ב` в этих фотографиях. Сравнение нескольких пунктов с архивными PDF выявило сильного кандидата печатного семейства TF_C, но RC06 представляет другую редакцию: его дополнительные условия не переносились в fixture. Каноническая связь с RC-группой и тождество конкретного PDF остаются UNKNOWN; полный текст не подтверждён владельцем, по пункту 12 OCR слабее. Рукопись, подписи и возможные отдельные дополнения не анализировались. Опубликованы только обезличенные выводы, ограничения и локальные проверки; Gold, обучение, cohort scoring, внешний провайдер и runtime не открыты. Следующий шаг — подтверждение текста владельцем и точной исходной связи при наличии доказательств.

PR #302 — оформлены первые пять черновых исследовательских карточек SECURITY из кандидатов №08–12: обеспечительный чек, вексель, поручительство, возможное использование и возврат обеспечения. Шесть полей каждой карточки описывают понятие, слоты-вопросы, связи и границы смешения; отдельный реестр привязывает их к опубликованным обезличенным механизмам. Проверяются раздельность инструментов, неоднозначный денежный предел RC06, узкий срок возврата коммунальных чеков RC03 и различие передачи обеспечения и уведомления перед использованием. Карточки не являются доказательством фактической выдачи или взыскания, юридическим Gold, метками обучения или runtime-схемой. Неподтверждённое происхождение `contract_001`, запрет внешних прогонов и канонический следующий шаг не изменены.

PR #301 — для будущей редакции исследовательского ядра согласованы два рабочих различия: сквозная ссылка на другой документ с отдельными признаками включения, приоритета и доступности текста (`DOCUMENT_REFERENCE`), а также направленное требование расходов на ремонт (`REPAIR_COST_RECOVERY`). №14 `TENANT_REPAIR_RECOVERY` остаётся частным маршрутом в датированном снимке из 30 кандидатов; противоположная ветка RC05 не объявляется правом арендатора на зачёт. Это решения уровня глоссария без формализации карточек, новых JSON-ID, извлекателя, Gold, обучения, внешних прогонов и правовых выводов. Активный трек, канонический следующий шаг, приватность и runtime не изменены.

PR #300 — к исследовательской инвентаризации онтологии добавлена сверка всех 12 обезличенных печатных механизмов RC05 и RC07 с существующими 30 кандидатами понятий. Указаны покрытия, отрицательные границы, отдельные временные триггеры и различия вне ядра: регистрация счетов/представление квитанций, предвозвратный протокол, направление возмещения ремонта и запрет зачёта, включённый недоступный документ, срок исправления после требования. Это предложения для проверки, без новых карточек, ID ядра, JSON-схемы, извлекателя, Gold, обучения или независимого scoring. Канонический следующий шаг, заморозка внешних прогонов, приватность и runtime не меняются.

PR #299 — по прямому разрешению владельца опубликованы два обезличенных исследовательских пакета: по шесть привязанных к печатным пунктам кандидатов ошибок чтения RC05 и RC07. Это гипотезы контроля, а не наблюдённые сбои модели, юридический Gold или обучающие метки. RC05/TF_B имеет собственную короткую редакцию; условия RC02/RC03 не заполняют её пробелы. Поскольку RC07/TF_D был вручную прочитан, это семейство переведено в development research: среди RC01–RC07 больше нет нетронутого независимого test-семейства. Карта покрытия, split, валидаторы и исследовательские документы синхронизированы. Оригиналы, OCR, рукопись, идентификаторы, реквизиты, provider/runtime и юридические выводы не добавлены. Активный трек, заморозка внешних прогонов и канонический следующий шаг не меняются.

PR #298 — по прямому разрешению владельца опубликована исследовательская инвентаризация онтологии: 30 кандидатов понятий и 9 временных ролей из существующих обезличенных разборов, с определениями, атрибутами, связями, источниками и контролями смешения. Тип инструмента отделён от его экземпляра; денежные пределы — от сроков; условие — от подтверждённого исполнения. Пробелы источников RC05 и последнего шаблона сохранены явно. JSON-карточки, новая runtime-схема, извлекатель, RAG, база данных, OCR, провайдеры и правовой Gold не создаются. Активный трек, канонический следующий шаг, заморозка внешних прогонов и границы приватности/безопасности не изменены.

Решение владельца от 2026-09-22: реальные анализы договоров и повторные full-contract прогоны временно приостановлены до создания и независимой проверки качественной базы экспертных знаний. Разрешены локальные синтетические/обезличенные fixture-тесты без внешнего API. PR #281 добавляет экспериментальный Expert Pack v0.1: CORE_PROTOCOL, MECHANISM_PLAYBOOK и 15 синтетических контрастных примеров; эти материалы не являются верифицированной юридической базой. Сохранён уже слитый PR #282 и все его требования контроля Codex. Область OCR, privacy/security, runtime и провайдеров не изменена.

PR #294 — по прямому поручению владельца собран один компактный обезличенный исследовательский пакет по девятистраничному частному договору: шесть взаимосвязанных печатных механизмов, возможные ошибки первого чтения и условия, меняющие первоначальный вывод. Рукописные поля только отмечены как зависимость и полностью исключены из смыслового анализа; значения, опись, оригинальные фотографии, имена и реквизиты не сохранены. Связь с семейством RC и источник независимой оценки не установлены; контрпримеры не являются наблюдёнными ошибками модели, юридическим Gold или production-правилами. Это разовое локальное содержательное исключение; канонический следующий шаг и запрет внешних прогонов реальных договоров сохраняются.

PR #295 — ещё одно ограниченное содержательное исключение: восемь обезличенных перекрёстных проверок печатных условий двух development-семейств TF_A (RC01/RC04 — два захвата одного договора) и TF_B (RC02/RC03 — разные редакции шаблона). Отдельно отмечены исправленная первоначальная гипотеза ассистента о роли сдающей стороны и семь предложенных контрольных ошибок, которые не являются наблюдёнными сбоями провайдера. Проект RC02 и ссылка на судебное дело не подтверждают исторические события; рукопись и подписи не анализировались. Источники, текст OCR, имена, номера документов и платёжные реквизиты не сохранялись; юридический Gold, обучение, независимая оценка и runtime не открыты. Канонический следующий шаг не меняется.

PR #296 — по поручению владельца выполнены полный печатный проход RC06 и короткая критическая сверка: семь обезличенных механизмов, развилки досрочного выезда и частичного возврата при повторной сдаче, разделение оплаты протечки и ремонта, пакет обеспечений, опция, ошибочная перекрёстная ссылка и отдельный слой финансовых/религиозных условий. Страницы PDF переставлены, но печатная последовательность пунктов восстановлена по видимой нумерации; рукописные значения и подписи полностью исключены. Поскольку TF_C/RC06 содержательно изучен, он переведён из резерва независимого теста в development research; TF_D/RC07 остаётся нетронутым резервом. Это не делает RC06 обучающим материалом или Gold. Оригинал, OCR, персональные данные и реквизиты не сохранены; runtime и канонический следующий шаг не меняются.

PR #297 — устранено расхождение текущей карты покрытия с уже опубликованными обезличенными пакетами и семейным split: RC01–RC04 имеют печатные исследовательские сверки, RC06 — семь печатных механизмов; RC05 не имеет в репозитории пакета с привязкой к оригиналу, RC07 остаётся неизученным резервом. Семейства TF_A–TF_D и research/holdout назначение отражены в coverage-файле и сверяются валидаторами; инвентарь от 23.09 остаётся историческим техническим снимком. Gold, обучение, независимая оценка, приватность, runtime и канонический следующий шаг не меняются.

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

## 8. Canonical next step — independent Router diagnostic

`next_step_id = expert-memory-router-blind-synthetic-evaluation-v1`

**Freeze remains:** no new full real-contract external-LLM/OCR/provider calls. No raw private originals, recoverable PII, signed names/IDs, page images, original source names or hashes in GitHub, CI, logs or RAG. The sanitized three-page printed `contract_001` and privately held source photographs can be compared locally for this step; private source data is not persisted in the repository.

**PR #292 delivered:** a second, owner-directed critical pass containing **15** cross-clause mechanisms backed by **55** exact short Hebrew quotes from the sanitized printed source, plus a clause-sequence integrity check. It adds the unverified property inventory, the signature-date trigger for arnona notice, and the special agreed-occupant term; separates early exit, post-term holdover and security realization; and narrows repair set-off to all three written preconditions. `8.ב` is not reconstructed. This research is not an observation of a model failure, an original-court holding or reviewed legal Gold.

**Unresolved:** local OCR strongly aligns three private source photographs with the sanitized Golden Fixture, and TF_C is a strong printed-template candidate. An assistant visual check now supports the selected material printed anchors, including clause 12, but does not certify every character. The original is not positively mapped to an exact private RC PDF/group; canonical `linked_family` remains UNKNOWN (RC07 is excluded as a direct source). Appendix B, handwritten fields and signatures were excluded from semantic use, so their original contents and any amendments are not known. PR #291 originally reserved TF_C and TF_D as independent-test families; after the owner-directed RC06 review in #296 and RC07 review in #299, both are development research. No unexposed independent test family remains among RC01–RC07. The unlinked Golden Fixture is NOT eligible for training or cohort scoring. Owner Hebrew reading is not required for the next synthetic Router experiment.

**PR #293 — bounded research exception:** three dated source-scoped and unverified statute-crosscheck hypotheses now cover actual tenant option versus renewed consent (§25יב), regular/urgent/emergency repair and undisclosed defects (§§8–9, 25ח), and financially burdensome security caps versus general realization/notice/return for an ordinary cheque (§25י). The 2026 licensed-provider amendment is future-effective only from 2026-09-30. No legal Gold or production authorization follows from this research.

**PR #294 — bounded printed-contract research exception:** one sanitized packet records six mechanism variants and candidate first-read errors from a private nine-page lease. All handwritten content is excluded from semantic use; no source images, raw OCR, PII or instrument identifiers are persisted. Its private source/template-family link is UNKNOWN, and neither candidate error nor legal proposition is Gold, training, evaluation or runtime data. The canonical next step and external-provider freeze remain unchanged.

**PR #295 — bounded two-family printed crosscheck exception:** eight sanitized crosschecks cover TF_A/RC01–RC04 and TF_B/RC02–RC03. TF_A captures count as one content instance; TF_B editions remain one development family. One assistant first-pass role inference was corrected in the short check; seven other first-read traps are candidate controls only. RC02 is an unsigned draft, the referenced court event and actual cheque return are unverified, and RC03 execution is not established by the printed text alone. Handwriting is fully excluded from semantic use. No legal Gold, training, independent evaluation, source media, raw OCR, PII or runtime integration; the canonical next step and provider freeze remain unchanged.

**PR #296 — bounded RC06 printed-content exception:** seven sanitized mechanisms are derived from one visual pass and a short critical check. The PDF's page order differs from the clause sequence; no handwritten field or signature content is used. RC06/TF_C is reclassified as development research following exposure, not as training or verified labels. RC07/TF_D alone remains reserved for independent testing. The historical 2026-09-23 split was updated with a documented reason, validator and regression; family links otherwise remain unchanged. No original, raw OCR, PII, legal Gold, external provider or runtime integration. The canonical next step and freeze remain unchanged.

**PR #297 — coverage/cohort corrective follow-up:** the current `real_contract_coverage_v1.json` now reflects TF_A–TF_D and printed research for RC01–RC04 and RC06. RC05 remains without a repository source-anchored mechanism packet; RC07 remains unreviewed independent-test reserve. The 2026-09-23 inventory is explicitly historical. Both coverage and split validators reject stale family/cohort assignments. No legal Gold, training, independent scoring, raw source, runtime or external-provider change; canonical next step unchanged.

**PR #299 — RC05/RC07 candidate errors and cohort sync:** six candidate first-read traps for each contract are source-scoped with printed clause locators and missing-fact boundaries. They are not observed external-model errors or verified labels. RC05 no longer lacks a printed research packet; TF_D/RC07 is exposed development research after manual review. All four families are now exposed, leaving no independent test among the supplied RC groups. The historical inventory is unchanged. Coverage, split, validators and ontology snapshot addendum reflect the new status, while the canonical next step and all privacy, provider and runtime gates remain unchanged.

**PR #300 — ontology inventory reconciliation exception:** all 12 RC05/RC07 packet mechanisms are mapped once to the original 30 candidate concepts or marked as a bounded gap. The 30 definitions and nine original temporal roles remain a dated snapshot. RC05 provides a printed example of a cure period after written rent demand; RC07 distinguishes a standing-order-triggered cheque return and an explicitly incorporated but unavailable document. Candidate gaps are not automatically new concepts or expert-verified labels. No cards, ontology JSON, extractor, runtime, external provider or canonical-next-step change.

**PR #301 — glossary core decisions exception:** `DOCUMENT_REFERENCE` records the stated document relation and whether its text was supplied, without inferring contents; `REPAIR_COST_RECOVERY` preserves the repair obligor and direction of a possible cost claim. Original candidate #14 stays tenant-specific in the dated inventory. These are working research terms, not formal cards or verified labels. No runtime, external provider, privacy or canonical-next-step change.

**PR #302 — five draft SECURITY cards exception:** inventory candidates #08–12 now have six-field research JSON cards and a separate source-locator registry. Their slots are questions about a target instance, not extracted values; links to other inventory candidates do not formalize those concepts. Four source-scoped ambiguity controls cover instrument identity, RC06 cap scope, RC03 return deadline scope, and delivery versus use. No source-family signoff, Gold, training, runtime, external provider, privacy or canonical-next-step change.

**PR #304 — assistant visual check and nonblind Router smoke:** three original photographs were inspected privately. The printed `8.א` to `9.א` sequence and selected material clauses, including §12, support the sanitized fixture without a material discrepancy found. Exact full transcription, unseen Appendix B and direct RC PDF identity are still unverified. A 43-block nonblind assistant trace exercises the proposed first-pass families, preserves meaningful `OTHER`, excludes the signature marker and identifies six cross-clause dependencies for the second pass. Its validator checks structured coverage and prohibited generated quotes; it does not measure model accuracy or authorize Gold, training, external real-contract calls or runtime use.

**PR #306 — user-reported RC07 Gemini trace:** one sanitized QA note separates the prompted 6/13 pair from autonomous link discovery, identifies unsupported inferences about notice dispatch, replacement release and security retention, and records possible missed links without scoring. Model variant and exact full prompt are not archived; this retrospectively records the owner's supplied output and does not authorize further real-contract provider runs, change the Router/core inventory or promote RC07 to Gold.

**PR #307 — in-force institutional guarantee boundary:** the dated 2026 security overlay is now marked in force from 2026-09-30, while expert verification and production wiring remain false. One research `INSTITUTIONAL_GUARANTEE` subtype remains under Router family `SECURITY`; distinct-instrument and unresolved-cap boundaries are regression-tested.

**Next bounded step:** `expert-memory-router-blind-synthetic-evaluation-v1`. Prepare fresh synthetic printed clauses with a concealed reference routing set, run a separate model context using the same portable first-pass JSON contract, then record missing and excess families and whether necessary linked clauses survive the second pass. Do not call an external provider with a real contract, infer an independent score from the same-assistant trace or promote the unresolved source family to training/holdout use. Exact private PDF identity remains an open provenance question, not a prerequisite for this synthetic experiment.

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

Every PR: exactly one Context Gate v1; both state files updated; final checks apply to the exact final head; actual paths exactly match the Context Gate; mandatory final-diff security review. GitHub auto-merge remains disabled; the orchestrating assistant may merge an authorized PR after the gates pass without a second owner command, unless the owner explicitly holds it.
