# Surya 2 vs Chandra OCR 2 research benchmark

This directory contains a research-only harness for one narrow question:

> Which self-hosted OCR candidate produces the more useful Hebrew contract text for a later Israel-hosted Privacy Gateway?

The benchmark compares:

- Surya 2 through the official `surya_ocr` CLI;
- Chandra OCR 2 through the official `chandra` CLI.

This PR does **not** implement PII detection, redaction, Gemini calls, production backend integration, Android work, or legal analysis.

## Privacy boundary

The benchmark input consists of raw contract page images and may contain PII.

Rules:

1. keep all page images under the ignored local `dataset/` directory;
2. keep all raw OCR and normalized outputs under the ignored local `artifacts/` directory;
3. do not commit images, OCR text, reports, screenshots, or logs containing contract content;
4. run OCR only on a local machine or an Israel-controlled compute environment approved for this research;
5. do not point Chandra vLLM or Surya inference URLs at an external endpoint for PII-bearing benchmark data.

Model-weight downloads are separate from document inference. Verify deployment networking before using real contracts.

## Why the harness uses CLIs

The repository does not add Surya or Chandra to application dependencies. Both OCR stacks are large and may have conflicting ML dependencies.

The harness invokes their official command-line interfaces and then normalizes outputs with Python stdlib code in this repository.

Using two separate virtual environments is recommended:

```text
.venv-surya/   -> surya_ocr
.venv-chandra/ -> chandra
```

On Windows, pass the full executable paths, for example:

```text
.venv-surya\Scripts\surya_ocr.exe
.venv-chandra\Scripts\chandra.exe
```

## Dataset layout

Use one photographed page per image file. File stems must be unique.

```text
research/ocr_benchmark/
  dataset/
    page_01.jpg
    page_02.jpg
    page_03.jpg
  artifacts/
```

Supported image suffixes:

```text
.bmp .jpeg .jpg .png .tif .tiff .webp
```

The first experiment should use the same original images for both models.

## Install model environments

Follow the upstream projects for GPU/backend prerequisites. Minimal package installation is:

```bash
# Surya environment
pip install surya-ocr

# Chandra environment, HuggingFace local backend
pip install 'chandra-ocr[hf]'
```

The harness defaults Chandra to `--method hf`. A locally controlled vLLM deployment can be selected with `--chandra-method vllm`.

## Run benchmark

From repository root:

```bash
python -m research.ocr_benchmark.benchmark \
  --input-dir research/ocr_benchmark/dataset \
  --output-dir research/ocr_benchmark/artifacts \
  --surya-executable /path/to/surya_ocr \
  --chandra-executable /path/to/chandra \
  --chandra-method hf
```

Extra model CLI arguments can be repeated:

```bash
python -m research.ocr_benchmark.benchmark \
  --input-dir research/ocr_benchmark/dataset \
  --output-dir research/ocr_benchmark/artifacts \
  --surya-extra-arg=--keep_server \
  --chandra-extra-arg=--batch-size \
  --chandra-extra-arg=1
```

Use `--normalize-only` to rebuild normalized files and the summary from already existing raw outputs without invoking either OCR model again.

## Output

```text
artifacts/
  raw/
    surya2/
      ... upstream Surya output ...
    chandra2/
      ... upstream Chandra output ...
  normalized/
    surya2/
      page_01.txt
      page_01.json
    chandra2/
      page_01.txt
      page_01.json
  benchmark_report.json
```

The normalized JSON schema is:

```json
{
  "model": "surya2",
  "document_id": "page_01",
  "source_name": "page_01.jpg",
  "page_number": 1,
  "text": "...",
  "blocks": [],
  "metadata": {}
}
```

Surya block text, bbox, polygon, label, confidence, and error flags are retained when present. The Chandra CLI path currently normalizes Markdown text and page metadata; it does not expose comparable block bounding boxes through this harness.

## Reported metrics

The automatic report contains only metrics that can be measured without a gold transcription:

- pages processed;
- non-empty pages;
- output character count;
- Surya block count;
- wall-clock runtime;
- seconds per page.

These are operational diagnostics, **not OCR accuracy metrics**.

Do not claim that one model is more accurate from character count or runtime alone.

## Human comparison rubric for the first dataset

For each page, inspect the normalized outputs side by side and record at least:

1. missing legal clauses or lines;
2. corrupted Hebrew words that change meaning;
3. dropped or reordered sections;
4. names, addresses, phone numbers, ID-like sequences, email addresses, and bank/account-like fields that OCR failed to reproduce accurately enough for later PII detection;
5. table/form structure loss;
6. hallucinated text not present in the image.

The privacy architecture has asymmetric risk. An OCR system can be good for reading contracts and still be unsafe as the only input to a PII scrubber if it systematically corrupts the identifiers that the scrubber must detect.

## Decision rule

This benchmark does not select a production OCR model by itself.

The intended sequence is:

```text
Surya 2 vs Chandra OCR 2
        ↓
choose OCR candidate(s) worth continuing
        ↓
Israel-specific deterministic PII rules
        +
PII model benchmark
        ↓
independent leak verification
        ↓
PASS / BLOCK research decision
```

A model should advance only if it preserves enough legal text **and** provides sufficiently reliable PII-bearing text for the next leak-focused experiment.

## Tests

The harness normalization and command construction use only stdlib code and can be tested without installing either OCR model:

```bash
python -m unittest tests.test_ocr_benchmark
```

No private images are required for the tests.
