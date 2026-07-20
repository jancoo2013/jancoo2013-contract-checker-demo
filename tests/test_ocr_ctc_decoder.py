from __future__ import annotations

import unittest

import numpy as np

from research.hebrew_contract_ocr.ctc_decoder import CTCDecoderError, greedy_decode
from research.hebrew_contract_ocr.dataset_contract import load_charset


class OCRCTCDecoderTests(unittest.TestCase):
    def test_rtl_decode_reverses_only_valid_time_and_collapses_ctc(self) -> None:
        charset = load_charset()
        ids = charset.character_to_id
        classes = len(charset.characters) + 1
        logits = np.full((8, 2, classes), -10.0, dtype=np.float32)

        # Left-to-right feature paths. Reversing valid time yields raw CTC paths
        # [א, א, blank, ב, ב] and [1, 1, 2, 2].
        first_visual = [ids["ב"], ids["ב"], 0, ids["א"], ids["א"]]
        second_visual = [ids["2"], ids["2"], ids["1"], ids["1"]]
        for time, class_id in enumerate(first_visual):
            logits[time, 0, class_id] = 10.0
        for time, class_id in enumerate(second_visual):
            logits[time, 1, class_id] = 10.0
        logits[5:, 0, ids["ג"]] = 100.0  # misleading padding must be ignored
        logits[4:, 1, ids["9"]] = 100.0

        result = greedy_decode(logits, [5, 4], charset=charset)

        self.assertEqual([line.text for line in result], ["אב", "12"])
        self.assertEqual(result[0].class_ids, (ids["א"], ids["ב"]))
        self.assertEqual([line.input_length for line in result], [5, 4])

    def test_blank_separates_repeated_characters_and_ltr_is_explicit(self) -> None:
        charset = load_charset()
        ids = charset.character_to_id
        classes = len(charset.characters) + 1
        logits = np.full((5, 1, classes), -1.0, dtype=np.float32)
        for time, class_id in enumerate([ids["A"], ids["A"], 0, ids["A"], ids["A"]]):
            logits[time, 0, class_id] = 1.0

        result = greedy_decode(logits, [5], charset=charset, rtl=False)

        self.assertEqual(result[0].text, "AA")

    def test_invalid_shapes_lengths_classes_and_values_fail_closed(self) -> None:
        charset = load_charset()
        classes = len(charset.characters) + 1
        valid = np.zeros((4, 2, classes), dtype=np.float32)
        cases = (
            (valid[0], [4, 4]),
            (valid, [4]),
            (valid, [0, 4]),
            (valid, [5, 4]),
            (np.zeros((4, 2, classes - 1), dtype=np.float32), [4, 4]),
            (np.full((4, 2, classes), np.nan, dtype=np.float32), [4, 4]),
        )
        for logits, lengths in cases:
            with self.subTest(shape=logits.shape, lengths=lengths):
                with self.assertRaises(CTCDecoderError):
                    greedy_decode(logits, lengths, charset=charset)


if __name__ == "__main__":
    unittest.main()
