// @ts-nocheck -- executed directly by Node without adding a test-only type dependency.
import assert from "node:assert/strict";
import test from "node:test";

import {
  MAX_TESSERACT_WORD_BOXES,
  MIN_TESSERACT_PII_MEAN_CONFIDENCE,
  assessHebrewOcrForPiiMasking,
  validateHebrewOcrForPiiMasking,
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

test("accepts a bounded high-quality in-image word result", () => {
  const result = validResult();
  assert.equal(validateHebrewOcrResult(result), result);
  assert.equal(validateHebrewOcrForPiiMasking(result), result);
  assert.deepEqual(assessHebrewOcrForPiiMasking(result), {
    usableForPiiMasking: true,
    blockingReasons: [],
    diagnostics: {
      meanConfidence: 91,
      minimumMeanConfidence: MIN_TESSERACT_PII_MEAN_CONFIDENCE,
      wordBoxCount: 1,
      ambiguousWordBoxCount: 0,
    },
  });
});

test("blocks low-confidence OCR before PII overlay construction", () => {
  const result = validResult();
  result.meanConfidence = 38;

  const assessment = assessHebrewOcrForPiiMasking(result);
  assert.equal(assessment.usableForPiiMasking, false);
  assert.deepEqual(assessment.blockingReasons, ["mean_confidence_below_threshold"]);
  assert.throws(
    () => validateHebrewOcrForPiiMasking(result),
    /OCR unusable — masking blocked: mean confidence 38 is below 60/,
  );
});

test("blocks whitespace-bearing ambiguous word boxes without exposing their value", () => {
  const result = validResult();
  result.text = "sensitive value";
  result.wordBoxes[0].text = "sensitive value";

  const assessment = assessHebrewOcrForPiiMasking(result);
  assert.deepEqual(assessment.blockingReasons, ["ambiguous_word_boxes"]);
  assert.equal(assessment.diagnostics.ambiguousWordBoxCount, 1);
  assert.equal(JSON.stringify(assessment).includes("sensitive value"), false);
  assert.throws(
    () => validateHebrewOcrForPiiMasking(result),
    /OCR unusable — masking blocked: 1 ambiguous word box contains whitespace/,
  );
});

test("keeps empty OCR structurally valid but blocks it for PII masking", () => {
  const result = validResult();
  result.text = "";
  result.wordBoxes = [];
  result.meanConfidence = 0;

  assert.equal(validateHebrewOcrResult(result), result);
  assert.deepEqual(assessHebrewOcrForPiiMasking(result).blockingReasons, [
    "no_word_boxes",
    "mean_confidence_below_threshold",
  ]);
  assert.throws(
    () => validateHebrewOcrForPiiMasking(result),
    /no OCR word boxes were returned; mean confidence 0 is below 60/,
  );
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

test("returns deeply immutable value-free quality diagnostics", () => {
  const assessment = assessHebrewOcrForPiiMasking(validResult());

  assert.throws(() => {
    assessment.blockingReasons.push("no_word_boxes");
  }, TypeError);
  assert.throws(() => {
    assessment.diagnostics.wordBoxCount = 999;
  }, TypeError);
});
