# OCR Project State & Continuity v0

Последнее обновление: 2026-08-05, PR #184, `android-tesseract-production-mask-renderer-v1`.

Активный трек: `local-pii-redaction`.

Единственный следующий шаг: `android-tesseract-production-mask-renderer-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Архитектуру задают `docs/ARCHITECTURE.md` и `docs/CUSTOM_OCR_PIPELINE.md`; evidence/masking contract задаёт `docs/PII_EVIDENCE_DETECTOR_V1.md`; машиночитаемое состояние хранится в `docs/OCR_PROJECT_STATE.json`. Подробная история до PR #184 остаётся в Git history и намеренно не дублируется здесь.

## 0. Изменение PR #184

- Добавлен отдельный bounded production renderer `mobile/src/piiProductionMaskRenderer.ts`.
- `renderTesseractProductionMask` принимает candidate geometry через существующий trusted projection path и локальный packed RGBA buffer.
- Renderer создаёт новый buffer и не мутирует исходный. Каждый пиксель точных per-word rectangles заменяется на фиксированный black RGB `0/0/0` и полностью непрозрачный alpha `255`.
- RTL word boxes остаются отдельными; diagnostic `enclosingBbox` не используется, поэтому промежутки между словами не закрываются общим union rectangle.
- Дробные projected edges округляются наружу через `floor/ceil`, чтобы не оставить неприкрытые крайние пиксели.
- Forged geometry, malformed dimensions, неподдерживаемый pixel buffer, неверная длина RGBA и несовместимое aspect ratio fail closed.
- Output помечен `opaqueReplacement: true` и `irreversibleDerivative: true`, но caller всё ещё обязан уничтожить/не передавать исходный buffer и передавать наружу только производный файл после privacy gate.
- Локально проходят `4/4` focused renderer tests и strict TypeScript check. Полный mobile/Android CI относится к exact final head SHA PR #184.
- PR не добавляет PII discovery, disposition authorization, detector orchestration, UI, image decode/encode, persistence, transport, dependencies, external OCR/LLM, реальные договоры или реальные PII.
- По merge-gated workflow `next_step_id` остаётся `android-tesseract-production-mask-renderer-v1` до merge PR #184 и нового чтения resulting `main`.

## 1. Актуальная privacy/OCR цепочка

| PR | Изменение | Доказано | Не доказано |
|---|---|---|---|
| #179 | Direct-value provenance adapter | Exact class/detector/start/end совпадение с approved finder | Android orchestration и real recall |
| #180 | Android Tesseract word boxes | Bounded text/confidence/in-bounds bbox, bridge validation | Real-contract recall и device smoke |
| #181 | Text span → word boxes | Trusted exact same-line mapping, cross-line fail closed | Approved finder orchestration |
| #182 | Candidate geometry | Immutable separate boxes, line/gap/bounds gates | Candidate correctness на реальных договорах |
| #183 | Development overlay | Contain-fit coordinates, fixed `0.35` opacity, value-free output | UI integration и production safety |
| #184 | Production pixel renderer | New RGBA derivative, exact opaque per-word replacement, source copy preserved | Decode/encode integration, source disposal и end-to-end privacy gate |

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
- page position, page number, alignment и наличие цифр являются только weak context и не дают `auto_mask`;
- monetary amounts, dates, clause numbers и notice periods не считаются PII только из-за цифр;
- fuzzy matching запрещён для PII authorization;
- geometry и renderer сами по себе не авторизуют маску и не доказывают complete PII coverage;
- при неполной evidence, geometry или validation внешний handoff блокируется.

## 3. Реальное состояние компонентов

| Компонент | Состояние | Доказано | Не доказано |
|---|---|---|---|
| Page normalization | Python reference v0 | Bounded grayscale master и synthetic tests | Android production capture quality |
| Candidate/evidence schema | Python reference v1 | Closed classes/dispositions/families и structural gates | Runtime integration |
| Direct PII patterns | Python reference v0 | Email, IL phone, check-digit ID, IL IBAN | Real recall и generalization |
| Marker/value relations | Python reference v0 | Approved same-line bounded relations | Android integration |
| Evidence decision adapters | Python reference v0/v1 | Provenance и deterministic dispositions | Working detector orchestration |
| Android Tesseract words | Runtime slice v1 | Bounded text/confidence/bbox | Real geometry/recall и device smoke |
| Android span mapping | PR #181 | Exact same-line span → trusted boxes | Approved finder orchestration |
| Android candidate geometry | PR #182 | Separate exact boxes и safety gates | Real correctness |
| Android development overlay | PR #183 | Reversible visual verification coordinates | UI integration |
| Android production renderer | PR #184 | Opaque local RGBA replacement in a new buffer | Decode/encode, source disposal и end-to-end handoff safety |
| External OCR handoff | Не подключён | Допустим только после privacy gate | Derivative safety не доказана |

## 4. Активный блокер

Reference evidence chain и Android Tesseract geometry пока не соединены в один runtime detector. PR #184 только необратимо заменяет пиксели уже предоставленной trusted geometry. Он не доказывает, что upstream detector нашёл все PII, не авторизует `auto_mask`, не кодирует итоговый файл и не разрешает внешний handoff.

До production остаются отдельные bounded задачи:

1. связать approved direct-value finder provenance с Android span mapping и disposition authorization;
2. подключить production renderer к локальному decode/encode pipeline с явным уничтожением/изоляцией source buffer;
3. добавить local privacy validation и fail-closed handoff gate;
4. проверить real-contract recall, complete coverage и over-redaction на whole-contract held-out evaluation.

## 5. Единственный следующий шаг

**`android-tesseract-production-mask-renderer-v1`: MERGE-GATED — реализован в PR #184 и остаётся каноническим идентификатором до merge и нового чтения resulting `main`.**

До merge PR #184 запрещено добавлять detector orchestration, UI/runtime decode/encode, external APIs, dependencies или реальные данные. После merge нужно заново прочитать exact resulting `main`, проверить final-head CI и только затем выбрать следующий bounded slice.

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
