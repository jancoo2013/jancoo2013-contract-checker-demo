from pathlib import Path


segmenter = Path("research/hebrew_contract_ocr/line_segmenter.py")
text = segmenter.read_text(encoding="utf-8")

old_constants = """MIN_ACTIVE_ROW_INK_RATIO = 0.0015
MAX_ACTIVE_ROW_GAP = 2
MIN_TEXTLIKE_HEIGHT = 12
"""
new_constants = """MIN_ACTIVE_ROW_INK_RATIO = 0.0015
MAX_ACTIVE_ROW_GAP = 2
MAX_SPARSE_ROW_EXPANSION = 3
MAX_UNRESOLVED_BAND_HEIGHT_RATIO = 0.10
MAX_UNRESOLVED_BAND_HEIGHT_PIXELS = 180
MIN_TEXTLIKE_HEIGHT = 12
"""
if text.count(old_constants) != 1:
    raise SystemExit("constant anchor mismatch")
text = text.replace(old_constants, new_constants, 1)

old_segmentation = """    row_ink = np.count_nonzero(ink, axis=1)
    minimum_active_ink = max(3, int(math.ceil(width * MIN_ACTIVE_ROW_INK_RATIO)))
    active_runs = _runs(row_ink >= minimum_active_ink, max_gap=MAX_ACTIVE_ROW_GAP)

    expanded_runs: list[tuple[int, int]] = []
    for y0, y1 in active_runs:
        while y0 > 0 and row_ink[y0 - 1] > 0:
            y0 -= 1
        while y1 < height and row_ink[y1] > 0:
            y1 += 1
        if expanded_runs and y0 <= expanded_runs[-1][1]:
            expanded_runs[-1] = (expanded_runs[-1][0], max(expanded_runs[-1][1], y1))
        else:
            expanded_runs.append((y0, y1))
"""
new_segmentation = """    row_ink = np.count_nonzero(ink, axis=1)
    minimum_active_ink = max(3, int(math.ceil(width * MIN_ACTIVE_ROW_INK_RATIO)))
    active_runs = _runs(row_ink >= minimum_active_ink, max_gap=MAX_ACTIVE_ROW_GAP)

    expanded_runs: list[tuple[int, int]] = []
    for y0, y1 in active_runs:
        top_expansion = 0
        while (
            y0 > 0
            and row_ink[y0 - 1] > 0
            and top_expansion < MAX_SPARSE_ROW_EXPANSION
        ):
            y0 -= 1
            top_expansion += 1
        bottom_expansion = 0
        while (
            y1 < height
            and row_ink[y1] > 0
            and bottom_expansion < MAX_SPARSE_ROW_EXPANSION
        ):
            y1 += 1
            bottom_expansion += 1
        if expanded_runs and y0 <= expanded_runs[-1][1]:
            expanded_runs[-1] = (expanded_runs[-1][0], max(expanded_runs[-1][1], y1))
        else:
            expanded_runs.append((y0, y1))

    max_unresolved_band_height = max(
        MAX_UNRESOLVED_BAND_HEIGHT_PIXELS,
        int(math.ceil(height * MAX_UNRESOLVED_BAND_HEIGHT_RATIO)),
    )
    if any(y1 - y0 > max_unresolved_band_height for y0, y1 in expanded_runs):
        raise LineSegmentationError(
            "unresolved oversized foreground band; safer preprocessing is required"
        )
"""
if text.count(old_segmentation) != 1:
    raise SystemExit("segmentation anchor mismatch")
segmenter.write_text(text.replace(old_segmentation, new_segmentation, 1), encoding="utf-8")


tests = Path("tests/test_ocr_line_segmenter.py")
text = tests.read_text(encoding="utf-8")
anchor = """    def test_separate_but_close_lines_receive_review_reason(self) -> None:
"""
inserted = """    def test_sparse_vertical_connector_does_not_merge_distant_lines(self) -> None:
        page = Image.new("L", (600, 700), 255)
        draw = ImageDraw.Draw(page)
        expected = [
            (80, 80, 520, 100),
            (80, 280, 520, 300),
            (80, 480, 520, 500),
        ]
        for bbox in expected:
            _draw_text_band(draw, bbox)
        draw.line((300, 100, 300, 480), fill=0, width=2)

        result = segment_page(page)

        text_lines = [
            line for line in result.lines
            if "foreground_too_small" not in line.reasons
        ]
        self.assertEqual(len(text_lines), 3)
        self.assertTrue(all(line.bbox[3] - line.bbox[1] < 60 for line in text_lines))
        self.assertTrue(
            all(
                line.bbox[3] - line.bbox[1] <= 100
                or "foreground_too_small" in line.reasons
                for line in result.lines
            )
        )

    def test_unresolved_wide_connector_band_fails_closed(self) -> None:
        page = Image.new("L", (600, 1000), 255)
        draw = ImageDraw.Draw(page)
        _draw_text_band(draw, (80, 100, 520, 140))
        _draw_text_band(draw, (80, 700, 520, 740))
        for x in (160, 240, 320, 400):
            draw.line((x, 140, x, 700), fill=0, width=2)

        with self.assertRaisesRegex(
            LineSegmentationError,
            "unresolved oversized foreground band",
        ):
            segment_page(page)

    def test_separate_but_close_lines_receive_review_reason(self) -> None:
"""
if text.count(anchor) != 1:
    raise SystemExit("test anchor mismatch")
tests.write_text(text.replace(anchor, inserted, 1), encoding="utf-8")


runtime = Path(".github/workflows/ocr-research-runtime.yml")
text = runtime.read_text(encoding="utf-8")
old_suite = """          tests.test_ocr_pii_review_pack_builder
          tests.test_ocr_recognizer_input
"""
new_suite = """          tests.test_ocr_pii_review_pack_builder
          tests.test_ocr_line_segmenter
          tests.test_ocr_recognizer_input
"""
if text.count(old_suite) != 1:
    raise SystemExit("workflow anchor mismatch")
runtime.write_text(text.replace(old_suite, new_suite, 1), encoding="utf-8")

Path(".github/workflows/codex-line-segmentation-patch.yml").unlink()
Path("tools/codex_line_segmentation_patch.py").unlink()
