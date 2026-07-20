# Model-assisted Gold testing v0

Status: approved development workflow. Read together with `docs/CUSTOM_OCR_PIPELINE.md`,
`docs/OCR_PROJECT_STATE.md`, and
`research/hebrew_contract_ocr/DATASET_CONTRACT_V0.md`.

This document fixes the current way in which the first real Hebrew Gold Set and
recognizer feasibility result will be produced. It deliberately keeps the reviewer
application small. Exact APK interaction details may change after a short pilot,
but the data-separation and evaluation rules below must not.

## 1. Goal

A Hebrew-capable reviewer must verify our OCR output, not manually transcribe an
entire contract. If a prediction contains one wrong letter or word, the reviewer
edits only that fragment in a prefilled copy of the prediction. The saved result is
still the exact complete line required for CER calculation.

The workflow must produce:

- a fixed set of high-resolution real line images that was not used for training;
- predictions from one frozen project-owned recognizer;
- exact reviewer-confirmed final text for every accepted line;
- an immutable link between image, prediction, model, and final text;
- a reproducible CER report for that frozen model.

It must not turn plausibility, a teacher prediction, or a Russian comment into
ground truth.

## 2. End-to-end order

1. Prepare the latest full-resolution contract with the existing page normalizer
   and line segmenter.
2. Freeze the candidate IDs and image hashes before viewing predictions from the
   recognizer being tested.
3. Reserve those candidates and matching sources from training.
4. Train one bootstrap project-owned line recognizer on synthetic data and allowed
   non-Gold silver data.
5. Freeze the model configuration and weights checksum.
6. Run that model on the reserved lines on the development computer.
7. Bundle the line images and frozen predictions into an offline review APK.
8. Run a small reviewer-UX pilot first. Continue with the untouched evaluation
   cohort only if the workflow is comfortable and unambiguous.
9. Export exact confirmed lines, materialize Gold Set v0, and calculate CER from
   the already frozen predictions.
10. Compare the same frozen predictions with any baseline on exactly the same
    accepted Gold rows. Consider production Android inference only after this
    result is understood.

Training before completed Gold is allowed only to create the bootstrap predictions
needed for efficient review. It is not evidence that the recognizer is accurate.

## 3. Candidate freeze and leakage boundary

- Gold candidates come only from the latest full-resolution contract. The old
  approximately 1000-pixel photos and their line archive are not Gold candidates.
- Candidate selection uses source provenance, page coverage, geometry, segmentation
  status, and predefined content categories where available. It must not select or
  discard rows because a tested model predicted them well or badly.
- The freeze manifest records stable row ID, source ID, page ID, crop coordinates,
  image hash, and review cohort. Real images and contract text remain local and are
  not committed.
- The pilot cohort and held-out evaluation cohort are assigned before predictions
  are reviewed.
- Candidate source/image matches are excluded from training before bootstrap
  training. Once exact labels exist, the existing text-leakage gate also applies.
- A line is not silently replaced after its prediction is seen. An objectively
  unreadable or invalid crop receives an explicit exclusion reason.

Pilot labels may diagnose the UI or guide later development, but if the model is
changed after pilot results are inspected, those pilot rows are not the untouched
test set for the changed model. The held-out evaluation cohort remains unopened
until the model to be measured is frozen.

## 4. Bootstrap recognizer

The bootstrap recognizer is the first minimal project-owned line model. It may use:

- deterministic synthetic Hebrew contract lines;
- silver rows outside the frozen candidate sources only after the dataset builder
  can prove those exclusions from the candidate manifest;
- the fixed project charset and dataset contract.

It may not use Gold candidates, their corrections, page-derived duplicates, or an
external OCR service at product runtime. Teacher OCR may remain an offline baseline
or source of non-Gold silver labels, never the production recognizer or Gold truth.

The model checksum, charset checksum, training dataset/version, random seed, and
configuration are frozen before candidate predictions are generated.

The current canonical training builder requires a materialized Gold manifest before
it admits silver data. Until a separate small PR adds and tests an equally strict
candidate-manifest exclusion path, the bootstrap model uses synthetic data only.
This workflow does not weaken the existing leakage gate by documentation.

## 5. Minimal reviewer APK v0

The APK is an offline annotation tool, not the product OCR application. OCR runs on
the development computer beforehand; the APK only displays bundled data and saves
review results. It requires no account, server, network connection, or on-device
model.

One screen contains:

1. the original high-resolution image of one text line;
2. our frozen OCR prediction, shown read-only;
3. a text field prefilled with the same prediction, where the reviewer changes only
   the incorrect letter, word, punctuation mark, or space;
4. an optional free-form Russian comment;
5. simple actions: confirm unchanged, save correction, cannot read, and postpone.

After confirm or save, the app advances to the next line and preserves progress.
Zooming the line image and correct RTL editing are required usability basics.

The APK does **not** require word-span selection, structured patch editing, page
reconstruction, automatic language correction, confidence visualization, or OCR
inference. A text diff may be derived later on the development computer; it is not
part of the reviewer's job. More UI is added only if the pilot exposes a concrete
need.

## 6. Review meanings

- `confirmed`: the prediction is the exact visible line; `final_text` equals the
  prediction.
- `corrected`: the reviewer changed the prefilled text and confirms that the whole
  resulting `final_text` now exactly matches the image.
- `unreadable`: the reviewer cannot determine the exact line from the image; no
  Gold text is created and a reason is retained.
- `pending`: no decision yet; the row is not Gold.

The reviewer may describe spacing, crop, or typography problems in Russian. The
comment is diagnostic metadata only. It never substitutes for an exact correction
and never changes CER automatically.

## 7. Minimal local export

Each result must retain at least:

- stable row ID and line-image SHA-256;
- model and prediction-set identifiers;
- original frozen prediction;
- review status;
- exact complete `final_text` for `confirmed` and `corrected` rows;
- optional reviewer comment.

The export format may add app version and timestamps, but v0 must not require a
complex edit-operation schema. The materializer validates hashes, charset, status,
and required text before admitting a row to Gold. Raw images, real Hebrew text,
review exports, and PII are never committed to GitHub.

## 8. Pilot gate

Start with approximately ten lines covering ordinary text, numbers/punctuation,
and at least one difficult or mixed-script case if present. The pilot answers only:

- can the reviewer see the source clearly on the phone;
- can the reviewer change one character or word without retyping the line;
- does RTL editing behave predictably;
- are the four outcomes understandable;
- is export/progress recovery reliable;
- is the correction burden acceptable.

If the UI is confusing, images remain unreadable, or most predictions require
near-total rewriting, stop before assigning the remaining cohort. Fix the concrete
problem and preserve which rows and model results have already been viewed.

## 9. Gold materialization and evaluation

Only exact `confirmed` and `corrected` rows from the designated evaluation cohort
enter Gold Set v0. `unreadable` and `pending` rows do not. Exclusions and their
reasons remain auditable.

CER is calculated against the original frozen prediction, not a prediction rerun
after the reviewer corrections are known. Report overall CER and the slices already
required by the Dataset & Evaluation Contract, including Hebrew, digits,
punctuation, clause numbers, and mixed Hebrew/Latin text where sample counts allow.
Any baseline uses the same accepted images and the same final labels.

Gold Set v0 remains evaluation-only. Neither its images nor its final text may be
added to recognizer training. Results from one contract prove feasibility on that
fixture, not general production accuracy.

## 10. Explicit non-goals

This workflow does not:

- ask the reviewer to type nine pages or recreate already correct text;
- use the old low-resolution contract as Gold;
- claim quality before human confirmation and CER;
- ship the teacher OCR or bootstrap desktop pipeline in the finished product;
- connect raw contract images to an external service;
- implement production Android OCR, page layout, or legal analysis;
- lock the project into an elaborate annotation UI before the ten-line pilot.
