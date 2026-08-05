# OCR Project State & Continuity v0

Последнее обновление: 2026-08-05, PR #185, `android-tesseract-development-overlay-ui-v1`.

Активный трек: `local-pii-redaction`.

Единственный следующий шаг: `android-tesseract-development-overlay-ui-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Архитектуру задают `docs/ARCHITECTURE.md` и `docs/CUSTOM_OCR_PIPELINE.md`; evidence/masking contract задаёт `docs/PII_EVIDENCE_DETECTOR_V1.md`; машиночитаемое состояние хранится в `docs/OCR_PROJECT_STATE.json`. Подробная история до PR #185 остаётся в Git history и намеренно не дублируется здесь.

## 0. Изменение PR #185

- Добавлен bounded development-only UI поверх реального локального Android Tesseract pass и выбранного на устройстве изображения.
- `buildTesseractDevelopmentInspectionOverlay` повторно валидирует OCR result и пропускает каждый реальный word box через существующую trusted цепочку: text index → exact span mapping → candidate geometry → development overlay.
- На contain-fit preview рисуются красные полупрозрачные прямоугольники с фиксированной opacity `0.35`; React Native layout используется для расчёта фактических размеров viewport и letterbox offsets.
- UI показывает количество прямоугольников и позволяет скрыть/показать overlay.
- Overlay намеренно покрывает все validated OCR word boxes. Это режим проверки геометрии, а не detector output, PII classification, disposition или разрешение маски.
- Output помечен `developmentOnly: true`, `inspectionOnly: "all-ocr-word-boxes"` и `notPiiDecision: true`; он не содержит OCR text, confidence, source offsets или diagnostic `enclosingBbox`.
- Выбранное изображение, overlay и координаты не сохраняются как derivative и не отправляются наружу. Отдельный существующий backend smoke-test по-прежнему отправляет только bundled synthetic redacted PNG.
- Локально проходят `5/5` focused inspection-overlay tests и strict TypeScript check. Полный mobile/Android CI относится к exact final head SHA PR #185.
- После merge обязательна ручная проверка на целевом Android-устройстве: масштаб, orientation/EXIF, letterboxing, смещение, clipping и соответствие прямоугольников реальным словам.
- По merge-gated workflow `next_step_id` остаётся `android-tesseract-development-overlay-ui-v1` до merge PR #185, нового чтения resulting `main` и визуального device review.

### PR #184 — закрыт без merge

- `android-tesseract-production-mask-renderer-v1` был признан преждевременным.
- Непрозрачный renderer нельзя возвращать в план до визуального подтверждения корректности полупрозрачного overlay на реальных локальных изображениях.

### PR #183 — `android-tesseract-development-overlay-v1`

- Trusted candidate geometry преобразуется в immutable contain-fit per-word rectangles с opacity `0.35`.
- RTL boxes остаются раздельными; diagnostic `enclosingBbox` не входит в output.
- Это только математический reversible overlay layout без UI и без production pixel replacement.

## 1. Актуальная Android/Tesseract цепочка

| PR | Изменение | Доказано | Не доказано |
|---|---|---|---|
| #179 | Direct-value provenance adapter | Exact class/detector/start/end совпадение с approved finder | Android orchestration и real recall |
| #180 | Android Tesseract word boxes | Bounded text/confidence/in-bounds bbox, bridge validation | Real-contract recall и target-device correctness |
| #181 | Text span → word boxes | Trusted exact same-line mapping, cross-line fail closed | Approved finder orchestration |
| #182 | Candidate geometry | Immutable separate boxes, line/gap/bounds gates | Candidate correctness на реальных договорах |
| #183 | Development overlay layout | Contain-fit exact rectangles, opacity `0.35`, value-free output | Реальное UI alignment |
| #185 | Development inspection UI | Реальное локальное изображение + все validated OCR word boxes, show/hide | PII selection, complete recall и device visual verdict |

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
- alpha layers, overlays, metadata и другие обратимые способы скрытия запрещены для production handoff;
- development overlay разрешён только для локальной визуальной проверки и не является anonymized derivative;
- page position, page number, alignment и наличие цифр являются только weak context и не дают `auto_mask`;
- monetary amounts, dates, clause numbers и notice periods не считаются PII только из-за цифр;
- fuzzy matching запрещён для PII authorization;
- geometry/UI сами по себе не авторизуют маску и не доказывают complete PII coverage;
- при неполной evidence, geometry или validation внешний handoff блокируется.

## 3. Реальное состояние компонентов

| Компонент | Состояние | Доказано | Не доказано |
|---|---|---|---|
| Reference evidence chain | Python v0/v1 | Pattern, marker/value, provenance и deterministic dispositions | Android runtime orchestration |
| Android Tesseract words | Runtime slice v1 | Bounded local OCR word text/confidence/bbox | Real recall и device visual correctness |
| Android span mapping | Runtime slice v1 | Exact same-line span → trusted word boxes | Approved finder binding |
| Android candidate geometry | PR #182 | Separate exact boxes и fail-closed geometry gates | Real candidate correctness |
| Development overlay layout | PR #183 | Trusted contain-fit value-free rectangles | Real screen alignment |
| Development overlay UI | PR #185 | Локальный preview и all-word geometry inspection | Device review и PII correctness |
| Production mask renderer | Не реализован в `main`; PR #184 закрыт | — | Непрозрачная необратимая Android-маска |
| Local privacy validator | Не реализован | — | Complete coverage и fail-closed handoff |
| External OCR handoff | Не подключён | Допустим только после privacy gate | Derivative safety |

## 4. Активный блокер

До PR #185 геометрия была проверена только синтетическими тестами. Теперь код может показать её на реальном локальном изображении, но корректность ещё должна быть подтверждена глазами на целевом телефоне.

Device review должен ответить:

1. совпадает ли каждый прямоугольник с соответствующим OCR-словом;
2. нет ли системного смещения по X/Y;
3. корректны ли portrait/landscape и EXIF orientation;
4. совпадает ли contain scaling с реальным preview;
5. не обрезаются ли прямоугольники у краёв;
6. остаётся ли результат стабильным на нескольких разрешениях и фотографиях.

Даже идеальный all-word overlay не доказывает PII recall: detector orchestration пока не подключена.

## 5. Единственный следующий шаг

**`android-tesseract-development-overlay-ui-v1`: MERGE-GATED — реализован в PR #185 и остаётся каноническим идентификатором до merge, нового чтения resulting `main` и ручного device review.**

До визуального review запрещено возвращаться к opaque production renderer, добавлять external handoff или утверждать, что маскирование работает корректно. После merge PR #185 нужно собрать/запустить Android development build, проверить несколько локальных тестовых изображений и зафиксировать реальные ошибки alignment. Только по результатам review выбирается следующий bounded PR: исправление координат либо подключение approved detector span к уже проверенному overlay.

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

Cold-start repository audit проводится каждые 3–5 слитых privacy/OCR PR либо раньше при конфликте binding documents. Последний полный audit: PR #177 после merge PR #176; найденный direct-match integrity blocker затем закрыт PR #178–#179.
