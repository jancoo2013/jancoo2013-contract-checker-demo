from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image, ImageOps

PRINTED_ONLY = "printed_only"
HAND_MARK_PRESENT = "hand_mark_present"
VALID_LABELS = {PRINTED_ONLY, HAND_MARK_PRESENT}


@dataclass(frozen=True)
class TileRow:
    path: Path
    label: str
    group_id: str
    page_id: str
    split: str

    @property
    def target(self) -> int:
        return 1 if self.label == HAND_MARK_PRESENT else 0


def stable_split(group_id: str, train_pct: int = 70, val_pct: int = 15) -> str:
    if not group_id.strip():
        raise ValueError("group_id must not be empty")
    if train_pct <= 0 or val_pct < 0 or train_pct + val_pct >= 100:
        raise ValueError("split percentages must leave a non-empty test split")
    bucket = int(hashlib.sha256(group_id.encode("utf-8")).hexdigest()[:8], 16) % 100
    if bucket < train_pct:
        return "train"
    if bucket < train_pct + val_pct:
        return "val"
    return "test"


def load_tile_manifest(path: Path) -> list[TileRow]:
    base = path.parent
    rows: list[TileRow] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"path", "label", "group_id", "page_id", "split"}
        if not required.issubset(reader.fieldnames or []):
            missing = sorted(required - set(reader.fieldnames or []))
            raise ValueError(f"manifest is missing columns: {', '.join(missing)}")
        for index, raw in enumerate(reader, start=2):
            label = (raw["label"] or "").strip()
            if label not in VALID_LABELS:
                raise ValueError(f"line {index}: unsupported label {label!r}")
            split = (raw["split"] or "").strip()
            if split not in {"train", "val", "test"}:
                raise ValueError(f"line {index}: unsupported split {split!r}")
            rel = Path((raw["path"] or "").strip())
            rows.append(
                TileRow(
                    path=(base / rel).resolve(),
                    label=label,
                    group_id=(raw["group_id"] or "").strip(),
                    page_id=(raw["page_id"] or "").strip(),
                    split=split,
                )
            )
    if not rows:
        raise ValueError("manifest contains no rows")
    return rows


def _edge_magnitude(gray: np.ndarray) -> np.ndarray:
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[:, 1:-1] = gray[:, 2:] - gray[:, :-2]
    gy[1:-1, :] = gray[2:, :] - gray[:-2, :]
    return np.sqrt(gx * gx + gy * gy)


def extract_features(image_path: Path, image_size: int = 32) -> np.ndarray:
    if image_size < 8:
        raise ValueError("image_size must be at least 8")
    with Image.open(image_path) as image:
        gray = ImageOps.grayscale(image)
        gray = ImageOps.autocontrast(gray)
        gray = gray.resize((image_size, image_size), Image.Resampling.BILINEAR)
        pixels = np.asarray(gray, dtype=np.float32) / 255.0
    ink = 1.0 - pixels
    edges = _edge_magnitude(pixels)
    return np.concatenate([ink.reshape(-1), edges.reshape(-1)]).astype(np.float32)


def build_feature_matrix(rows: Sequence[TileRow], image_size: int = 32) -> tuple[np.ndarray, np.ndarray]:
    if not rows:
        raise ValueError("no rows supplied")
    features = [extract_features(row.path, image_size=image_size) for row in rows]
    targets = np.asarray([row.target for row in rows], dtype=np.float32)
    return np.vstack(features), targets


def sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def score_matrix(features: np.ndarray, weights: np.ndarray, bias: float) -> np.ndarray:
    return sigmoid(features @ weights + bias)


def aggregate_pages(rows: Sequence[TileRow], scores: Sequence[float]) -> dict[str, tuple[int, float]]:
    if len(rows) != len(scores):
        raise ValueError("rows and scores length mismatch")
    pages: dict[str, tuple[int, float]] = {}
    for row, score in zip(rows, scores, strict=True):
        current_target, current_score = pages.get(row.page_id, (0, 0.0))
        pages[row.page_id] = (max(current_target, row.target), max(current_score, float(score)))
    return pages


def binary_metrics(targets: Sequence[int], scores: Sequence[float], threshold: float) -> dict[str, float | int]:
    if len(targets) != len(scores):
        raise ValueError("targets and scores length mismatch")
    tp = tn = fp = fn = 0
    for target, score in zip(targets, scores, strict=True):
        pred = int(float(score) >= threshold)
        if target == 1 and pred == 1:
            tp += 1
        elif target == 0 and pred == 0:
            tn += 1
        elif target == 0 and pred == 1:
            fp += 1
        else:
            fn += 1
    positives = tp + fn
    negatives = tn + fp
    predicted_positive = tp + fp
    total = positives + negatives
    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "recall": tp / positives if positives else 0.0,
        "precision": tp / predicted_positive if predicted_positive else 0.0,
        "false_negative_rate": fn / positives if positives else 0.0,
        "false_positive_rate": fp / negatives if negatives else 0.0,
        "accuracy": (tp + tn) / total if total else 0.0,
    }


def choose_threshold(
    targets: Sequence[int],
    scores: Sequence[float],
    min_recall: float = 0.99,
) -> tuple[float, dict[str, float | int]]:
    if not 0.0 < min_recall <= 1.0:
        raise ValueError("min_recall must be in (0, 1]")
    candidates = sorted({0.0, 1.0, *[float(score) for score in scores]})
    feasible: list[tuple[float, dict[str, float | int]]] = []
    fallback: list[tuple[float, dict[str, float | int]]] = []
    for threshold in candidates:
        metrics = binary_metrics(targets, scores, threshold)
        fallback.append((threshold, metrics))
        if float(metrics["recall"]) >= min_recall:
            feasible.append((threshold, metrics))
    pool = feasible or fallback
    pool.sort(
        key=lambda item: (
            float(item[1]["false_positive_rate"]),
            -float(item[1]["recall"]),
            -item[0],
        )
    )
    return pool[0]


def page_metrics(rows: Sequence[TileRow], scores: Sequence[float], threshold: float) -> dict[str, float | int]:
    pages = aggregate_pages(rows, scores)
    targets = [target for target, _ in pages.values()]
    page_scores = [score for _, score in pages.values()]
    metrics = binary_metrics(targets, page_scores, threshold)
    metrics["pages"] = len(pages)
    return metrics


def worst_page_errors(
    rows: Sequence[TileRow],
    scores: Sequence[float],
    threshold: float,
    limit: int = 20,
) -> dict[str, list[dict[str, float | str]]]:
    pages = aggregate_pages(rows, scores)
    false_negatives = [
        {"page_id": page_id, "score": score}
        for page_id, (target, score) in pages.items()
        if target == 1 and score < threshold
    ]
    false_positives = [
        {"page_id": page_id, "score": score}
        for page_id, (target, score) in pages.items()
        if target == 0 and score >= threshold
    ]
    false_negatives.sort(key=lambda item: float(item["score"]))
    false_positives.sort(key=lambda item: -float(item["score"]))
    return {
        "false_negatives": false_negatives[:limit],
        "false_positives": false_positives[:limit],
    }
