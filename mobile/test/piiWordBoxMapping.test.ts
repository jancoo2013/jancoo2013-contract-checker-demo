// @ts-nocheck -- executed directly by Node without adding a test-only type dependency.
import assert from "node:assert/strict";
import test from "node:test";

import {
  MAX_MAPPED_WORD_BOXES,
  buildTesseractWordTextIndex,
  mapTextSpanToTesseractWordBoxes,
} from "../src/piiWordBoxMapping.ts";

function resultWithWords(words, text = words.map((word) => word.text).join(" ")) {
  return {
    text,
    elapsedMs: 20,
    meanConfidence: 90,
    width: 200,
    height: 100,
    wordBoxes: words,
  };
}

function word(text, confidence, bbox) {
  return { text, confidence, bbox };
}

test("indexes exact full OCR text while preserving line boundaries", () => {
  const index = buildTesseractWordTextIndex(
    resultWithWords(
      [
        word("טלפון:", 96, [150, 10, 195, 25]),
        word("050-123", 91, [80, 30, 140, 45]),
        word("4567", 89, [30, 30, 70, 45]),
      ],
      "טלפון:\n050-123 4567\n",
    ),
  );

  assert.equal(index.sourceText, "טלפון:\n050-123 4567\n");
  assert.deepEqual(index.words.map(({ wordIndex, start, end }) => ({ wordIndex, start, end })), [
    { wordIndex: 0, start: 0, end: 6 },
    { wordIndex: 1, start: 7, end: 14 },
    { wordIndex: 2, start: 15, end: 19 },
  ]);
  assert.equal(JSON.stringify(index.words).includes("050-123"), false);
});

test("maps one same-line multi-word value in original RTL iterator order", () => {
  const index = buildTesseractWordTextIndex(
    resultWithWords(
      [
        word("טלפון:", 96, [150, 10, 195, 25]),
        word("050-123", 91, [80, 30, 140, 45]),
        word("4567", 89, [30, 30, 70, 45]),
      ],
      "טלפון:\n050-123 4567\n",
    ),
  );
  const start = index.sourceText.indexOf("050-123");
  const end = start + "050-123 4567".length;
  const mapping = mapTextSpanToTesseractWordBoxes(index, start, end);

  assert.deepEqual(mapping, {
    startWordIndex: 1,
    endWordIndexExclusive: 3,
    wordBoxes: [
      { wordIndex: 1, confidence: 91, bbox: [80, 30, 140, 45] },
      { wordIndex: 2, confidence: 89, bbox: [30, 30, 70, 45] },
    ],
  });
  assert.equal(JSON.stringify(mapping).includes("050-123"), false);
  assert.equal(JSON.stringify(mapping).includes("4567"), false);
});

test("maps a value inside a punctuation-sharing word box", () => {
  const index = buildTesseractWordTextIndex(
    resultWithWords([word("(demo@example.test)", 88, [20, 20, 180, 40])]),
  );
  const start = index.sourceText.indexOf("demo@example.test");
  const end = start + "demo@example.test".length;

  assert.deepEqual(mapTextSpanToTesseractWordBoxes(index, start, end), {
    startWordIndex: 0,
    endWordIndexExclusive: 1,
    wordBoxes: [{ wordIndex: 0, confidence: 88, bbox: [20, 20, 180, 40] }],
  });
});

test("rejects cross-line spans and inconsistent full-text alignment", () => {
  const crossLine = buildTesseractWordTextIndex(
    resultWithWords(
      [
        word("050-123", 90, [80, 10, 140, 25]),
        word("4567", 90, [30, 30, 70, 45]),
      ],
      "050-123\n4567",
    ),
  );
  assert.throws(
    () => mapTextSpanToTesseractWordBoxes(crossLine, 0, crossLine.sourceText.length),
    /line boundary|unsupported whitespace/,
  );

  assert.throws(
    () =>
      buildTesseractWordTextIndex(
        resultWithWords(
          [
            word("abc", 90, [0, 0, 10, 10]),
            word("def", 90, [20, 0, 30, 10]),
          ],
          "abc X def",
        ),
      ),
    /inconsistent|unboxed/,
  );
});

test("rejects forged indexes, malformed spans, whitespace words, and oversized mappings", () => {
  assert.throws(
    () => mapTextSpanToTesseractWordBoxes({ sourceText: "x", words: [] }, 0, 1),
    /trusted builder/,
  );

  const index = buildTesseractWordTextIndex(
    resultWithWords([
      word("abc", 90, [0, 0, 10, 10]),
      word("def", 90, [20, 0, 30, 10]),
    ]),
  );
  for (const [start, end] of [
    [-1, 1],
    [0, 0],
    [2, 1],
    [0, 8],
    [0.5, 1],
    [3, 4],
    [0, 4],
  ]) {
    assert.throws(() => mapTextSpanToTesseractWordBoxes(index, start, end), /span|offsets/);
  }

  assert.throws(
    () =>
      buildTesseractWordTextIndex(
        resultWithWords([word("two words", 90, [0, 0, 20, 10])]),
      ),
    /whitespace/,
  );

  const manyWords = Array.from({ length: MAX_MAPPED_WORD_BOXES + 1 }, (_, index) =>
    word(String(index % 10), 80, [0, 0, 1, 1]),
  );
  const oversized = buildTesseractWordTextIndex(resultWithWords(manyWords));
  assert.throws(
    () => mapTextSpanToTesseractWordBoxes(oversized, 0, oversized.sourceText.length),
    /too many/,
  );
});

test("returns defensive immutable geometry copies", () => {
  const sourceBbox = [10, 10, 30, 20];
  const index = buildTesseractWordTextIndex(
    resultWithWords([word("value", 87, sourceBbox)]),
  );
  sourceBbox[0] = 999;
  assert.deepEqual(index.words[0].bbox, [10, 10, 30, 20]);

  const mapping = mapTextSpanToTesseractWordBoxes(index, 0, 5);
  assert.throws(() => {
    mapping.wordBoxes[0].bbox[0] = 999;
  }, TypeError);
  assert.deepEqual(mapping.wordBoxes[0].bbox, [10, 10, 30, 20]);
});
