from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from research.handwriting_gate.prepare_paired_bags import Pair
from research.handwriting_gate.prepare_region_bags import (
    NEGATIVE_BAG,
    POSITIVE_BAG,
    dilate_mask,
    label_components,
    prepare_pair_regions,
)
from research.handwriting_gate.train_region_mil_lopo import (
    Bag,
    _smooth_max_logit_and_feature_gradient,
    run_lopo,
    train_mil,
)


class RegionBagPreparationTests(unittest.TestCase):
    def test_component_labeling_keeps_separate_regions(self):
        mask = np.zeros((40, 40), dtype=bool)
        mask[2:12, 3:13] = True
        mask[25:35, 26:36] = True

        labels, components = label_components(mask, min_area=20)

        self.assertEqual(len(components), 2)
        self.assertNotEqual(labels[5, 5], 0)
        self.assertNotEqual(labels[30, 30], 0)
        self.assertNotEqual(labels[5, 5], labels[30, 30])

    def test_small_components_are_filtered(self):
        mask = np.zeros((20, 20), dtype=bool)
        mask[1:3, 1:3] = True
        mask[8:18, 8:18] = True

        _, components = label_components(mask, min_area=20)

        self.assertEqual(len(components), 1)
        self.assertGreaterEqual(components[0].area, 100)

    def test_dilation_expands_exclusion_area(self):
        mask = np.zeros((15, 15), dtype=bool)
        mask[7, 7] = True

        expanded = dilate_mask(mask, radius=2)

        self.assertTrue(expanded[5, 5])
        self.assertTrue(expanded[9, 9])
        self.assertFalse(expanded[0, 0])

    def test_pair_preparation_creates_region_bags_and_original_only_tiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original_path = root / "original.jpg"
            redacted_path = root / "redacted.jpg"
            output_dir = root / "prepared"

            original = Image.new("RGB", (128, 128), (70, 70, 70))
            original.save(original_path, quality=100)
            redacted = original.copy()
            draw = ImageDraw.Draw(redacted)
            draw.rectangle((8, 8, 35, 35), fill="white")
            draw.rectangle((88, 88, 119, 119), fill="white")
            redacted.save(redacted_path, quality=100)

            rows, report = prepare_pair_regions(
                pair=Pair("page_1", original_path, redacted_path),
                output_dir=output_dir,
                tile_size=64,
                stride=64,
                diff_threshold=30,
                component_min_area=100,
                component_tile_min_fraction=0.01,
                negative_exclusion_radius=1,
            )

            positive_bags = {row.bag_id for row in rows if row.bag_label == POSITIVE_BAG}
            negative_rows = [row for row in rows if row.bag_label == NEGATIVE_BAG]
            self.assertEqual(len(positive_bags), 2)
            self.assertGreaterEqual(len(negative_rows), 1)
            self.assertEqual(report["components"], 2)

            positive_tile = next(row for row in rows if row.bag_label == POSITIVE_BAG)
            saved_mean = float(np.asarray(Image.open(positive_tile.path).convert("L"), dtype=np.float32).mean())
            self.assertLess(saved_mean, 120.0)


class RegionMilTests(unittest.TestCase):
    def test_smooth_max_gradient_has_expected_shape(self):
        features = np.asarray([[0.0, 1.0], [2.0, 0.0]], dtype=np.float32)
        weights = np.asarray([1.0, -0.5], dtype=np.float32)

        bag_logit, gradient = _smooth_max_logit_and_feature_gradient(
            features,
            weights,
            bias=0.0,
            temperature=0.25,
        )

        self.assertTrue(np.isfinite(bag_logit))
        self.assertEqual(gradient.shape, (2,))
        self.assertTrue(np.all(np.isfinite(gradient)))

    def test_training_returns_finite_model(self):
        bags = [
            Bag("p1", "1", 1, np.asarray([[2.0, 2.0], [0.1, 0.0]], dtype=np.float32)),
            Bag("p2", "2", 1, np.asarray([[2.5, 1.5]], dtype=np.float32)),
            Bag("n1", "1", 0, np.asarray([[-2.0, -1.5]], dtype=np.float32)),
            Bag("n2", "2", 0, np.asarray([[-1.5, -2.0]], dtype=np.float32)),
        ]

        model = train_mil(bags, epochs=50, learning_rate=0.05, l2=1e-4, temperature=0.25)

        self.assertTrue(np.all(np.isfinite(model.weights)))
        self.assertTrue(np.isfinite(model.bias))

    def test_lopo_reports_all_pages(self):
        bags = []
        for page in ("1", "2", "3"):
            offset = float(page)
            bags.append(
                Bag(
                    bag_id=f"{page}_positive",
                    page_id=page,
                    target=1,
                    features=np.asarray([[2.0 + 0.1 * offset, 2.0], [0.0, 0.1]], dtype=np.float32),
                )
            )
            bags.append(
                Bag(
                    bag_id=f"{page}_negative",
                    page_id=page,
                    target=0,
                    features=np.asarray([[-2.0, -2.0 - 0.1 * offset]], dtype=np.float32),
                )
            )

        report = run_lopo(
            bags=bags,
            epochs=80,
            learning_rate=0.05,
            l2=1e-4,
            temperature=0.25,
            min_recall=1.0,
        )

        self.assertEqual(len(report["folds"]), 3)
        self.assertEqual(report["aggregate"]["positive_pages_total"], 3)
        self.assertIn("region_recall", report["aggregate"])
        self.assertIn("negative_tile_false_positive_rate", report["aggregate"])


if __name__ == "__main__":
    unittest.main()
