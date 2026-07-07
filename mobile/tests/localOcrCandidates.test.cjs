const assert = require("node:assert/strict");
const test = require("node:test");

const {
  countProposalsByType,
  detectPiiProposals,
} = require("../.tmp-tests/localOcrCandidates.js");

const IMAGE_SIZE = { width: 900, height: 220 };

function item(text, x, y, width = text.length * 12, height = 24) {
  return {
    text,
    confidence: 90,
    bbox: { x, y, width, height },
  };
}

function proposalsFor(items, imageSize = IMAGE_SIZE) {
  return detectPiiProposals(items, imageSize);
}

test("creates ID proposal from ID anchor with perfect digits", () => {
  const proposals = proposalsFor([item('ת"ז:', 700, 40, 46), item("123456789", 470, 40, 150)]);
  const counts = countProposalsByType(proposals);

  assert.equal(counts.id_field, 1);
  assert.equal(proposals[0].type, "id_field");
  assert.ok(proposals[0].bbox.x + proposals[0].bbox.width <= proposals[0].anchorBbox.x);
});

test("creates ID proposal from ID anchor with corrupted value OCR", () => {
  const proposals = proposalsFor([item('ת"ז:', 700, 40, 46), item("12A?xx", 500, 40, 90)]);
  const counts = countProposalsByType(proposals);

  assert.equal(counts.id_field, 1);
});

test("creates ID proposal from anchor even when value token is missing", () => {
  const proposals = proposalsFor([item('ת"ז:', 700, 40, 46)]);
  const counts = countProposalsByType(proposals);

  assert.equal(counts.id_field, 1);
  assert.ok(proposals[0].bbox.width > 0);
});

test("detects full split-token ID anchor and unions anchor boxes", () => {
  const proposals = proposalsFor([
    item("תעודת", 700, 40, 70),
    item("זהות", 620, 40, 58),
    item("123456789", 380, 40, 150),
  ]);
  const id = proposals.find((proposal) => proposal.type === "id_field");

  assert.ok(id);
  assert.deepEqual(id.anchorBbox, { x: 620, y: 40, width: 150, height: 24 });
});

test("creates phone proposal from phone anchor with corrupted value OCR", () => {
  const proposals = proposalsFor([item("טלפון:", 680, 40, 90), item("05O-?xx", 470, 40, 100)]);
  const counts = countProposalsByType(proposals);

  assert.equal(counts.phone_field, 1);
});

test("creates email proposal from email anchor with corrupted-looking value OCR", () => {
  const proposals = proposalsFor([item("אימייל:", 680, 40, 90), item("t?st@??", 470, 40, 100)]);
  const counts = countProposalsByType(proposals);

  assert.equal(counts.email_field, 1);
});

test("does not create proposal for unrelated 9-digit value without anchor", () => {
  const proposals = proposalsFor([item("123456789", 470, 40, 150)]);
  const counts = countProposalsByType(proposals);

  assert.equal(proposals.length, 0);
  assert.equal(counts.id_field, 0);
});

test("does not create proposal for phone-looking value without anchor", () => {
  const proposals = proposalsFor([item("050-123-4567", 470, 40, 150)]);
  const counts = countProposalsByType(proposals);

  assert.equal(proposals.length, 0);
  assert.equal(counts.phone_field, 0);
});

test("keeps multiple same-line proposals distinct and away from neighbor labels", () => {
  const proposals = proposalsFor([
    item('ת"ז:', 760, 40, 48),
    item("123456789", 555, 40, 135),
    item("טלפון:", 390, 40, 90),
    item("050-000-0000", 120, 40, 170),
  ]);
  const id = proposals.find((proposal) => proposal.type === "id_field");
  const phone = proposals.find((proposal) => proposal.type === "phone_field");

  assert.ok(id);
  assert.ok(phone);
  assert.equal(proposals.length, 2);
  assert.ok(id.bbox.x >= phone.anchorBbox.x + phone.anchorBbox.width);
  assert.ok(phone.bbox.x + phone.bbox.width <= id.bbox.x);
});

test("normalizes ID punctuation and quote variants", () => {
  const dotVariant = proposalsFor([item("ת.ז.:", 700, 40, 56)]);
  const quoteVariant = proposalsFor([item("ת״ז:", 700, 80, 56)]);

  assert.equal(countProposalsByType(dotVariant).id_field, 1);
  assert.equal(countProposalsByType(quoteVariant).id_field, 1);
});

test("detects ID abbreviation split around quote token", () => {
  const proposals = proposalsFor([
    item("ת", 740, 40, 20),
    item('"', 720, 40, 10),
    item("ז", 695, 40, 20),
  ]);

  assert.equal(countProposalsByType(proposals).id_field, 1);
});

test("detects dotted ID abbreviation split into four tokens", () => {
  const proposals = proposalsFor([
    item("ת", 760, 40, 20),
    item(".", 742, 40, 8),
    item("ז", 715, 40, 20),
    item(".", 697, 40, 8),
  ]);

  assert.equal(countProposalsByType(proposals).id_field, 1);
});

test("detects email abbreviation split around quote token", () => {
  const proposals = proposalsFor([
    item("דוא", 760, 40, 45),
    item('"', 738, 40, 10),
    item("ל", 712, 40, 20),
  ]);

  assert.equal(countProposalsByType(proposals).email_field, 1);
});

test("does not treat bare טל as phone anchor", () => {
  const proposals = proposalsFor([item("טל", 700, 40, 40)]);

  assert.equal(countProposalsByType(proposals).phone_field, 0);
  assert.equal(proposals.length, 0);
});

test("detects split-token anchor in source order when x order differs", () => {
  const proposals = proposalsFor([
    item("תעודת", 700, 40, 70),
    item("זהות", 610, 40, 58),
  ]);
  const counts = countProposalsByType(proposals);

  assert.equal(counts.id_field, 1);
});

test("detects split-token anchor in visual RTL order when iterator order differs", () => {
  const proposals = proposalsFor([
    item("זהות", 610, 40, 58),
    item("תעודת", 700, 40, 70),
  ]);
  const counts = countProposalsByType(proposals);

  assert.equal(counts.id_field, 1);
});

test("clamps proposal geometry to image bounds", () => {
  const proposals = proposalsFor([item("טלפון:", 20, 5, 70, 24)], { width: 100, height: 30 });
  const proposal = proposals[0];

  assert.ok(proposal);
  assert.equal(proposal.bbox.x, 0);
  assert.ok(proposal.bbox.y >= 0);
  assert.ok(proposal.bbox.y + proposal.bbox.height <= 30);
  assert.ok(proposal.bbox.x + proposal.bbox.width <= 100);
});
