# Surya serverless GPU OCR viability benchmark v1

This PR adds the first bounded slice of the benchmark selected in PR #190:
one fixed ten-page Hebrew contract-like source packet and one deterministic
quality/geometry oracle for Surya OCR output.

It does **not** run Surya, deploy a worker, measure GPU runtime, or claim an
overall viability result.

## Question answered by this slice

Given Surya `results.json` for the fixed packet, does the output preserve:

- materially correct normalized Hebrew text;
- five required legal sentinel clauses;
- seven critical amounts, durations and notice periods;
- one valid image bbox per page;
- positive text-block bboxes contained inside the page;
- at least one usable text block on every page?

Cold start, warm execution, queue delay, VRAM, billed seconds, cost and provider
log/retention behavior remain required parts of the active benchmark, but are
not implemented or inferred here.

## Privacy boundary

The checked-in fixture is synthetic and contains no real PII. Generated page
images, raw OCR text, reports, logs and provider artifacts must remain outside
version control under an ignored local path such as `tests/tmp/`.

Do not use a real user contract for repository automation.

## Files

- `viability_fixture_v1.json` — ten synthetic source pages, thresholds, five
  sentinel clauses and seven critical values.
- `viability.py` — quality/geometry evaluator using the existing Surya output
  loader in `benchmark.py`.
- `tests/test_ocr_viability.py` — focused tests with synthetic `PageResult`
  objects; no model download or GPU is required.

## Prepare input pages

Render or otherwise create exactly these ten filenames from the source strings
in `viability_fixture_v1.json`:

```text
page_01.png
...
page_10.png
```

Before OCR, record the rendering method, font name/hash, dimensions and page
hashes outside the repository, then visually verify all ten pages. The renderer
and serverless runner belong to later bounded PRs inside the same active
`serverless-gpu-ocr-viability-benchmark-v1` step.

## Produce Surya output

The existing research harness can produce the raw Surya directory without
adding Surya to application dependencies:

```bash
python -m research.ocr_benchmark.benchmark \
  --input-dir tests/tmp/surya_viability/pages \
  --output-dir tests/tmp/surya_viability/run \
  --surya-executable /path/to/surya_ocr \
  --chandra-executable /path/to/chandra
```

For a Surya-only run, an isolated invocation may instead write the same
`results.json` shape under a local raw directory. Do not commit that output.

## Evaluate quality and geometry

```bash
python -m research.ocr_benchmark.viability \
  --input-dir tests/tmp/surya_viability/pages \
  --raw-surya-dir tests/tmp/surya_viability/run/raw/surya2 \
  --expected-manifest research/ocr_benchmark/viability_fixture_v1.json \
  --output tests/tmp/surya_viability/quality_geometry_report.json
```

`quality_geometry_verdict=PASS` requires:

1. exactly the ten expected page names;
2. normalized document CER at most `1.0%` **or** word similarity at least
   `99.0%`;
3. every sentinel clause preserved after normalization;
4. every critical value preserved after normalization;
5. every page has a valid `image_bbox`;
6. every text-bearing block has a positive bbox inside that page;
7. at least one usable text block on every page.

## Interpretation boundary

A quality/geometry `PASS` is only one sub-gate. It is not an overall Surya
viability decision and does not authorize production upload, encryption,
server-side PII sanitization, Gemini handoff or use of real contracts.

The active benchmark remains incomplete until later bounded work measures cold
and warm execution, queue delay, total-device VRAM, OOM behavior, worker
lifetime, billed seconds, cost, logs and cleanup on an approved scale-to-zero
GPU worker.
