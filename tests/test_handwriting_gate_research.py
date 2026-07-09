from __future__ import annotations

import unittest
from pathlib import Path

from research.handwriting_gate.gate_baseline import (
    HAND_MARK_PRESENT,
    PRINTED_ONLY,
    TileRow,
    aggregate_pages,
    choose_threshold,
    page_metrics,
    stable_split,
)
from research.handwriting_gate.prepare_tiles import MarkBox, iter_tile_boxes, tile_has_mark


class HandwritingGateResearchTests(unittest.TestCase):
    def test_stable_split_is_deterministic(self):
        self.assertEqual(stable_split("template-001"), stable_split("template-001"))
        self.assertIn(stable_split("template-002"), {"train", "val", "test"})

    def test_tiling_covers_right_and_bottom_edges(self):
        boxes = list(iter_tile_boxes(width=1000, height=700, tile_size=384, stride=256))
        self.assertTrue(any(right == 1000 for _, _, right, _ in boxes))
        self.assertTrue(any(bottom == 700 for _, _, _, bottom in boxes))

    def test_tile_is_positive_when_mark_center_is_inside(self):
        tile = (0, 0, 384, 384)
        self.assertTrue(tile_has_mark(tile, (MarkBox(100, 120, 40, 20),)))
        self.assertFalse(tile_has_mark(tile, (MarkBox(500, 500, 40, 20),)))

    def test_page_aggregation_uses_max_tile_risk_and_any_positive_target(self):
        rows = [
            TileRow(path=Path("unused"), label=PRINTED_ONLY, group_id="g", page_id="p", split="test"),
            TileRow(path=Path("unused"), label=HAND_MARK_PRESENT, group_id="g", page_id="p", split="test"),
        ]
        pages = aggregate_pages(rows, [0.1, 0.8])
        self.assertEqual(pages["p"], (1, 0.8))

    def test_threshold_selection_prefers_recall_constraint_then_lower_fpr(self):
        targets = [1, 1, 0, 0]
        scores = [0.9, 0.7, 0.8, 0.2]
        threshold, metrics = choose_threshold(targets, scores, min_recall=1.0)
        self.assertLessEqual(threshold, 0.7)
        self.assertEqual(metrics["recall"], 1.0)

    def test_page_metrics_are_page_level_not_tile_level(self):
        rows = [
            TileRow(path=Path("unused"), label=PRINTED_ONLY, group_id="g1", page_id="clean", split="test"),
            TileRow(path=Path("unused"), label=PRINTED_ONLY, group_id="g1", page_id="clean", split="test"),
            TileRow(path=Path("unused"), label=HAND_MARK_PRESENT, group_id="g2", page_id="marked", split="test"),
        ]
        metrics = page_metrics(rows, [0.1, 0.2, 0.9], threshold=0.5)
        self.assertEqual(metrics["pages"], 2)
        self.assertEqual(metrics["tp"], 1)
        self.assertEqual(metrics["tn"], 1)


if __name__ == "__main__":
    unittest.main()
