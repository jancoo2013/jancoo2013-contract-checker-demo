// @ts-nocheck -- executed directly by Node without a test-only type dependency.
import assert from "node:assert/strict";
import test from "node:test";

import { buildTesseractPiiCandidateOverlay } from "../src/piiCandidateOverlay.ts";
import { findDirectValueMatches } from "../src/piiDirectPatterns.ts";

const VALID_ID = "123456782";
const VALID_IBAN = "IL88 1234 5678 9012 3456 789";

function resultWithWords(words, text = words.map((word) => word.text).join(" "), size = {}) {
  return {
    text,
    elapsedMs: 20,
    meanConfidence: 90,
    width: size.width ?? 500,
    height: size.height ?? 200,
    wordBoxes: words,
  };
}

function word(text, confidence, bbox) {
  return { text, confidence, bbox };
}

test("Android direct finder matches the approved high-confidence classes", () => {
  const text = `${VALID_ID}; tenant@example.test; 050-123-4567; ${VALID_IBAN}`;
  const matches = findDirectValueMatches(text);

  assert.deepEqual(
    matches.map((match) => match.piiClass),
    ["israeli_id", "email", "phone", "bank_identifier"],
  );
  assert.deepEqual(
    matches.map((match) => match.detectorId),
    ["direct-israeli-id-v0", "direct-email-v0", "direct-israeli-phone-v0", "direct-israeli-iban-v0"],
  );
  assert.deepEqual(
    matches.map((match) => text.slice(match.start, match.end)),
    [VALID_ID, "tenant@example.test", "050-123-4567", VALID_IBAN],
  );
});

test("finder rejects invalid checksum values and ambiguous numeric shapes", () => {
  const text = [
    "ID 123456783",
    "ID 000000000",
    "generic 111111111",
    "phone 060-123-4567",
    "phone 12-050-123-4567-34",
    "iban IL89 1234 5678 9012 3456 789",
    "account 123456789012",
  ].join("; ");

  assert.deepEqual(findDirectValueMatches(text), []);
});

test("projects only approved candidates and keeps output value-free", () => {
  const overlay = buildTesseractPiiCandidateOverlay(
    resultWithWords(
      [
        word(VALID_ID, 91, [20, 20, 120, 40]),
        word("tenant@example.test", 90, [140, 20, 330, 40]),
        word("050-123-4567", 89, [20, 60, 170, 80]),
        word("IL88", 89, [20, 100, 70, 120]),
        word("1234", 89, [80, 100, 125, 120]),
        word("5678", 89, [135, 100, 180, 120]),
        word("9012", 89, [190, 100, 235, 120]),
        word("3456", 89, [245, 100, 290, 120]),
        word("789", 89, [300, 100, 335, 120]),
        word("3500", 88, [360, 20, 410, 40]),
      ],
      `${VALID_ID} tenant@example.test 050-123-4567; ${VALID_IBAN}; 3500`,
    ),
    500,
    200,
  );

  assert.deepEqual(overlay.summary, {
    totalCandidates: 4,
    bankIdentifier: 1,
    email: 1,
    phone: 1,
    israeliId: 1,
  });
  assert.equal(overlay.candidateRects.length, 9);
  assert.equal(overlay.candidateRects.some((rect) => rect.wordIndex === 9), false);
  assert.equal(overlay.notMaskDecision, true);
  assert.equal(overlay.notCompletePiiCoverage, true);

  const serialized = JSON.stringify(overlay);
  for (const value of [VALID_ID, "tenant@example.test", "050-123-4567", VALID_IBAN]) {
    assert.equal(serialized.includes(value), false);
  }
  assert.equal(Object.keys(overlay.candidateRects[0]).includes("start"), false);
  assert.equal(Object.keys(overlay.candidateRects[0]).includes("end"), false);
  assert.equal(serialized.includes("detectorId"), false);
});

test("supports an empty candidate result without inventing rectangles", () => {
  const overlay = buildTesseractPiiCandidateOverlay(
    resultWithWords([
      word("לחודש", 88, [10, 10, 80, 30]),
      word("3500", 88, [90, 10, 140, 30]),
    ]),
    300,
    300,
  );

  assert.deepEqual(overlay.summary, {
    totalCandidates: 0,
    bankIdentifier: 0,
    email: 0,
    phone: 0,
    israeliId: 0,
  });
  assert.deepEqual(overlay.candidateRects, []);
});

test("fails closed for malformed OCR output and invalid viewports", () => {
  assert.throws(() => buildTesseractPiiCandidateOverlay({}, 100, 100), /OCR result/);
  const valid = resultWithWords([word("050-123-4567", 87, [10, 10, 120, 20])]);
  for (const [width, height] of [
    [0, 100],
    [100, -1],
    [Number.NaN, 100],
    [100, Number.POSITIVE_INFINITY],
  ]) {
    assert.throws(() => buildTesseractPiiCandidateOverlay(valid, width, height), /finite and positive/);
  }
});

test("returns deeply immutable candidate output", () => {
  const overlay = buildTesseractPiiCandidateOverlay(
    resultWithWords([word("050-123-4567", 87, [10, 10, 120, 20])]),
    200,
    100,
  );

  assert.throws(() => {
    overlay.candidateRects[0].left = 999;
  }, TypeError);
  assert.throws(() => {
    overlay.summary.phone = 999;
  }, TypeError);
});
