from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from research.handwriting_gate.gate_baseline import (
    build_feature_matrix,
    load_tile_manifest,
    page_metrics,
    score_matrix,
    worst_page_errors,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the handwriting gate at page level.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    parser.add_argument("--split", choices=["train", "val", "test"], default="test")
    args = parser.parse_args()

    with np.load(args.model) as model:
        weights = model["weights"]
        bias = float(model["bias"][0])
        mean = model["mean"]
        std = model["std"]
        image_size = int(model["image_size"][0])
        threshold = float(model["threshold"][0])

    rows = [row for row in load_tile_manifest(args.manifest) if row.split == args.split]
    if not rows:
        raise SystemExit(f"split {args.split!r} is empty")
    features, _ = build_feature_matrix(rows, image_size=image_size)
    scores = score_matrix((features - mean) / std, weights, bias)

    report = {
        "split": args.split,
        "threshold": threshold,
        "page_metrics": page_metrics(rows, scores, threshold),
        "errors": worst_page_errors(rows, scores, threshold),
    }
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
