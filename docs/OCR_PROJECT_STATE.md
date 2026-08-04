# OCR Project State & Continuity v0

Последнее обновление: 2026-08-04, PR #182, `android-tesseract-candidate-geometry-v1`.

Активный трек: `local-pii-redaction`.

Единственный следующий шаг: `android-tesseract-candidate-geometry-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Архитектуру задают `docs/ARCHITECTURE.md` и `docs/CUSTOM_OCR_PIPELINE.md`; evidence/masking contract задаёт `docs/PII_EVIDENCE_DETECTOR_V1.md`; машиночитаемое состояние хранится в `docs/OCR_PROJECT_STATE.json`. Подробная история до PR #182 остаётся в Git history и намеренно не дублируется здесь.

## 0. Изменение PR #182

- Добавлен bounded Android/TypeScript geometry layer поверх trusted mapping PR #181.
- `buildTesseractCandidateGeometry` принимает только mapping, созданный доверенным mapper, и сохраняет exact per-word `bbox` отдельными immutable прямоугольниками.
- Дополнительный `enclosingBbox` предназначен только для диагностики. Он не является production mask geometry и не должен закрывать промежутки между словами.
- Геометрия fail closed отклоняет forged mapping, пустой или несогласованный word range, duplicate/non-consecutive word indexes, out-of-image boxes, отсутствие общей вертикальной text-line band и горизонтальный gap больше двух высот соседних word boxes.
- Output не содержит OCR text, matched PII value, source offsets или confidence. Добавленные synthetic tests покрывают RTL multi-box, single-box, different-line, unsafe-gap, forged-input и immutable/value-free output.
- Локально проходят `12/12` dependency-free mobile tests и strict TypeScript check. Финальный Android CI относится к exact final head SHA PR #182.
- PR не добавляет detector orchestration, evidence/dispositions, masks, renderer, UI, persistence, transport, dependencies, external OCR/LLM, реальные договоры или реальные PII.
- По merge-gated workflow `next_step_id` остаётся `android-tesseract-candidate-geometry-v1` до merge PR #182 и нового чтения resulting `main`. Только после этого можно отдельно выбрать development mask rendering: полупрозрачное отображение для визуальной проверки и непрозрачная необратимая production-маска.

## 1. Недавняя Android/Tesseract цепочка

### PR #181 — `android-tesseract-word-span-mapping-v1`

- Точный request-local Tesseract full text индексируется по validated iterator-order word boxes без синтетической склейки строк.
- Один caller-confirmed same-line span преобразуется в exact overlapping word indexes, confidence и immutable pixel bboxes.
- Cross-line spans, malformed offsets, forged indexes, inconsistent full-text alignment и более 64 boxes отклоняются.
- Mapping является только геометрической ссылкой и сам по себе не разрешает маску.

### PR #180 — `android-tesseract-word-boxes-v1`

- Существующий on-device Tesseract pass возвращает bounded word text, confidence и in-bounds bbox без второго OCR pass.
- Native iterator cleanup, TypeScript runtime validation, synthetic tests и Android debug build подтверждены.
- Реальные recall, complete PII coverage, device smoke и production privacy safety не доказаны.

### PR #179 — `pii-direct-value-match-provenance-v1`

- Python reference adapter повторно запускает approved direct-value finder на caller-supplied local source text.
- Candidate допускается только при exact совпадении class, detector ID, start и end с finder-produced match.
- Source text, raw PII value и offsets не сохраняются в candidate/evidence output.

## 2. Privacy boundary

```text
raw phone photo
→ on-device preprocessing
→ on-device PII evidence detection
→ local candidate geometry
→ irreversible local masks
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
- page position, page number, alignment и наличие цифр являются только weak context и не дают `auto_mask`;
- monetary amounts, dates, clause numbers и notice periods не считаются PII только из-за цифр;
- fuzzy matching запрещён для PII authorization;
- при неполной evidence или geometry внешний handoff блокируется.

## 3. Реальное состояние компонентов

| Компонент | Состояние | Доказано | Не доказано |
|---|---|---|---|
| Page normalization | Python reference v0 | Bounded grayscale master и synthetic tests | Android production capture quality |
| Line segmentation | Python reference v0 + giant-band guard | Bounded sparse-row expansion и oversized-band fail closed | Новый real review pack и повторная over-redaction диагностика |
| Candidate/evidence schema | Python reference v1 | Closed classes/dispositions/families, class-bound strong evidence, geometry gates | Runtime integration и production safety |
| Direct PII patterns | Python reference v0 | Email, Israeli phone, check-digit ID, Israeli IBAN; ambiguous numeric rejection | Real recall и cross-contract generalization |
| Marker/value relations | Python reference v0 | Approved markers, same-line bounded relation, class compatibility | Android/runtime integration |
| Visual evidence | Python reference v0 | Closed caller-prevalidated kinds and in-bounds geometry | Pixel classifier for handwriting/signatures/stamps |
| Evidence decision adapters | Python reference v0/v1 | Provenance, structural gates, deterministic dispositions | Working detector orchestration |
| Android Tesseract words | Runtime slice v1 | Bounded text/confidence/bbox and bridge validation | Real geometry/recall and device smoke |
| Android span mapping | Runtime slice v1 | Exact same-line span → trusted word boxes, value-free output | Approved finder orchestration |
| Android candidate geometry | PR #182 | Trusted exact box group, line/gap/bounds gates, diagnostic enclosing bbox | Mask rendering and real correctness |
| Local mask renderer | Python reference v0 | Opaque irreversible grayscale replacement | Android implementation and candidate correctness |
| Android detector/renderer | Не реализован | — | Automatic evidence detection and masking |
| External OCR handoff | Не подключён | Допустим только после privacy gate | Derivative safety не доказана |

## 4. Активный блокер

Reference evidence chain и Android Tesseract geometry пока не соединены в один runtime detector. PR #182 решает только безопасное представление геометрии уже подтверждённого same-line span. Он не доказывает, что upstream detector нашёл все PII, и не создаёт mask/disposition.

До production остаются отдельные bounded задачи:

1. связать approved direct-value finder provenance с Android span mapping;
2. определить development-only renderer точных word boxes;
3. сделать production renderer полностью непрозрачным и необратимым;
4. добавить local privacy validation и fail-closed handoff gate;
5. проверить real-contract recall, complete coverage и over-redaction на whole-contract held-out evaluation.

## 5. Единственный следующий шаг

**`android-tesseract-candidate-geometry-v1`: MERGE-GATED — реализован в PR #182 и остаётся каноническим идентификатором до merge и нового чтения resulting `main`.**

До merge PR #182 запрещено добавлять masks, renderer/UI integration, detector orchestration, external APIs, dependencies или реальные данные. После merge нужно заново прочитать exact resulting `main`, проверить final-head CI и только затем выбрать следующий bounded slice. Предпочтительный следующий кандидат — development renderer точных word boxes с полупрозрачным отображением; production output при этом должен оставаться полностью непрозрачным и необратимым.

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
