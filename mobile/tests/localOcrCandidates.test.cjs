const assert = require("node:assert/strict");
const test = require("node:test");

const {
  countCandidatesByType,
  detectPiiCandidates,
} = require("../.tmp-tests/localOcrCandidates.js");

function item(text, x, y, width = text.length * 10, height = 20) {
  return {
    text,
    confidence: 90,
    bbox: { x, y, width, height },
  };
}

test("detects standalone ID-like values", () => {
  const candidates = detectPiiCandidates([item("123-456-789", 10, 10, 120)]);
  const counts = countCandidatesByType(candidates);

  assert.equal(counts.id_like, 1);
  assert.equal(counts.phone_like, 0);
});

test("does not duplicate phone as an ID-like value", () => {
  const candidates = detectPiiCandidates([item("050-123-4567", 10, 10, 130)]);
  const counts = countCandidatesByType(candidates);

  assert.equal(counts.phone_like, 1);
  assert.equal(counts.id_like, 0);
});

test("detects split-token phone and unions only participating boxes", () => {
  const candidates = detectPiiCandidates([
    item("note", 0, 10, 20),
    item("050", 40, 10, 30),
    item("-", 72, 10, 8),
    item("123", 82, 10, 30),
    item("-", 114, 10, 8),
    item("4567", 124, 10, 40),
    item("tail", 200, 10, 20),
  ]);
  const phone = candidates.find((candidate) => candidate.type === "phone_like");

  assert.ok(phone);
  assert.equal(phone.text, "050-123-4567");
  assert.deepEqual(phone.bbox, { x: 40, y: 10, width: 124, height: 20 });
});

test("detects split-token email", () => {
  const candidates = detectPiiCandidates([
    item("tenant", 10, 10, 60),
    item("@", 72, 10, 10),
    item("example", 84, 10, 70),
    item(".", 156, 10, 6),
    item("invalid", 164, 10, 70),
  ]);
  const counts = countCandidatesByType(candidates);

  assert.equal(counts.email_like, 1);
});

test("does not match ID-like value inside longer numeric sequence", () => {
  const candidates = detectPiiCandidates([item("99123-456-78988", 10, 10, 160)]);
  const counts = countCandidatesByType(candidates);

  assert.equal(counts.id_like, 0);
});

test("preserves OCR iterator order instead of sorting RTL tokens by x", () => {
  const candidates = detectPiiCandidates([
    item("tenant", 300, 10, 60),
    item("@", 260, 10, 10),
    item("example", 180, 10, 70),
    item(".", 168, 10, 6),
    item("invalid", 90, 10, 70),
  ]);
  const counts = countCandidatesByType(candidates);

  assert.equal(counts.email_like, 1);
});
