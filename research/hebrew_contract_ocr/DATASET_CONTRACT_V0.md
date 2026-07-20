# OCR Dataset & Evaluation Contract v0

This document is binding for the project-owned Hebrew contract OCR research pipeline. It defines data representation and accuracy measurement independently of any training framework or model architecture.

## 1. Text representation

Ground truth and predictions use logical Unicode order. They are never stored in manually reversed visual order.

Canonical normalization is:

1. remove a Unicode BOM;
2. normalize to Unicode NFC;
3. collapse all whitespace runs to one ASCII space;
4. strip leading and trailing whitespace;
5. preserve case and punctuation;
6. reject Unicode bidi-control characters instead of silently applying them.

The renderer, UI, or terminal is responsible for visual RTL display. Dataset code must not reverse Hebrew strings.

## 2. Charset and CTC IDs

`charset_v0.json` is the versioned character contract. It contains:

- all unpointed Hebrew letters, including final forms;
- ASCII digits;
- uppercase and lowercase Latin letters;
- contract punctuation, Hebrew quote marks, currency, percent, field-line, and dash characters;
- ASCII space as character ID 1.

CTC blank is ID 0 and is not a text character. Every other ID is the one-based array position in `characters`. Unknown characters block dataset materialization and prediction evaluation.

Changing character order, normalization, or blank ID creates a new charset version. It must not silently modify v0.

## 3. Data tiers and permitted splits

| Tier | Meaning | Permitted splits |
|---|---|---|
| `synthetic` | Exact generated text and generated pixels | `train`, `validation` |
| `silver` | Real crop with teacher/consensus label that may still be wrong | `train` only after Gold exclusions |
| `gold` | Real crop checked character-by-character by a Hebrew-capable reviewer | `test` only |

Silver metrics are pipeline diagnostics, not real OCR accuracy. Only a clean test-only gold evaluation may be reported as real CER.

## 4. Canonical manifest schema

Each JSONL row contains:

| Field | Contract |
|---|---|
| `schema_version` | Integer `1` |
| `dataset_id` | Immutable dataset/version identifier |
| `sample_id` | Stable tier-prefixed identifier |
| `image` | Safe POSIX-style path relative to the dataset root |
| `text` | Canonically normalized logical-order ground truth |
| `data_tier` | `synthetic`, `silver`, or `gold` |
| `split` | `train`, `validation`, or `test` according to tier |
| `label_status` | Provenance status; gold requires `human_approved` or `human_corrected` |
| `source_dataset` | Immutable source dataset/pack identifier |
| `source_id` | Stable source row or crop identifier |
| `image_sha256` | SHA-256 of exact image bytes |
| `text_sha256` | SHA-256 of normalized UTF-8 text |
| `width`, `height` | Verified image dimensions |

Optional provenance such as `pack_id`, `selection_category`, `page`, `line`, and synthetic `template_id` may be retained.

Canonical datasets copy exact source images into their own ignored output directory. Builders refuse to overwrite a non-empty output directory.

## 5. Split and leakage rules

- Silver rows not reserved for Gold join `train`.
- Synthetic rows may join `train` or `validation`.
- All rows with identical normalized text are forced into one training split.
- Duplicate image bytes are rejected.
- Gold rows never join the training dataset.
- Training materialization requires a non-empty canonical Gold manifest and excludes matching
  source crops, exact image bytes, and normalized text before copying any training image.
- Evaluation is blocked if gold and training contain an identical image hash or identical normalized text hash.

Exact text overlap is intentionally strict for v0. It prevents a narrow legal-language recognizer from receiving the exact evaluation sequence during training.

Gold from one contract is a fixed recognizer-feasibility fixture, not evidence of generalization. A general quality claim additionally requires held-out contracts separated at source-document level.

## 6. Build and validate training data

```bash
python -m research.hebrew_contract_ocr.dataset_contract build-training \
  --synthetic-manifest /local/synthetic/manifest.jsonl \
  --synthetic-root /local/synthetic \
  --synthetic-dataset-id synthetic_contract_lines_v0 \
  --silver-manifest /local/hebrew_contract_lines_v0/silver_verified_v1.jsonl \
  --silver-root /local/hebrew_contract_lines_v0 \
  --silver-dataset-id different_lease_01_silver_v1 \
  --gold-manifest research/hebrew_contract_ocr/generated/gold_v0/manifest.jsonl \
  --gold-root research/hebrew_contract_ocr/generated/gold_v0 \
  --output-dir research/hebrew_contract_ocr/generated/training_v0
```

Gold must be materialized first using the next section. The builder writes
`gold_exclusions.jsonl` with source IDs and hashes, but no contract text, then reruns the exact
Gold/training leakage gate before accepting the training output.

Validate any canonical dataset:

```bash
python -m research.hebrew_contract_ocr.dataset_contract validate \
  --manifest research/hebrew_contract_ocr/generated/training_v0/manifest.jsonl \
  --dataset-root research/hebrew_contract_ocr/generated/training_v0
```

## 7. Materialize future Gold Set v0

After human review:

```bash
python -m research.hebrew_contract_ocr.dataset_contract materialize-gold \
  --review-manifest /local/gold_review_v0/gold_accepted_v0.jsonl \
  --review-root /local/gold_review_v0 \
  --output-dir research/hebrew_contract_ocr/generated/gold_v0
```

Only review rows with status `approved` or `corrected` are materialized. Pending and excluded rows are ignored.

Before evaluation:

```bash
python -m research.hebrew_contract_ocr.dataset_contract check-leakage \
  --training-manifest research/hebrew_contract_ocr/generated/training_v0/manifest.jsonl \
  --training-root research/hebrew_contract_ocr/generated/training_v0 \
  --gold-manifest research/hebrew_contract_ocr/generated/gold_v0/manifest.jsonl \
  --gold-root research/hebrew_contract_ocr/generated/gold_v0
```

## 8. Prediction and CER contract

Prediction JSONL contains one logical-order row per predicted sample:

```json
{"sample_id": "gld_...", "prediction": "..."}
```

Character error rate is exact Levenshtein CER:

```text
CER = (substitutions + deletions + insertions) / reference characters
```

The report includes:

- overall CER and edit counts;
- Hebrew-letter slice;
- digit slice;
- punctuation/symbol slice;
- Latin slice;
- space slice;
- Gold Set selection-category slices;
- missing predictions, counted as full deletions;
- worst sample IDs without embedding contract text in the report.

Substitutions and deletions belong to the reference character class. Insertions belong to the inserted prediction character class.

```bash
python -m research.hebrew_contract_ocr.evaluate_ocr \
  --ground-truth-manifest research/hebrew_contract_ocr/generated/gold_v0/manifest.jsonl \
  --ground-truth-root research/hebrew_contract_ocr/generated/gold_v0 \
  --training-manifest research/hebrew_contract_ocr/generated/training_v0/manifest.jsonl \
  --training-root research/hebrew_contract_ocr/generated/training_v0 \
  --predictions /local/predictions.jsonl \
  --output /local/cer_report_v0.json
```

The evaluator rejects extra sample IDs, unknown characters, invalid ground truth, and training/gold leakage. Non-gold evaluation is blocked unless an explicit smoke-test flag is supplied, and such output must not be presented as OCR quality.

## 9. Scope boundary

This contract does not select a recognizer architecture, train a model, export Android weights, reconstruct pages, or perform legal analysis. Those stages consume this contract; they do not redefine it.
