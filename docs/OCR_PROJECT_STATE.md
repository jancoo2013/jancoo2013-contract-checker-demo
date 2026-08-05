# OCR Project State & Continuity v0

Последнее обновление: 2026-08-05, PR #189, `visual-pii-localization-architecture-reset-v1`.

Активный трек: `local-pii-redaction`.

Единственный следующий шаг: `visual-pii-synthetic-baseline-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Архитектуру задают `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md` и `docs/VISUAL_PII_LOCALIZATION_V1.md`; evidence/masking contract задаёт `docs/PII_EVIDENCE_DETECTOR_V1.md`; машиночитаемое состояние хранится в `docs/OCR_PROJECT_STATE.json`.

## 0. Изменение PR #189

- PR #188 закрыт без merge: ML Kit Latin и поиск готового полного Hebrew OCR не являются активным направлением.
- Реальный device review подтвердил, что полноформатный Tesseract pass по фотографии страницы непригоден как основа PII-маскировщика.
- Ошибочная зависимость `full-page OCR → regex → reverse mapping` исключена из активного пути.
- Новый активный путь — визуальная локализация PII-регионов без обязательного прочтения всего договора.
- Первый learned component возвращает только класс, score и geometry; он не должен транскрибировать имена, адреса или юридический текст.
- Learned output остаётся evidence, а не самостоятельной авторизацией `auto_mask`.
- Raw images, readable PII и real crops не попадают в GitHub, CI или внешние сервисы.

## 1. Активная целевая цепочка

```text
raw phone photo
→ on-device geometric/image preprocessing
→ visual PII-region proposals
→ deterministic evidence and geometry checks
→ auto_mask / local_review / keep
→ irreversible local pixel replacement
→ local fail-closed privacy validation
→ anonymized derivative
→ approved external OCR
→ secondary text redaction
→ legal-risk analysis
→ Russian report
```

Запрещённая активная зависимость:

```text
full-page local Hebrew OCR
→ complete transcript
→ regex search
→ reverse text-to-box mapping
```

Tesseract-код остаётся исторической диагностикой и не может авторизовать production mask или использоваться как fallback active path.

## 2. Сохранённые компоненты

| Компонент | Статус |
|---|---|
| PII classes and evidence contract | Сохраняется |
| Direct-value validators/checksums | Сохраняются как дополнительная evidence, когда значение доступно |
| `auto_mask / local_review / keep` | Сохраняется |
| Provenance and fail-closed decisions | Сохраняются |
| Geometry gates and development overlay | Сохраняются и будут переиспользованы после появления visual proposals |
| Tesseract full-page recognition | NO-GO для активного MVP masking path |
| Production irreversible mask renderer | Не реализован |
| Local privacy validator | Не реализован |
| External OCR handoff | Не подключён; разрешён только после privacy gate |

## 3. Новый модельный контракт

Первый визуальный baseline работает offline и возвращает bounding boxes для классов:

- `printed_pii_field_or_value`;
- `handwritten_entry`;
- `signature_or_initials`;
- `stamp_or_seal`;
- `non_pii_text`;
- `ambiguous_sensitive_region`.

Model score не является достаточным основанием для `auto_mask`. Page position, alignment, handwriting appearance и digit density также не авторизуют маску по отдельности.

## 4. Данные и оценка

Разрешены:

- synthetic pages/crops с фиктивными данными;
- value-free annotations: class + geometry;
- локально контролируемые real crops, которые не покидают машину владельца и не коммитятся.

Primary research metrics:

- sensitive-region recall;
- complete-box coverage;
- missed-sensitive-area rate;
- over-redaction of legally relevant text;
- page/contract-level privacy pass rate.

Split выполняется по целым договорам и template families, а не по отдельным страницам или кропам.

## 5. Единственный следующий шаг

**`visual-pii-synthetic-baseline-v1`**.

Bounded scope:

1. repository-owned synthetic page-tile generator;
2. value-free bounding-box annotations;
3. один компактный offline detector/classifier baseline;
4. held-out synthetic evaluation;
5. mobile-compatible export только при прохождении provisional gate;
6. без Android-интеграции, production masks, внешних API и real images в CI.

Provisional gate:

- sensitive-region recall ≥ `0.98`;
- complete-box coverage ≥ `0.97`;
- отсутствие template IDs и contract-specific coordinates как features;
- отдельный отчёт false positives по legally relevant printed text;
- воспроизводимость synthetic generation и evaluation.

Эти thresholds являются research gate, а не заявлением о production safety.

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

Последний полный cold-start audit: PR #177 после merge PR #176.
