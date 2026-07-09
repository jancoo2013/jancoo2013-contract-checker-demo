# Region MIL leave-one-page-out experiment

This experiment is the next step after `prepare_paired_bags.py`.

It uses the same aligned local pairs:

```text
dataset/
  original/
    1.jpg
    ...
  redacted/
    1.jpg
    ...
```

The redacted images are used only to derive weak labels. All model input tiles are cropped from `original/`.

## 1. Build region-level bags

```bash
python -m research.handwriting_gate.prepare_region_bags \
  --original-dir research/handwriting_gate/dataset/original \
  --redacted-dir research/handwriting_gate/dataset/redacted \
  --output-dir research/handwriting_gate/prepared_regions
```

The preparation step:

1. computes an original/redacted difference mask;
2. finds 8-connected changed regions;
3. filters tiny components;
4. creates one positive MIL bag per surviving changed region;
5. puts overlapping original-image tiles into that region bag;
6. creates singleton negative bags from tiles outside a dilated exclusion zone around every changed pixel.

Defaults:

- tile size: 256 px;
- stride: 128 px;
- difference threshold: 30;
- minimum connected-component area: 200 px;
- minimum component fraction per candidate tile: 0.001;
- negative exclusion dilation radius: 8 px.

Output:

```text
prepared_regions/
  region_tiles/
  region_bags_manifest.csv
  region_dataset_report.json
```

## 2. Run the linear MIL LOPO experiment

```bash
python -m research.handwriting_gate.train_region_mil_lopo \
  --manifest research/handwriting_gate/prepared_regions/region_bags_manifest.csv \
  --report-out research/handwriting_gate/artifacts/region_mil_lopo_report.json
```

The trainer uses the existing Pillow/NumPy feature baseline and a smooth-max MIL pooling objective. No new ML framework is added.

Evaluation is leave-one-page-out:

```text
fold 1: train pages 2..9 -> test page 1
fold 2: train pages 1,3..9 -> test page 2
...
fold 9: train pages 1..8 -> test page 9
```

For each fold, the report includes:

- positive-region bag recall;
- false-negative region bags;
- false-positive rate on clean negative tiles;
- false-positive negative tiles;
- page score and page detection result;
- threshold chosen from the training fold under a recall constraint.

Aggregate output includes:

- region recall;
- region false-negative rate;
- negative-tile false-positive rate;
- positive-page recall across the nine held-out folds.

## Interpretation limits

This dataset contains only filled positive pages. Therefore:

- positive-page recall can be estimated;
- region-level weak-label recall can be estimated;
- false-positive rate can be estimated on clean negative tiles;
- **page-level false-positive rate cannot be estimated yet**.

Region labels are weak labels derived from broad redaction differences. They can contain label noise. Results from this experiment are evidence about whether the research direction has signal, not a production acceptance test.

Do not integrate this model into the mobile application based on this experiment alone. A later test needs independent clean pages and independent handwritten pages from unseen documents.
