// @ts-nocheck
import assert from "node:assert/strict";
import test from "node:test";
import {
  buildTesseractCandidateGeometry,
  buildTesseractWordTextIndex,
  mapTextSpanToTesseractWordBoxes,
} from "../src/piiWordBoxMapping.ts";
import {
  PRODUCTION_MASK_ALPHA,
  PRODUCTION_MASK_GRAYSCALE,
  renderTesseractProductionMask,
} from "../src/piiProductionMaskRenderer.ts";

function word(text, bbox) {
  return { text, confidence: 90, bbox };
}

function trustedGeometry(words, width, height, text = words.map((item) => item.text).join(" ")) {
  const index = buildTesseractWordTextIndex({
    text,
    elapsedMs: 10,
    meanConfidence: 90,
    width,
    height,
    wordBoxes: words,
  });
  return buildTesseractCandidateGeometry(
    mapTextSpanToTesseractWordBoxes(index, 0, index.sourceText.length),
  );
}

function rgbaImage(width, height, alpha = 17) {
  const pixels = new Uint8Array(width * height * 4);
  for (let index = 0; index < pixels.length; index += 4) {
    pixels[index] = 11;
    pixels[index + 1] = 22;
    pixels[index + 2] = 33;
    pixels[index + 3] = alpha;
  }
  return { width, height, pixels };
}

function pixel(image, x, y) {
  const offset = (y * image.width + x) * 4;
  return [...image.pixels.slice(offset, offset + 4)];
}

test("replaces separate word boxes with fully opaque black pixels and preserves gaps", () => {
  const geometry = trustedGeometry([
    word("a", [0, 0, 1, 1]),
    word("b", [3, 0, 4, 1]),
  ], 4, 2);
  const source = rgbaImage(4, 2, 9);
  const before = new Uint8Array(source.pixels);
  const result = renderTesseractProductionMask(geometry, source);

  assert.deepEqual(pixel(result, 0, 0), [0, 0, 0, 255]);
  assert.deepEqual(pixel(result, 3, 0), [0, 0, 0, 255]);
  assert.deepEqual(pixel(result, 1, 0), [11, 22, 33, 9]);
  assert.deepEqual(pixel(result, 2, 0), [11, 22, 33, 9]);
  assert.deepEqual(source.pixels, before);
  assert.notEqual(result.pixels.buffer, source.pixels.buffer);
  assert.equal(result.opaqueReplacement, true);
  assert.equal(result.irreversibleDerivative, true);
  assert.equal(PRODUCTION_MASK_GRAYSCALE, 0);
  assert.equal(PRODUCTION_MASK_ALPHA, 255);
});

test("projects trusted geometry to a same-aspect resized RGBA derivative", () => {
  const geometry = trustedGeometry([word("a", [1, 0, 2, 1])], 4, 2);
  const result = renderTesseractProductionMask(geometry, rgbaImage(8, 4));

  for (const [x, y] of [[2, 0], [3, 0], [2, 1], [3, 1]]) {
    assert.deepEqual(pixel(result, x, y), [0, 0, 0, 255]);
  }
  assert.deepEqual(pixel(result, 1, 0), [11, 22, 33, 17]);
  assert.deepEqual(pixel(result, 4, 0), [11, 22, 33, 17]);
});

test("rejects forged geometry and aspect-ratio mismatches", () => {
  const forged = {
    startWordIndex: 0,
    endWordIndexExclusive: 1,
    wordBoxes: [{ wordIndex: 0, bbox: [0, 0, 1, 1] }],
    enclosingBbox: [0, 0, 1, 1],
  };
  assert.throws(() => renderTesseractProductionMask(forged, rgbaImage(4, 2)), /trusted builder/);

  const geometry = trustedGeometry([word("a", [0, 0, 1, 1])], 4, 2);
  assert.throws(() => renderTesseractProductionMask(geometry, rgbaImage(4, 3)), /aspect ratio/);
});

test("rejects malformed packed RGBA sources", () => {
  const geometry = trustedGeometry([word("a", [0, 0, 1, 1])], 4, 2);
  for (const source of [
    null,
    { width: 0, height: 2, pixels: new Uint8Array(0) },
    { width: 4, height: 2, pixels: [] },
    { width: 4, height: 2, pixels: new Uint8Array(31) },
  ]) {
    assert.throws(() => renderTesseractProductionMask(geometry, source), /source|width|pixels|length/);
  }
});
