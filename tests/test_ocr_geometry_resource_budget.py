from __future__ import annotations

import unittest

from research.hebrew_contract_ocr.geometry_resource_budget import (
    MAX_GEOMETRY_ACCOUNTED_BYTES,
    MAX_SOURCE_LONG_SIDE,
    MAX_SOURCE_PIXELS,
    PERSISTENT_PREVIEW_BYTES_PER_PIXEL,
    PREVIEW_ANALYSIS_WORKING_BYTES_PER_PIXEL,
    PREVIEW_LONG_SIDE,
    GeometryResourceBudgetError,
    assess_geometry_resource_budget,
)


class GeometryResourceBudgetTests(unittest.TestCase):
    def test_accounting_is_mode_aware_and_phase_explicit(self) -> None:
        expected = {
            "L": (1, 8),
            "RGB": (3, 16),
            "RGBA": (4, 20),
            "P": (1, 15),
            "F": (4, 21),
        }
        for mode, (source_bytes, transform_bytes) in expected.items():
            with self.subTest(mode=mode):
                result = assess_geometry_resource_budget((100, 100), mode)
                self.assertEqual(result.source_bytes_per_pixel, source_bytes)
                self.assertEqual(
                    result.transform_peak_bytes_per_pixel,
                    transform_bytes,
                )
                self.assertEqual(result.preview_size, (100, 100))
                self.assertEqual(result.preview_pixels, 10_000)
                self.assertEqual(
                    result.transform_phase_bytes,
                    10_000
                    * (transform_bytes + PERSISTENT_PREVIEW_BYTES_PER_PIXEL),
                )
                self.assertEqual(
                    result.preview_analysis_phase_bytes,
                    10_000
                    * (source_bytes + PREVIEW_ANALYSIS_WORKING_BYTES_PER_PIXEL),
                )
                self.assertEqual(
                    result.accounted_peak_bytes,
                    max(
                        result.transform_phase_bytes,
                        result.preview_analysis_phase_bytes,
                    ),
                )

    def test_preview_accounting_uses_the_same_bounded_long_side(self) -> None:
        result = assess_geometry_resource_budget((2_400, 3_200), "L")

        self.assertEqual(result.preview_size, (1_350, PREVIEW_LONG_SIDE))
        self.assertEqual(result.preview_pixels, 1_350 * PREVIEW_LONG_SIDE)

    def test_preview_working_set_can_be_the_accounted_peak(self) -> None:
        result = assess_geometry_resource_budget((1_800, 1_800), "L")

        self.assertGreater(
            result.preview_analysis_phase_bytes,
            result.transform_phase_bytes,
        )
        self.assertEqual(
            result.accounted_peak_bytes,
            result.preview_analysis_phase_bytes,
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
        size = (4_900, 4_900)
        rgb = assess_geometry_resource_budget(size, "RGB")
        self.assertLessEqual(rgb.accounted_peak_bytes, MAX_GEOMETRY_ACCOUNTED_BYTES)

        with self.assertRaisesRegex(
            GeometryResourceBudgetError,
            "accounted-memory budget",
        ):
            assess_geometry_resource_budget(size, "RGBA")

    def test_lab_mode_fails_closed_at_resource_contract(self) -> None:
        with self.assertRaisesRegex(GeometryResourceBudgetError, "unsupported"):
            assess_geometry_resource_budget((100, 100), "LAB")

    def test_supported_convertible_mode_remains_allowed(self) -> None:
        result = assess_geometry_resource_budget((100, 100), "YCbCr")
        self.assertEqual(result.source_mode, "YCbCr")
        self.assertGreater(result.accounted_peak_bytes, 0)

    def test_unsupported_mode_fails_closed(self) -> None:
        for mode in ("UNKNOWN", None):
            with self.subTest(mode=mode), self.assertRaisesRegex(
                GeometryResourceBudgetError,
                "unsupported",
            ):
                assess_geometry_resource_budget((100, 100), mode)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
