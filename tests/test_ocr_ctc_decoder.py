from __future__ import annotations

import unittest

import numpy as np

from research.hebrew_contract_ocr.ctc_decoder import CTCDecoderError, greedy_decode
from research.hebrew_contract_ocr.dataset_contract import load_charset
from research.hebrew_contract_ocr.text_order import (
    TextOrderError,
    logical_to_visual_rtl,
    visual_to_logical_rtl,
)


def _path_for_text(text: str, character_to_id: dict[str, int]) -> list[int]:
    path: list[int] = []
    previous: int | None = None
    for character in text:
        class_id = character_to_id[character]
        if class_id == previous:
            path.append(0)
        path.extend((class_id, class_id))
        previous = class_id
    return path


def _logits_for_paths(
    paths: list[list[int]],
    classes: int,
    padding_id: int,
) -> tuple[np.ndarray, list[int]]:
    time = max(len(path) for path in paths) + 3
    logits = np.full((time, len(paths), classes), -10.0, dtype=np.float32)
    lengths: list[int] = []
    for batch_index, path in enumerate(paths):
        lengths.append(len(path))
        for time_index, class_id in enumerate(path):
            logits[time_index, batch_index, class_id] = 10.0
        logits[len(path) :, batch_index, padding_id] = 100.0
    return logits, lengths


class OCRCTCDecoderTests(unittest.TestCase):
    def test_rtl_decode_restores_supported_logical_runs_and_ignores_padding(self) -> None:
        charset = load_charset()
        ids = charset.character_to_id
        visual_texts = [
            "בא",
            "123",
            "AS-IS",
            "AS-IS 2.1 רכושה",
            "%12 :(בא)",
        ]
        paths = [_path_for_text(text, ids) for text in visual_texts]
        logits, lengths = _logits_for_paths(
            paths,
            len(charset.characters) + 1,
            ids["ג"],
        )

        result = greedy_decode(logits, lengths, charset=charset)

        expected = [
            "אב",
            "123",
            "AS-IS",
            "השוכר 2.1 AS-IS",
            "(אב): 12%",
        ]
        self.assertEqual([line.text for line in result], expected)
        self.assertEqual(
            result[3].class_ids,
            tuple(ids[character] for character in expected[3]),
        )
        self.assertEqual([line.input_length for line in result], lengths)

    def test_supported_rtl_contract_is_reversible(self) -> None:
        logical_lines = (
            "אב",
            "השוכר 2.1 AS-IS",
            "(אב): 12%",
            "א - ב",
            "אב  (AS-IS)",
        )
        for logical in logical_lines:
            with self.subTest(logical=logical):
                visual = logical_to_visual_rtl(logical)
                self.assertEqual(visual_to_logical_rtl(visual), logical)

    def test_blank_separates_repeated_characters_and_ltr_is_explicit(self) -> None:
        charset = load_charset()
        ids = charset.character_to_id
        classes = len(charset.characters) + 1
        logits = np.full((5, 1, classes), -1.0, dtype=np.float32)
        for time, class_id in enumerate([ids["A"], ids["A"], 0, ids["A"], ids["A"]]):
            logits[time, 0, class_id] = 1.0

        result = greedy_decode(logits, [5], charset=charset, rtl=False)

        self.assertEqual(result[0].text, "AA")
        self.assertEqual(result[0].class_ids, (ids["A"], ids["A"]))

    def test_no_space_mixed_direction_token_fails_closed(self) -> None:
        charset = load_charset()
        ids = charset.character_to_id
        path = _path_for_text("Aא", ids)
        logits, lengths = _logits_for_paths(
            [path],
            len(charset.characters) + 1,
            ids["ג"],
        )

        with self.assertRaisesRegex(CTCDecoderError, "ASCII-space boundary"):
            greedy_decode(logits, lengths, charset=charset)
        with self.assertRaises(TextOrderError):
            logical_to_visual_rtl("אA")

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
