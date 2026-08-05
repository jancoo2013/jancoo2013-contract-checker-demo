# OCR Project State & Continuity v0

Последнее обновление: 2026-08-05, PR #186, `android-tesseract-pii-candidate-overlay-v1`.

Активный трек: `local-pii-redaction`.

Единственный следующий шаг: `android-tesseract-pii-candidate-overlay-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Архитектуру задают `docs/ARCHITECTURE.md` и `docs/CUSTOM_OCR_PIPELINE.md`; evidence/masking contract задаёт `docs/PII_EVIDENCE_DETECTOR_V1.md`; машиночитаемое состояние хранится в `docs/OCR_PROJECT_STATE.json`. Подробная история до PR #186 остаётся в Git history.

## 0. Изменение PR #186

- Добавлен Android/TypeScript parity-port approved Python direct-value finder для четырёх high-confidence классов: `email`, Israeli `phone`, checksum-valid `israeli_id`, checksum-valid Israeli `bank_identifier`/IL IBAN.
- Сохранены канонические detector IDs, приоритет классов, overlap suppression, exact source spans и fail-closed rejection числовых подстрок внутри более длинных separated tokens.
- Approved spans проходят существующую trusted цепочку: Tesseract full-text index → exact span-to-word-box mapping → candidate geometry → contain-fit development overlay.
- Development UI по умолчанию показывает полупрозрачные прямоугольники только для approved direct-value candidates и выводит value-free counts по классам.
- Режим всех OCR word boxes PR #185 сохранён отдельным development-переключателем для технической диагностики геометрии.
- Candidate overlay не содержит matched value, source offsets, confidence или detector ID; output помечен `developmentOnly`, `notMaskDecision` и `notCompletePiiCoverage`.
- Выбранное изображение, OCR result и overlay остаются локальными; derivative не создаётся и наружу не отправляется.
- Локально проходят `6/6` focused PII-candidate tests, `5/5` existing inspection-overlay tests и оба strict TypeScript checks.
- Ручная проверка на целевом Android-устройстве обязательна после merge: совпадение масок с email/phone/ID/IBAN, отсутствие системного смещения и корректность portrait/landscape/EXIF/letterboxing.

## 1. Актуальная Android/Tesseract цепочка

| PR | Изменение | Доказано | Не доказано |
|---|---|---|---|
| #179 | Direct-value provenance adapter | Exact class/detector/start/end совпадение с approved Python finder | Android orchestration и real recall |
| #180 | Android Tesseract word boxes | Bounded local text/confidence/in-bounds bbox | Real-contract recall и target-device correctness |
| #181 | Text span → word boxes | Exact same-line span mapping, cross-line fail closed | Approved finder runtime binding |
| #182 | Candidate geometry | Immutable separate boxes и geometry gates | Real candidate correctness |
| #183 | Development overlay layout | Contain-fit value-free rectangles, opacity `0.35` | Реальное UI alignment |
| #185 | All-word inspection UI | Реальное локальное изображение + every OCR word box | PII selection и device visual verdict |
| #186 | Direct PII candidate overlay | Approved direct finder parity + candidate-only default UI | Complete PII recall и production mask safety |

## 2. Privacy boundary

```text
raw phone photo
→ on-device preprocessing
→ on-device PII evidence detection
→ authorized local candidate geometry
→ irreversible local pixel replacement
→ local fail-closed privacy validation
→ anonymized derivative
→ approved external OCR
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
- при неполной evidence, geometry или validation внешний handoff блокируется.

## 3. Реальное состояние компонентов

| Компонент | Состояние | Доказано | Не доказано |
|---|---|---|---|
| Reference evidence chain | Python v0/v1 | Pattern, marker/value, provenance, deterministic dispositions | Полная Android orchestration |
| Android direct-value finder | PR #186 | Parity для email/phone/checksum ID/checksum IL IBAN | Real-contract recall |
| Android Tesseract words | Runtime slice v1 | Bounded local OCR word text/confidence/bbox | Target-device recall и orientation correctness |
| Span/geometry/overlay | PR #181–#183 | Exact word boxes и contain-fit rectangles | Device visual correctness |
| Development UI | PR #185–#186 | All-word diagnostic + direct-candidate default mode | Production UX и complete coverage |
| Production mask renderer | Не реализован в `main`; PR #184 закрыт | — | Непрозрачная необратимая Android-маска |
| Local privacy validator | Не реализован | — | Complete coverage и fail-closed handoff |
| External OCR handoff | Не подключён | Допустим только после privacy gate | Derivative safety |

## 4. Активный блокер

PR #186 делает ручной тест понятным без знания иврита: проверяются визуально узнаваемые email, телефоны, девятизначные ID и IL IBAN. Однако даже правильное попадание всех показанных прямоугольников не доказывает, что система нашла все PII на странице.

Device review должен ответить:

1. полностью ли прямоугольник закрывает найденное значение;
2. не смещены ли прямоугольники по X/Y;
3. корректны ли portrait/landscape и EXIF orientation;
4. не захватываются ли соседние слова или промежутки;
5. стабилен ли результат на нескольких разрешениях и фотографиях;
6. какие PII визуально присутствуют, но не были показаны candidate overlay.

## 5. Единственный следующий шаг

**`android-tesseract-pii-candidate-overlay-v1`: MERGE-GATED — реализован в PR #186.**

До merge, нового чтения resulting `main` и ручного device review запрещено возвращаться к opaque renderer, добавлять external handoff или утверждать, что маскирование работает корректно. После review выбирается один bounded шаг: исправление alignment/direct-pattern binding либо расширение approved evidence orchestration для marker/value и visual PII.

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
