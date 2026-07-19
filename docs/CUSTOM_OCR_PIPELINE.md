# Project-owned Hebrew contract OCR pipeline

Status: active development contract. Read together with `docs/ARCHITECTURE.md`.

This file records the OCR direction chosen for the product so that later work does not silently return to temporary OCR engines or confuse label creation with production inference.

## Non-negotiable decisions

1. The finished product uses a compact project-owned OCR model with project-owned weights.
2. OCR inference runs on the Android device. Contract images are not sent to an external OCR provider.
3. Surya, Chandra, Tesseract, and multimodal LLMs are not production OCR dependencies.
4. A temporary OCR engine may be used offline only as a teacher for candidate labels or as a research baseline. Its output is never automatically gold.
5. The privacy layer, handwriting gate, OCR recognizer, layout parser, and legal analyzer are separate components. A result from one component does not prove another component works.
6. OCR quality claims require exact comparison against a fixed human-verified gold set. Character count, visual plausibility, model confidence, and teacher agreement are not accuracy metrics.
7. Dataset manifests, charset IDs, split rules, leakage checks, and CER follow `research/hebrew_contract_ocr/DATASET_CONTRACT_V0.md`.
8. Page previews, rectified masters, resolution gates, and recognizer line height follow `research/hebrew_contract_ocr/IMAGE_RESOLUTION_CONTRACT_V0.md`.
9. Automatic corner proposals, fail-closed rejection, `frame_clipped` handling, and outside-page deletion follow `research/hebrew_contract_ocr/PAGE_BOUNDARY_DETECTOR_V0.md`.

Changing any of these decisions requires an explicit user decision and an update to this file in the same PR.

## Product runtime pipeline

```text
raw phone photo
→ on-device geometric and image preprocessing
→ on-device privacy handling according to the approved privacy design
→ project-owned compact OCR recognizer
→ RTL line and page reconstruction with coordinates
→ contract structure and clause parser
→ evidence blocks
→ legal-risk analysis
→ Russian report
```

Only our exported model weights and our preprocessing/postprocessing code ship in the Android application. Research teachers do not.

Geometric preprocessing is bounded by the Image Resolution Contract v0. Native camera resolution does not flow directly into OCR: a sampled preview drives page-boundary detection, and the source is rectified directly into a bounded grayscale page master without materializing a full high-megapixel RGBA bitmap.

The accepted page quadrilateral is destructive by design for derived OCR input: pixels outside it are discarded. Raw source photos remain unchanged. A frame-clipped page is recorded explicitly and may require recapture; the pipeline must not move an internal edge inward merely to force an A4-looking crop.

Production integration with raw user photos remains blocked until the privacy design is approved. That block does not prevent offline OCR research on synthetic data, redacted crops, or locally controlled datasets.

## Training pipeline

```text
synthetic Hebrew contract templates ─┐
                                    ├→ line-image dataset → compact recognizer training
verified real line crops ────────────┘                         ↓
                                               fixed real gold evaluation
                                                            ↓
                                                 export our own weights
```

Data tiers:

- `synthetic`: text is generated from reviewed templates and rendered with known exact ground truth;
- `silver`: a teacher prediction was checked using agreement, page context, or automated review, but remains fallible;
- `gold`: a qualified Hebrew reader verified the exact characters against the best available source;
- `excluded`: cropped, merged, illegible, handwritten, redacted-over-text, or otherwise unsuitable for recognizer training.

Silver data may be useful for training and bootstrapping. It must not be used as the only evaluation truth.

## Current milestone: recognizer feasibility v0

Work in this order:

1. Generate deterministic synthetic Hebrew contract lines.
2. Keep the existing 170 locally verified crops as silver data; do not claim they are gold.
3. Create a small fixed real gold test set with help from a Hebrew-capable verifier.
4. Train one simple compact line recognizer architecture; do not invent a new neural architecture.
5. Measure exact character error rate (CER), separately for Hebrew letters, digits, punctuation, and mixed `AS-IS` lines.
6. Compare with the fixed baseline on the same gold set.
7. Consider Android export only after a measurable feasibility result.

Current state:

- step 1 is implemented by the deterministic synthetic-line generator;
- step 2 exists locally as the 170-row silver archive and remains explicitly silver;
- step 3 is the active work item: build a stratified review pack and obtain exact human verification from a Hebrew-capable reviewer.

While human verification is pending, the framework-independent Dataset & Evaluation Contract v0 may be implemented and smoke-tested on synthetic/silver data. This preparation must not be presented as a real quality result.

The review-pack collector does not turn teacher labels into gold. A row becomes gold only after the reviewer marks its exact transcription as approved or corrected. This work does not train a model and does not change application runtime behavior.

## Evaluation gates

Every experiment records:

- immutable dataset/version identifiers;
- random seed and generator arguments;
- training configuration and model checksum;
- exact gold-set CER;
- CER slices for clause numbers, currency, punctuation, Hebrew-only text, and Hebrew/Latin text;
- examples of deletions, insertions, substitutions, and reading-order failures;
- inference latency and model size only after accuracy is known.

No Android work is justified by a teacher model looking good on its own labels. No model is declared better from a handful of visually inspected rows.

## Detours to avoid

- Do not keep tuning Surya, Chandra, or Tesseract as if it were the product recognizer.
- Do not add a production dependency on a teacher OCR engine.
- Do not treat contextual language-model correction as proof that line recognition is accurate.
- Do not train on the fixed gold test set.
- Do not commit raw contracts, source photos, real line crops, real OCR text, generated manifests containing real contract text, or PII.
- Do not merge privacy, handwriting, layout, OCR, and legal-analysis experiments into one unmeasurable result.
- Do not start Android integration before the recognizer passes the agreed gold-set gate.

## Repository workflow

Use one small branch and one draft PR per measurable step. Each OCR PR states:

- which numbered milestone step it implements;
- which data tier it reads or writes;
- which metric changed;
- which external engines, APIs, or dependencies were used;
- whether any runtime application behavior changed.

When the next action is ambiguous, return to this file and choose the first incomplete milestone step instead of opening a new OCR direction.
