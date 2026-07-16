# Synthetic Hebrew contract lines

This research tool renders deterministic, single-line Hebrew rental-contract samples for training the project-owned OCR recognizer.

It does not call Surya, Chandra, Tesseract, Gemini, a cloud OCR service, or any network API. It uses the existing Pillow and NumPy dependencies. Fonts remain local and are not copied into the generated dataset.

The generator scans the supplied font directory and automatically rejects font files that do not contain the complete Hebrew alphabet. This prevents missing Hebrew glyphs from silently becoming square placeholder characters in training images.

## Generate a template-only dataset

Pillow must be built with `libraqm`; otherwise mixed Hebrew, numbers, punctuation, and `AS-IS` cannot be rendered with reliable bidirectional ordering.

Linux example:

```bash
python -m research.hebrew_contract_ocr.generate_synthetic_lines \
  --output-dir research/hebrew_contract_ocr/generated/template_v0 \
  --font-dir /usr/share/fonts/truetype \
  --count 10000 \
  --seed 20260716
```

Windows example:

```powershell
python -m research.hebrew_contract_ocr.generate_synthetic_lines `
  --output-dir research/hebrew_contract_ocr/generated/template_v0 `
  --font-dir C:\Windows\Fonts `
  --count 10000 `
  --seed 20260716
```

The output directory must be empty. The generator never deletes or overwrites an existing dataset.

## Mix in the local verified-line corpus

The current verified archive can contribute exact line text while the pixels, font, noise, blur, scale, and compression remain synthetic:

```bash
python -m research.hebrew_contract_ocr.generate_synthetic_lines \
  --output-dir research/hebrew_contract_ocr/generated/mixed_v0 \
  --font-dir /usr/share/fonts/truetype \
  --corpus-jsonl /local/path/silver_verified_v1.jsonl \
  --corpus-ratio 0.35 \
  --count 10000 \
  --seed 20260716
```

`--corpus-jsonl` is read locally. Never commit that file, its source crops, or a generated manifest containing real contract text. The repository ignores everything under `research/hebrew_contract_ocr/generated/`.

## Output contract

```text
generated/mixed_v0/
  images/
    line_000000.png
    ...
  manifest.jsonl
  summary.json
```

Each manifest row contains the exact logical Unicode target text, the train/validation split, the template or local-corpus source, the font path, a per-sample seed, and all degradation parameters. The same seed, fonts, arguments, and dependency versions produce the same files.

This generator creates training data; it does not measure OCR quality. Quality is measured separately as exact CER on a fixed real gold test set that is never used for training.
