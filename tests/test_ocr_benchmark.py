from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research.ocr_benchmark.benchmark import (
    PageResult,
    build_chandra_command,
    build_surya_command,
    discover_images,
    html_to_text,
    load_chandra_results,
    load_surya_results,
    summarize_model,
    write_normalized,
)


class OCRBenchmarkTests(unittest.TestCase):
    def test_html_to_text_preserves_readable_lines(self):
        value = "<p>שלום <b>עולם</b></p><div>שורה שנייה<br>סוף</div>"

        self.assertEqual(html_to_text(value), "שלום עולם\nשורה שנייה\nסוף")

    def test_discover_images_is_sorted_and_requires_unique_stems(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "b.png").write_bytes(b"x")
            (root / "a.jpg").write_bytes(b"x")

            self.assertEqual([path.name for path in discover_images(root)], ["a.jpg", "b.png"])

            (root / "a.png").write_bytes(b"x")
            with self.assertRaisesRegex(ValueError, "stems must be unique"):
                discover_images(root)

    def test_load_surya_results_normalizes_text_blocks_and_bbox(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "page_01.jpg"
            input_path.write_bytes(b"x")
            raw_dir = root / "raw"
            raw_dir.mkdir()
            payload = {
                "page_01": [
                    {
                        "blocks": [
                            {
                                "html": "<p>חוזה שכירות</p>",
                                "bbox": [1, 2, 30, 40],
                                "polygon": [[1, 2], [30, 2], [30, 40], [1, 40]],
                                "label": "Text",
                                "confidence": 0.9,
                            }
                        ],
                        "image_bbox": [0, 0, 100, 200],
                    }
                ]
            }
            (raw_dir / "results.json").write_text(json.dumps(payload), encoding="utf-8")

            results = load_surya_results(raw_dir, [input_path])

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].text, "חוזה שכירות")
            self.assertEqual(results[0].blocks[0]["bbox"], [1, 2, 30, 40])
            self.assertEqual(results[0].metadata["image_bbox"], [0, 0, 100, 200])

    def test_load_chandra_results_normalizes_markdown_and_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "page_01.jpg"
            input_path.write_bytes(b"x")
            document_dir = root / "raw" / "page_01"
            document_dir.mkdir(parents=True)
            (document_dir / "page_01.md").write_text("# חוזה\n\nטקסט", encoding="utf-8")
            metadata = {
                "num_pages": 1,
                "total_token_count": 17,
                "total_chunks": 2,
                "pages": [{"page_num": 0, "page_box": [0, 0, 100, 200]}],
            }
            (document_dir / "page_01_metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8"
            )

            results = load_chandra_results(root / "raw", [input_path])

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].text, "# חוזה\n\nטקסט")
            self.assertEqual(results[0].metadata["token_count"], 17)
            self.assertEqual(results[0].blocks, [])

    def test_write_normalized_and_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            results = [
                PageResult(
                    model="surya2",
                    document_id="page_01",
                    source_name="page_01.jpg",
                    page_number=1,
                    text="שלום",
                    blocks=[{"text": "שלום"}],
                    metadata={},
                )
            ]

            written = write_normalized(results, output_dir)
            summary = summarize_model(results, runtime_seconds=2.0)

            self.assertEqual(len(written), 2)
            self.assertEqual((output_dir / "surya2" / "page_01.txt").read_text(encoding="utf-8"), "שלום\n")
            self.assertEqual(summary["pages"], 1)
            self.assertEqual(summary["seconds_per_page"], 2.0)
            self.assertEqual(summary["blocks"], 1)

    def test_command_builders_use_documented_cli_shapes(self):
        surya = build_surya_command(
            "surya_ocr",
            Path("dataset"),
            Path("artifacts/raw/surya2"),
            ["--keep_server"],
        )
        chandra = build_chandra_command(
            "chandra",
            Path("dataset"),
            Path("artifacts/raw/chandra2"),
            "hf",
            ["--batch-size", "1"],
        )

        self.assertEqual(
            surya,
            [
                "surya_ocr",
                "dataset",
                "--output_dir",
                "artifacts/raw/surya2",
                "--keep_server",
            ],
        )
        self.assertEqual(
            chandra,
            [
                "chandra",
                "dataset",
                "artifacts/raw/chandra2",
                "--method",
                "hf",
                "--no-images",
                "--no-html",
                "--batch-size",
                "1",
            ],
        )


if __name__ == "__main__":
    unittest.main()
