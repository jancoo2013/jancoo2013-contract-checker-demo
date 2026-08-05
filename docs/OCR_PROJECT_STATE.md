# OCR Project State & Continuity v0

Последнее обновление: 2026-08-05, PR #187, `android-tesseract-real-photo-quality-gate-v1`.

Активный трек: `local-pii-redaction`.

Единственный следующий шаг: `android-tesseract-real-photo-quality-gate-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Архитектуру задают `docs/ARCHITECTURE.md` и `docs/CUSTOM_OCR_PIPELINE.md`; evidence/masking contract задаёт `docs/PII_EVIDENCE_DETECTOR_V1.md`; машиночитаемое состояние хранится в `docs/OCR_PROJECT_STATE.json`. Подробная история до PR #187 остаётся в Git history.

## 0. Изменение PR #187

- Первый целевой device review после merge PR #186 выполнен на реальной фотографии договора.
- Native Tesseract завершил вызов, но вернул непригодный для PII-авторизации результат: mean confidence `38`, `324` word boxes и один `RIL_WORD` box с внутренним whitespace.
- До PR #187 приложение показывало общий OCR status `success`, после чего candidate overlay падал позже с технической ошибкой `Tesseract word box ... contains whitespace`.
- Добавлен value-free fail-closed quality gate перед любым PII candidate overlay.
- Gate блокирует masking authorization, если:
  - Tesseract не вернул word boxes;
  - mean confidence ниже provisional development threshold `60`;
  - хотя бы один word box содержит внутренний whitespace и поэтому неоднозначен для exact text-span mapping.
- Блокировка возвращает явное сообщение `OCR unusable — masking blocked` с безопасными диагностическими числами и reason codes; OCR text и matched PII values в diagnostic assessment не сохраняются.
- Низкокачественный или неоднозначный OCR больше не может выглядеть как успешный masking pass.
- Выбранное изображение и OCR остаются локальными; derivative не создаётся, наружу ничего не отправляется.
- Этот PR не улучшает распознавание, не меняет модель `heb.traineddata`, `PSM_AUTO`, preprocessing, orientation, crop, contrast или page segmentation.

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
| #187 | Real-photo OCR quality gate | Low-quality/ambiguous OCR blocks PII authorization before overlay | Улучшение OCR и real-photo candidate recall |

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
- OCR completion не равно OCR usability;
- при низком качестве OCR, неоднозначной evidence, geometry или validation внешний handoff блокируется.

## 3. Реальное состояние компонентов

| Компонент | Состояние | Доказано | Не доказано |
|---|---|---|---|
| Reference evidence chain | Python v0/v1 | Pattern, marker/value, provenance, deterministic dispositions | Полная Android orchestration |
| Android direct-value finder | PR #186 | Parity для email/phone/checksum ID/checksum IL IBAN | Real-contract recall |
| Android Tesseract words | Runtime slice v1 | Bounded local OCR word text/confidence/bbox | Пригодное распознавание real photos |
| OCR quality gate | PR #187 | Explicit fail-closed block for empty/low-confidence/ambiguous result | Правильность threshold для всех камер и документов |
| Span/geometry/overlay | PR #181–#183 | Exact word boxes и contain-fit rectangles | Device visual correctness на usable OCR |
| Development UI | PR #185–#187 | All-word diagnostic, direct-candidate mode, explicit quality block | Production UX и complete coverage |
| Production mask renderer | Не реализован в `main`; PR #184 закрыт | — | Непрозрачная необратимая Android-маска |
| Local privacy validator | Не реализован | — | Complete coverage и fail-closed handoff |
| External OCR handoff | Не подключён | Допустим только после privacy gate | Derivative safety |

## 4. Активный блокер

Реальный device review показал, что текущий полноформатный Tesseract pass по фотографии страницы непригоден для PII detection: распознанный текст искажен, mean confidence равен `38`, а exact word mapping встречает неоднозначный whitespace-bearing box.

PR #187 исправляет только ложный статус успеха и делает блокировку явной. Он намеренно не пытается «спасти» мусорный OCR и не ослабляет exact mapping ради появления прямоугольников.

После merge повторный тест той же фотографии должен подтвердить:

1. экран больше не показывает masking pass как `success`;
2. candidate overlay не строится;
3. пользователь получает `OCR unusable — masking blocked`;
4. диагностическое сообщение содержит только confidence/threshold/counts/reasons и не содержит OCR text или PII values;
5. прежняя техническая ошибка про конкретный word-box не является основным user-facing результатом.

## 5. Единственный следующий шаг

**`android-tesseract-real-photo-quality-gate-v1`: MERGE-GATED — PR #187.**

До merge, нового чтения resulting `main` и повторного target-device теста запрещено возвращаться к opaque renderer, добавлять external handoff или утверждать, что локальное PII-маскирование работает.

После успешного retest выбирается отдельный bounded шаг по OCR input quality. Наиболее вероятный следующий слой: локальное определение/выравнивание страницы, ориентация и контролируемая подготовка изображения перед Tesseract. Он не входит в PR #187.

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
