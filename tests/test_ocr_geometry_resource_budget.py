from __future__ import annotations

import unittest

from research.hebrew_contract_ocr.geometry_resource_budget import (
    MAX_GEOMETRY_ACCOUNTED_BYTES,
    MAX_SOURCE_LONG_SIDE,
    MAX_SOURCE_PIXELS,
    GeometryResourceBudgetError,
    assess_geometry_resource_budget,
)


class GeometryResourceBudgetTests(unittest.TestCase):
    def test_accounting_is_mode_aware(self) -> None:
        expected = {
            "L": 8,
            "RGB": 16,
            "RGBA": 20,
            "P": 15,
            "F": 21,
        }
        for mode, bytes_per_pixel in expected.items():
            with self.subTest(mode=mode):
                result = assess_geometry_resource_budget((100, 100), mode)
                self.assertEqual(
                    result.accounted_peak_bytes_per_pixel,
                    bytes_per_pixel,
                )
                self.assertEqual(
                    result.accounted_peak_bytes,
                    10_000 * bytes_per_pixel,
                )

    def test_long_side_limit_rejects_without_allocating_image(self) -> None:
        with self.assertRaisesRegex(GeometryResourceBudgetError, "long-side limit"):
            assess_geometry_resource_budget((MAX_SOURCE_LONG_SIDE + 1, 1), "L")

    def test_pixel_limit_rejects_without_allocating_image(self) -> None:
        self.assertLessEqual(6_000, MAX_SOURCE_LONG_SIDE)
        self.assertGreater(36_000_000, MAX_SOURCE_PIXELS)
        with self.assertRaisesRegex(GeometryResourceBudgetError, "pixel safety limit"):
            assess_geometry_resource_budget((6_000, 6_000), "L")

    def test_mode_budget_rejects_rgba_where_same_rgb_size_is_allowed(self) -> None:
        size = (5_000, 5_000)
        rgb = assess_geometry_resource_budget(size, "RGB")
        self.assertLessEqual(rgb.accounted_peak_bytes, MAX_GEOMETRY_ACCOUNTED_BYTES)

        with self.assertRaisesRegex(
            GeometryResourceBudgetError,
            "accounted-memory budget",
        ):
            assess_geometry_resource_budget(size, "RGBA")

    def test_unsupported_mode_fails_closed(self) -> None:
        with self.assertRaisesRegex(GeometryResourceBudgetError, "unsupported"):
            assess_geometry_resource_budget((100, 100), "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
