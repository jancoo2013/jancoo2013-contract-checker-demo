# Visual PII Localization v1

Status: approved architecture reset for the active local privacy track.

## 1. Product objective

The on-device component must locate and irreversibly redact likely PII regions before any image leaves the device.

It is not required to produce a complete Hebrew transcript of the contract.

The active problem is therefore:

```text
page image
→ visual PII-region candidates
→ deterministic evidence and geometry checks
→ fail-closed disposition
→ irreversible local masks
```

The rejected dependency is:

```text
full-page Hebrew OCR
→ text regexes
→ reverse mapping into image coordinates
```

Tesseract remains retained only as historical diagnostic code. It is not an active masking dependency and must not be used as a fallback that can authorize masks.

## 2. First model boundary

The first learned component is a compact visual region detector/classifier. It receives an image crop or page tile and returns only class, score and geometry.

Initial classes:

- `printed_pii_field_or_value`;
- `handwritten_entry`;
- `signature_or_initials`;
- `stamp_or_seal`;
- `non_pii_text`;
- `ambiguous_sensitive_region`.

The first model does not need to read names, addresses or Hebrew sentences. It must learn visual and layout evidence sufficient to propose regions for later deterministic disposition.

## 3. Evidence boundary

A model score alone does not authorize `auto_mask`.

Model output becomes one evidence item inside the existing decision chain. Production disposition remains one of:

- `auto_mask` only when approved evidence and geometry rules are satisfied;
- `local_review` for plausible but incomplete evidence;
- `keep` only when the region is safely classified as non-PII.

Page position, alignment, handwriting appearance or digit density cannot independently authorize a mask.

## 4. Data strategy

Training and evaluation data may contain only:

- synthetic pages and crops;
- generated fictitious PII;
- locally controlled real crops that never enter GitHub or external services;
- value-free annotations containing class and geometry only.

Real contracts are split by whole contract. Pages or crops from one contract must not cross train, validation and held-out evaluation boundaries.

GitHub must never contain raw contract images, readable PII, signatures, account details or reversible masked derivatives.

## 5. First experiment

The first implementation step is `visual-pii-synthetic-baseline-v1`.

It must build an offline, repository-owned baseline without Android integration:

1. generate synthetic page tiles with printed text-like regions, fictitious form fields, handwriting-like strokes and signatures;
2. emit value-free bounding-box annotations;
3. train or fit one compact baseline detector/classifier;
4. evaluate region recall and false-positive behavior on held-out synthetic templates;
5. export one mobile-compatible model artifact only if the baseline meets the provisional gate;
6. do not add the model to the Android runtime in the same PR.

## 6. Provisional go/no-go gate

The baseline may proceed to a real-crop evaluation only when all conditions hold:

- sensitive-region recall at least `0.98` on held-out synthetic contracts;
- complete-box coverage at least `0.97`;
- no contract-specific coordinates or template IDs used as features;
- false positives are reported separately for legally relevant printed text;
- model artifact and inference runtime fit the later Samsung A55 budget;
- evaluation is reproducible from repository-owned synthetic generation rules.

These thresholds are research gates, not production safety claims.

## 7. Out of scope for the baseline

The first baseline must not:

- read full Hebrew text;
- recognize names or addresses character by character;
- connect Gemini, Google Vision or any external OCR;
- add production masks;
- change the Android application;
- use real contract images in CI;
- claim complete PII coverage;
- reactivate CRNN full-line OCR research.

## 8. Expected continuation

If the synthetic baseline fails, the architecture returns to review before any Android work.

If it passes, the next separate steps are:

```text
local real-crop evaluation
→ mobile export/inference benchmark
→ evidence adapter
→ development overlay
→ irreversible mask renderer
→ local privacy validator
```

Each step requires its own bounded PR and evidence gate.
