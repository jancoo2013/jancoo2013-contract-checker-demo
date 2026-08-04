// @ts-nocheck -- executed directly by Node without adding a test-only type dependency.
import assert from "node:assert/strict";
import test from "node:test";

import {
  MAX_TESSERACT_WORD_BOXES,
  validateHebrewOcrResult,
} from "../src/tesseractResult.ts";

function validResult() {
  return {
    text: "synthetic OCR",
    elapsedMs: 25,
    meanConfidence: 91,
    width: 100,
    height: 80,
    wordBoxes: [
      {
        text: "synthetic",
        confidence: 90.5,
        bbox: [10, 12, 60, 30],
      },
    ],
  };
}

test("accepts a bounded in-image word result", () => {
  const result = validResult();
  const validated = validateHebrewOcrResult(result);
  assert.equal(validated.text, result.text);
  assert.deepEqual(validated.wordBoxes, result.wordBoxes);
  assert.deepEqual(validated.directPiiWordBoxes, []);
});

test("rejects malformed or out-of-image coordinates", () => {
  for (const bbox of [
    [10, 10, 10, 20],
    [20, 10, 10, 20],
    [-1, 10, 20, 20],
    [10, 10, 101, 20],
    [10.5, 10, 20, 20],
  ]) {
    const result = validResult();
    result.wordBoxes[0].bbox = bbox;
    assert.throws(() => validateHebrewOcrResult(result), /coordinates|outside/);
  }
});

test("rejects invalid confidence and blank word text", () => {
  const invalidConfidence = validResult();
  invalidConfidence.wordBoxes[0].confidence = Number.NaN;
  assert.throws(() => validateHebrewOcrResult(invalidConfidence), /confidence/);

  const blankText = validResult();
  blankText.wordBoxes[0].text = "   ";
  assert.throws(() => validateHebrewOcrResult(blankText), /text/);
});

test("rejects a word batch beyond the native limit", () => {
  const result = validResult();
  result.wordBoxes = Array.from(
    { length: MAX_TESSERACT_WORD_BOXES + 1 },
    () => ({ text: "x", confidence: 80, bbox: [0, 0, 1, 1] }),
  );
  assert.throws(() => validateHebrewOcrResult(result), /word-box batch/);
});
