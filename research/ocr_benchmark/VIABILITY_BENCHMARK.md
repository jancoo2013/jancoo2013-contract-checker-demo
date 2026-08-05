# Surya serverless GPU OCR viability benchmark v1

This package turns the architecture decision in PR #190 into one reproducible
research benchmark. It does **not** deploy a production worker or claim that
Surya has passed.

## Question

Can Surya OCR 2 process one fixed ten-page Hebrew contract-like packet on one
24 GB-class GPU with:

- materially correct normalized Hebrew text;
- preserved critical clauses, amounts, dates, durations, notice periods and
  negation-bearing language;
- usable block coordinates on every page;
- measured cold first-page time and warm ten-page time;
- measured peak VRAM and positive headroom;
- measured provider worker lifetime, billed seconds and cost?

Latency and cost are reported in v1. They are not blocking gates. Text quality,
critical sentinels, geometry, complete runtime evidence and VRAM headroom are
blocking gates.

## Scope boundary

Allowed:

- the synthetic source packet in `viability_fixture_v1.json`;
- locally rendered pages generated from that source;
- one isolated Surya OCR 2 benchmark environment;
- raw benchmark output under `tests/tmp/`;
- a compact value-bearing report kept local until reviewed and sanitized.

Not included:

- Android upload;
- production encryption or key mediation;
- real user contracts;
- production PII detection or masking;
- Gemini or legal analysis;
- permanent document storage;
- a custom VPS, queue, Redis, RabbitMQ or MinIO;
- a production Runpod handler.

Raw OCR text and page images must not be committed. The expected synthetic
source is safe to commit because it contains no real PII.

## Files

- `viability_fixture_v1.json` — ten source pages, thresholds, five sentinel
  clauses and seven critical values.
- `generate_viability_fixture.py` — deterministic page renderer. It records the
  exact font SHA-256, Pillow version and output image hashes.
- `run_surya_viability.py` — one-process cold/warm runner using the Surya 2
  Python API. It records GPU memory through `nvidia-smi` and writes Surya JSON
  without printing OCR text.
- `viability.py` — evaluator for normalized Hebrew CER, word similarity,
  sentinels, critical values, block geometry, VRAM, timing and cost.
- `tests/test_ocr_viability.py` — stdlib/Pillow tests using fake Surya
  predictions; no GPU or model download is required.

## 1. Render the synthetic packet

Use a Hebrew-capable font that also contains digits and Latin punctuation.
Do not add the font file to the repository.

```bash
python -m research.ocr_benchmark.generate_viability_fixture \
  --manifest research/ocr_benchmark/viability_fixture_v1.json \
  --output-dir tests/tmp/surya_viability/pages \
  --font-path /path/to/hebrew-capable-font.ttf
```

The renderer writes `render_manifest.json`. Record and retain:

- renderer version;
- font filename and SHA-256;
- Pillow version;
- ten page hashes and dimensions.

Open all ten pages and mark the human readability review complete before
spending GPU time. The renderer deliberately refuses text that does not fit on
one page.

## 2. Prepare the isolated Surya 2 environment

Do not add Surya, vLLM or model weights to application dependencies.

```bash
python -m venv .venv-surya-v2
. .venv-surya-v2/bin/activate
python -m pip install --upgrade pip
python -m pip install "surya-ocr==0.20.0"
```

Surya 2 uses a shared inference backend. On a normal NVIDIA host its manager can
spawn vLLM when Docker and the NVIDIA Container Toolkit are available. In a
serverless container without nested Docker, start a compatible vLLM server in
the same worker image and set:

```bash
export SURYA_INFERENCE_BACKEND=vllm
export SURYA_INFERENCE_URL=http://127.0.0.1:8000/v1
```

The exact backend image, model revision and startup command must be recorded in
the provider run notes. Do not treat an unpinned model download as a
reproducible benchmark.

Upstream references:

- Surya repository and v2 usage:
  `https://github.com/datalab-to/surya`
- Surya OCR 2 release:
  `https://github.com/datalab-to/surya/releases/tag/v0.20.0`
- model card:
  `https://huggingface.co/datalab-to/surya-ocr-2`

## 3. Run cold and warm inference

The runner loads ten images, constructs one predictor, processes page 1 once,
then processes all ten pages with the same predictor.

```bash
python -m research.ocr_benchmark.run_surya_viability \
  --input-dir tests/tmp/surya_viability/pages \
  --output-dir tests/tmp/surya_viability/run
```

Produced local artifacts:

```text
tests/tmp/surya_viability/run/
  runtime_manifest.json
  raw/
    cold_first_page/results.json
    warm/results.json
```

`cold_first_page_seconds` includes any lazy inference-server/model startup
triggered by the first prediction. `predictor_initialization_seconds` is kept
separate because construction may not load the model. `warm_document_seconds`
measures the complete ten-page call after warm-up.

The runner samples total GPU memory, not only the Python process, so a child
vLLM process is included. The first sample is the baseline; `peak_vram_mb` is
the highest observed device usage.

The runner does not print image names or OCR text. Provider/runtime logs must
still be inspected separately for leaked request bodies, filenames, model
responses or page content.

## 4. Add provider measurements and evaluate

Provider billing data usually becomes available after the job. Supply the
actual values when evaluating:

```bash
python -m research.ocr_benchmark.viability \
  --input-dir tests/tmp/surya_viability/pages \
  --raw-surya-dir tests/tmp/surya_viability/run/raw/warm \
  --expected-manifest research/ocr_benchmark/viability_fixture_v1.json \
  --runtime-manifest tests/tmp/surya_viability/run/runtime_manifest.json \
  --worker-lifetime-seconds <actual-worker-lifetime> \
  --billed-seconds <actual-billed-seconds> \
  --usd-per-second <actual-provider-price> \
  --output tests/tmp/surya_viability/viability_report.json
```

Do not substitute model throughput for any of these values.

## Blocking gates

`PASS` requires all of the following:

1. exactly the ten expected page names;
2. normalized document CER at most `1.0%` **or** word similarity at least
   `99.0%`;
3. every sentinel clause preserved after normalization;
4. every critical duration, notice period and amount preserved;
5. every page has a valid `image_bbox`;
6. every text-bearing block has a positive bbox contained in that page;
7. at least one usable text block on every page;
8. measured total/peak VRAM, no OOM and positive headroom;
9. complete cold, warm, worker-lifetime and billed-time fields.

The cost target is `$0.02` for this planning run, but v1 reports whether the
target was met without making it a blocking gate. The active architecture
document retains the broader provisional research ceiling of `$0.10` per
ten-page contract.

## What this benchmark cannot prove

A synthetic clean packet is useful for rejecting a broken runtime or obviously
bad OCR configuration. It cannot establish readiness for real photographed
contracts. A later held-out owner-controlled, rights-cleared photo packet must
repeat the same evaluation before production worker, upload, encryption,
sanitization or analyzer integration begins.

Likewise, valid block geometry proves that coordinates are structurally usable.
It does not prove complete PII recall or safe irreversible masking.
