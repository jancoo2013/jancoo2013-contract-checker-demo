// @ts-nocheck -- executed directly by Node without a test-only type dependency.
import assert from "node:assert/strict";
import test from "node:test";

import {
  buildTesseractDevelopmentInspectionOverlay,
} from "../src/piiDevelopmentOverlayInspection.ts";

function resultWithWords(words, text = words.map((word) => word.text).join(" "), size = {}) {
  return {
    text,
    elapsedMs: 20,
    meanConfidence: 90,
    width: size.width ?? 200,
    height: size.height ?? 100,
    wordBoxes: words,
  };
}

function word(text, confidence, bbox) {
  return { text, confidence, bbox };
}

test("projects every real OCR word box through the trusted development path", () => {
  const overlay = buildTesseractDevelopmentInspectionOverlay(
    resultWithWords([
      word("050-123", 91, [80, 30, 140, 45]),
      word("4567", 89, [30, 30, 70, 45]),
    ]),
    300,
    300,
  );

  assert.deepEqual(overlay, {
    developmentOnly: true,
    inspectionOnly: "all-ocr-word-boxes",
    notPiiDecision: true,
    opacity: 0.35,
    renderedImage: { left: 0, top: 75, width: 300, height: 150 },
    wordRects: [
      { wordIndex: 0, left: 120, top: 120, width: 90, height: 22.5 },
      { wordIndex: 1, left: 45, top: 120, width: 60, height: 22.5 },
    ],
  });
});

test("keeps the inspection output value-free and distinct from a PII decision", () => {
  const overlay = buildTesseractDevelopmentInspectionOverlay(
    resultWithWords([word("demo@example.test", 88, [20, 20, 180, 40])]),
    200,
    100,
  );
  const serialized = JSON.stringify(overlay);

  assert.equal(serialized.includes("demo@example.test"), false);
  assert.equal(serialized.includes("confidence"), false);
  assert.equal(serialized.includes("enclosingBbox"), false);
  assert.equal(overlay.notPiiDecision, true);
});

test("supports an empty valid OCR result without inventing rectangles", () => {
  const overlay = buildTesseractDevelopmentInspectionOverlay(
    resultWithWords([], "", { width: 100, height: 200 }),
    300,
    300,
  );

  assert.deepEqual(overlay.renderedImage, { left: 75, top: 0, width: 150, height: 300 });
  assert.deepEqual(overlay.wordRects, []);
});

test("fails closed for malformed OCR output and invalid viewports", () => {
  assert.throws(
    () => buildTesseractDevelopmentInspectionOverlay({}, 100, 100),
    /OCR result/,
  );
  const valid = resultWithWords([word("value", 87, [10, 10, 30, 20])]);
  for (const [width, height] of [
    [0, 100],
    [100, -1],
    [Number.NaN, 100],
    [100, Number.POSITIVE_INFINITY],
  ]) {
    assert.throws(
      () => buildTesseractDevelopmentInspectionOverlay(valid, width, height),
      /finite and positive/,
    );
  }
});

test("returns deeply immutable inspection geometry", () => {
  const overlay = buildTesseractDevelopmentInspectionOverlay(
    resultWithWords([word("value", 87, [10, 10, 30, 20])]),
    200,
    100,
  );

  assert.throws(() => {
    overlay.wordRects[0].left = 999;
  }, TypeError);
  assert.throws(() => {
    overlay.renderedImage.left = 999;
  }, TypeError);
  assert.deepEqual(overlay.wordRects[0], {
    wordIndex: 0,
    left: 10,
    top: 10,
    width: 20,
    height: 10,
  });
});
