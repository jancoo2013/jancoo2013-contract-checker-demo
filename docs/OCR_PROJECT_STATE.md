# OCR Project State & Continuity v0

Последнее обновление: 2026-08-04, PR #183, `android-tesseract-development-overlay-v1`.

Активный трек: `local-pii-redaction`.

Единственный следующий шаг: `android-tesseract-development-overlay-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Архитектуру задают `docs/ARCHITECTURE.md` и `docs/CUSTOM_OCR_PIPELINE.md`; evidence/masking contract задаёт `docs/PII_EVIDENCE_DETECTOR_V1.md`; машиночитаемое состояние хранится в `docs/OCR_PROJECT_STATE.json`. Подробная история до PR #183 остаётся в Git history и намеренно не дублируется здесь.

## 0. Изменение PR #183

- Добавлен bounded development-only overlay layout поверх trusted candidate geometry PR #182.
- `buildTesseractDevelopmentOverlay` принимает только geometry, созданную доверенным builder, и преобразует exact per-word boxes в contain-fit viewport с корректными letterbox offsets.
- RTL boxes остаются отдельными прямоугольниками; diagnostic `enclosingBbox` намеренно не входит в overlay output и не может случайно закрыть промежутки между словами.
- Overlay имеет фиксированную прозрачность `0.35`, помечен `developmentOnly: true`, возвращает immutable координаты и не содержит OCR text, matched PII value, source offsets или confidence.
- Forged geometry, zero/negative/NaN/infinite viewport dimensions fail closed. Synthetic tests покрывают scaling, letterboxing, RTL order, value-free output и deep immutability.
- Локально проходят `16/16` focused mapping/geometry/overlay tests и strict TypeScript check. Полный mobile/Android CI относится к exact final head SHA PR #183.
- PR не изменяет пиксели изображения, не создаёт production derivative, не добавляет detector orchestration, disposition authorization, UI integration, persistence, transport, dependencies, external OCR/LLM, реальные договоры или реальные PII.
- По merge-gated workflow `next_step_id` остаётся `android-tesseract-development-overlay-v1` до merge PR #183 и нового чтения resulting `main`. Следующий bounded slice может отдельно определить полностью непрозрачный необратимый production renderer.

### PR #182 — `android-tesseract-candidate-geometry-v1`

- Trusted same-line mapping преобразуется в immutable exact per-word geometry с line/gap/bounds gates.
- `enclosingBbox` остаётся только диагностическим и не является production mask geometry.
- Geometry сама по себе не авторизует mask/disposition и не доказывает real PII recall.

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
| Android candidate geometry | PR #182 | Trusted exact box group, line/gap/bounds gates, diagnostic enclosing bbox | Real correctness and detector orchestration |
| Android development overlay | PR #183 | Trusted contain-fit per-word rectangles, fixed `0.35` opacity, value-free output | UI integration and production privacy safety |
| Local mask renderer | Python reference v0 | Opaque irreversible grayscale replacement | Android implementation and candidate correctness |
| Android detector/renderer | Не реализован | — | Automatic evidence detection and masking |
| External OCR handoff | Не подключён | Допустим только после privacy gate | Derivative safety не доказана |

## 4. Активный блокер

Reference evidence chain и Android Tesseract geometry пока не соединены в один runtime detector. PR #183 добавляет только обратимый development overlay для уже trusted geometry. Он не доказывает, что upstream detector нашёл все PII, не меняет пиксели и не создаёт production mask/disposition.

До production остаются отдельные bounded задачи:

1. связать approved direct-value finder provenance с Android span mapping;
2. сделать production renderer полностью непрозрачным и необратимым;
3. добавить local privacy validation и fail-closed handoff gate;
4. проверить real-contract recall, complete coverage и over-redaction на whole-contract held-out evaluation.

## 5. Единственный следующий шаг

**`android-tesseract-development-overlay-v1`: MERGE-GATED — реализован в PR #183 и остаётся каноническим идентификатором до merge и нового чтения resulting `main`.**

До merge PR #183 запрещено добавлять production pixel replacement, UI/runtime integration, detector orchestration, external APIs, dependencies или реальные данные. После merge нужно заново прочитать exact resulting `main`, проверить final-head CI и только затем выбрать отдельный bounded production renderer с полностью непрозрачной необратимой заменой пикселей.

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
