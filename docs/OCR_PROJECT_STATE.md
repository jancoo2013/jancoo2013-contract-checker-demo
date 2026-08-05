# OCR Project State & Continuity v0

Последнее обновление: 2026-08-05, PR #188, `on-device-hebrew-ocr-replacement-audit-v1`.

Активный трек: `local-pii-redaction`.

Единственный следующий шаг: `android-mlkit-latin-direct-pii-spike-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Архитектуру задают `docs/ARCHITECTURE.md` и `docs/CUSTOM_OCR_PIPELINE.md`; evidence/masking contract задаёт `docs/PII_EVIDENCE_DETECTOR_V1.md`; машиночитаемое состояние хранится в `docs/OCR_PROJECT_STATE.json`. Подробная история до PR #187 остаётся в Git history.

## 0. Изменение PR #188

- Tesseract окончательно признан NO-GO для реальных фотографий ивритских договоров: ранее проверялись обе Hebrew-модели, а target-device интеграция подтвердила фактически непригодное распознавание.
- Повторять Tesseract `fast`/full, PSM, confidence tuning или preprocessing ради спасения этого OCR запрещено без нового явного решения владельца продукта.
- Surya исключена: текущая модель примерно 650M параметров и не имеет поддерживаемого Android deployment path для Samsung A55.
- PaddleOCR/PP-OCRv5 исключён как готовая замена: в актуальном официальном multilingual-наборе нет Hebrew recognizer.
- EasyOCR исключён: Hebrew не является доступной стандартной моделью, поддерживаемого Android product path нет.
- Полноценной готовой on-device Hebrew OCR-замены, удовлетворяющей всем MVP-ограничениям, аудит не нашёл.
- Единственный немедленный кандидат — bundled Google ML Kit Latin Text Recognition v2, но только для четырёх direct-value классов: email, Israeli phone, checksum Israeli ID, checksum IL IBAN.
- ML Kit Latin не считается Hebrew OCR и не закрывает имена, адреса, marker-value поля, подписи, печати или рукописные данные.
- Custom ONNX Runtime Mobile/LiteRT recognizer остаётся технически возможным отдельным research path, но не готовой заменой.

Полный отчёт: `docs/ON_DEVICE_HEBREW_OCR_REPLACEMENT_AUDIT_V1.md`.

## 1. Актуальная цепочка доказательств

| PR/аудит | Изменение | Доказано | Не доказано |
|---|---|---|---|
| #179 | Direct-value provenance adapter | Exact class/detector/start/end совпадение с approved Python finder | Android orchestration и real recall |
| #180 | Android Tesseract word boxes | Bounded local text/confidence/in-bounds bbox | Пригодное распознавание real photos |
| #181 | Text span → word boxes | Exact same-line span mapping, cross-line fail closed | Approved finder runtime binding |
| #182 | Candidate geometry | Immutable separate boxes и geometry gates | Real candidate correctness |
| #183 | Development overlay layout | Contain-fit value-free rectangles, opacity `0.35` | Реальное UI alignment |
| #185 | All-word inspection UI | Реальное локальное изображение + every OCR word box | PII selection и device visual verdict |
| #186 | Direct PII candidate overlay | Approved direct finder parity + candidate-only default UI | Complete PII recall и production mask safety |
| #187 | Real-photo OCR quality gate | Low-quality/ambiguous OCR blocks PII authorization before overlay | Улучшение OCR и real-photo candidate recall |
| #188 | On-device replacement audit | Tesseract/Surya/PaddleOCR/EasyOCR rejected; ML Kit Latin admitted only for direct values | Реальный ML Kit recall на mixed Hebrew pages |

## 2. Privacy boundary

```text
raw phone photo
→ local Latin/digit element recognition with geometry
→ deterministic direct-value PII checks
→ separate visual evidence paths for Hebrew fields/names/addresses/signatures/handwriting
→ irreversible local pixel replacement
→ local fail-closed privacy validation
→ anonymized derivative
→ approved external full Hebrew OCR
→ secondary text redaction
→ legal-risk analysis
→ Russian report
```

Обязательные инварианты:

- raw photos, recoverable pixels и unredacted OCR text не покидают устройство;
- наружу может уйти только irreversibly anonymized derivative после local privacy gate;
- alpha overlays разрешены только для локальной development-проверки и запрещены как production masking;
- page position, alignment и наличие цифр не дают `auto_mask`;
- суммы, даты, номера пунктов и notice periods не считаются PII только из-за числовой формы;
- fuzzy matching запрещён для PII authorization;
- direct-value overlay покрывает только четыре high-confidence класса и не доказывает complete PII coverage;
- geometry/UI сами по себе не авторизуют production mask;
- OCR completion не равно OCR usability;
- неподдерживаемый Hebrew script нельзя выдавать за Hebrew OCR;
- при низком качестве recognition, неоднозначной evidence, geometry или validation внешний handoff блокируется.

## 3. Реальное состояние компонентов

| Компонент | Состояние | Доказано | Не доказано |
|---|---|---|---|
| Reference evidence chain | Python v0/v1 | Pattern, marker/value, provenance, deterministic dispositions | Полная Android orchestration |
| Android direct-value finder | PR #186 | Parity для email/phone/checksum ID/checksum IL IBAN | Real-contract recall |
| Android Tesseract | Retired NO-GO | Real-photo failure and fail-closed quality block | Ничего больше не исследуется в active MVP |
| ML Kit Latin direct-value path | Не реализован | Official on-device Android API, geometry and Latin/digit capability | Recall на mixed Hebrew contract photos |
| Hebrew names/addresses/signatures | Не реализованы | Требуются отдельные evidence paths | Модель, recall и production safety |
| Custom ONNX/LiteRT recognizer | Paused research option | Android deployment substrates exist | Suitable model, memory, latency, accuracy |
| Production mask renderer | Не реализован в `main`; PR #184 закрыт | — | Непрозрачная необратимая Android-маска |
| Local privacy validator | Не реализован | — | Complete coverage и fail-closed handoff |
| External OCR handoff | Не подключён | Допустим только после privacy gate | Derivative safety |

## 4. Активный блокер

Готового локального full-page Hebrew OCR для Samsung A55 в утверждённом стеке нет. Это больше не задача «подкрутить качество Tesseract».

Ближайшая проверяемая гипотеза уже: может ли небольшой официальный Android recognizer, не понимающий Hebrew script, надёжно извлечь расположенные внутри ивритской страницы прямые значения из цифр и латиницы.

Даже успешный результат не закроет complete PII coverage. Имена, адреса, подписи и рукопись останутся отдельным обязательным блокером.

## 5. Единственный следующий шаг

**`android-mlkit-latin-direct-pii-spike-v1`.**

Разрешённый bounded scope:

1. bundled ML Kit Latin recognizer только в development Android path;
2. тот же selected-image локальный сценарий;
3. adapter из Latin/digit elements + geometry в существующий direct-value contract;
4. только email/phone/checksum ID/checksum IL IBAN;
5. development overlay и value-free diagnostics;
6. без Tesseract fallback, Hebrew marker inference, production masks и external handoff.

Target-device go/no-go выполняется на Samsung A55 и реальных локальных фотографиях. Если direct-value recall остаётся непригодным, поиск взаимозаменяемых готовых OCR прекращается; следующим решением становится custom narrow ONNX/LiteRT model либо изменение privacy workflow.

## 6. Правила восстановления и работы

Перед новой privacy/OCR веткой:

1. прочитать `AGENTS.md`, architecture/pipeline contracts и оба state-файла с актуального `main`;
2. проверить отсутствие пересекающегося PR;
3. опубликовать один exact Context Gate v1;
4. менять только declared paths и текущий bounded step;
5. открыть draft PR, затем обновить оба state-файла фактическим номером;
6. выполнить focused tests и финальные checks на exact final head SHA;
7. проверить diff, state continuity, generated files и отсутствие auto-merge;
8. не merge без явного решения владельца продукта.

Последний полный cold-start audit: PR #177 после merge PR #176; найденный direct-match integrity blocker закрыт PR #178–#179.
