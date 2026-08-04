import type { HebrewOcrResult } from "../modules/tesseract-ocr";
import { validateHebrewOcrResult } from "./tesseractResult.ts";

export const MAX_MAPPED_WORD_BOXES = 64;
export const MAX_WORD_GAP_HEIGHT_MULTIPLIER = 2;

type ImageSize = Readonly<{
  width: number;
  height: number;
}>;

export type IndexedTesseractWord = Readonly<{
  wordIndex: number;
  start: number;
  end: number;
  confidence: number;
  bbox: readonly [number, number, number, number];
}>;

export type TesseractWordTextIndex = Readonly<{
  sourceText: string;
  words: readonly IndexedTesseractWord[];
}>;

export type MappedTesseractWordBox = Readonly<{
  wordIndex: number;
  confidence: number;
  bbox: readonly [number, number, number, number];
}>;

export type TesseractWordSpanMapping = Readonly<{
  startWordIndex: number;
  endWordIndexExclusive: number;
  wordBoxes: readonly MappedTesseractWordBox[];
}>;

export type TesseractCandidateWordBox = Readonly<{
  wordIndex: number;
  bbox: readonly [number, number, number, number];
}>;

export type TesseractCandidateGeometry = Readonly<{
  startWordIndex: number;
  endWordIndexExclusive: number;
  wordBoxes: readonly TesseractCandidateWordBox[];
  enclosingBbox: readonly [number, number, number, number];
}>;

const trustedIndexes = new WeakSet<object>();
const indexImageSizes = new WeakMap<object, ImageSize>();
const trustedMappings = new WeakSet<object>();
const mappingImageSizes = new WeakMap<object, ImageSize>();
const WORD_WHITESPACE = /\s/u;
const ONLY_WHITESPACE = /^\s*$/u;

function copyBbox(
  bbox: readonly [number, number, number, number],
): readonly [number, number, number, number] {
  return Object.freeze([bbox[0], bbox[1], bbox[2], bbox[3]]);
}

function containsNonAsciiSpaceWhitespace(value: string): boolean {
  for (const character of value) {
    if (character !== " " && WORD_WHITESPACE.test(character)) {
      return true;
    }
  }
  return false;
}

function assertBoxInsideImage(
  bbox: readonly [number, number, number, number],
  imageSize: ImageSize,
): void {
  const [left, top, right, bottom] = bbox;
  if (
    !bbox.every(Number.isInteger) ||
    left < 0 ||
    top < 0 ||
    right > imageSize.width ||
    bottom > imageSize.height ||
    left >= right ||
    top >= bottom
  ) {
    throw new Error("MappedTesseract word box is outside the source image.");
  }
}

/**
 * Index exact Tesseract full-text offsets for the validated iterator words.
 *
 * The original text is preserved, including line boundaries. Every non-whitespace
 * character must belong to the next iterator word; otherwise indexing fails closed.
 * Word records intentionally omit OCR text and retain only request-local offsets.
 */
export function buildTesseractWordTextIndex(value: unknown): TesseractWordTextIndex {
  const result: HebrewOcrResult = validateHebrewOcrResult(value);
  const words: IndexedTesseractWord[] = [];
  let cursor = 0;

  result.wordBoxes.forEach((wordBox, wordIndex) => {
    if (WORD_WHITESPACE.test(wordBox.text)) {
      throw new Error(`Tesseract word box ${wordIndex} contains whitespace.`);
    }

    const start = result.text.indexOf(wordBox.text, cursor);
    if (start < 0 || !ONLY_WHITESPACE.test(result.text.slice(cursor, start))) {
      throw new Error(`Tesseract word box ${wordIndex} is inconsistent with full OCR text.`);
    }
    const end = start + wordBox.text.length;
    words.push(
      Object.freeze({
        wordIndex,
        start,
        end,
        confidence: wordBox.confidence,
        bbox: copyBbox(wordBox.bbox),
      }),
    );
    cursor = end;
  });

  if (!ONLY_WHITESPACE.test(result.text.slice(cursor))) {
    throw new Error("Tesseract full OCR text contains unboxed non-whitespace content.");
  }

  const index = Object.freeze({
    sourceText: result.text,
    words: Object.freeze(words),
  });
  const imageSize = Object.freeze({ width: result.width, height: result.height });
  trustedIndexes.add(index);
  indexImageSizes.set(index, imageSize);
  return index;
}

/**
 * Resolve one non-empty direct-value span to its exact OCR word boxes.
 *
 * The span may begin or end inside a word when punctuation shares its box. It may
 * contain ASCII spaces between value words, but it cannot cross a Tesseract line
 * boundary or other non-ASCII whitespace. Output remains value-free and boxes are
 * not combined; candidate geometry aggregation belongs to a later layer.
 */
export function mapTextSpanToTesseractWordBoxes(
  index: TesseractWordTextIndex,
  start: number,
  end: number,
): TesseractWordSpanMapping {
  if (typeof index !== "object" || index === null || !trustedIndexes.has(index)) {
    throw new Error("Tesseract word text index was not produced by the trusted builder.");
  }
  if (!Number.isInteger(start) || !Number.isInteger(end)) {
    throw new Error("Text span offsets must be integers.");
  }
  if (start < 0 || start >= end || end > index.sourceText.length) {
    throw new Error("Text span is outside the canonical Tesseract word text.");
  }
  if (
    WORD_WHITESPACE.test(index.sourceText[start]) ||
    WORD_WHITESPACE.test(index.sourceText[end - 1])
  ) {
    throw new Error("Text span must begin and end inside a Tesseract word.");
  }
  if (containsNonAsciiSpaceWhitespace(index.sourceText.slice(start, end))) {
    throw new Error("Text span crosses a Tesseract line boundary or unsupported whitespace.");
  }

  const overlappingWords = index.words.filter((word) => word.end > start && word.start < end);
  if (overlappingWords.length === 0) {
    throw new Error("Text span does not overlap a Tesseract word.");
  }
  if (overlappingWords.length > MAX_MAPPED_WORD_BOXES) {
    throw new Error("Text span overlaps too many Tesseract word boxes.");
  }

  const mappedWordBoxes = overlappingWords.map((word) =>
    Object.freeze({
      wordIndex: word.wordIndex,
      confidence: word.confidence,
      bbox: copyBbox(word.bbox),
    }),
  );
  const firstWord = overlappingWords[0];
  const lastWord = overlappingWords[overlappingWords.length - 1];
  const mapping = Object.freeze({
    startWordIndex: firstWord.wordIndex,
    endWordIndexExclusive: lastWord.wordIndex + 1,
    wordBoxes: Object.freeze(mappedWordBoxes),
  });
  const imageSize = indexImageSizes.get(index);
  if (imageSize === undefined) {
    throw new Error("Trusted Tesseract index is missing source image metadata.");
  }
  trustedMappings.add(mapping);
  mappingImageSizes.set(mapping, imageSize);
  return mapping;
}

/**
 * Convert one trusted same-line word-span mapping into value-free candidate geometry.
 *
 * Exact word boxes remain separate. The enclosing box is diagnostic only and must
 * not be treated as the production mask when it would cover gaps between words.
 */
export function buildTesseractCandidateGeometry(
  mapping: TesseractWordSpanMapping,
): TesseractCandidateGeometry {
  if (typeof mapping !== "object" || mapping === null || !trustedMappings.has(mapping)) {
    throw new Error("Tesseract word-span mapping was not produced by the trusted mapper.");
  }

  const imageSize = mappingImageSizes.get(mapping);
  if (imageSize === undefined) {
    throw new Error("Trusted Tesseract mapping is missing source image metadata.");
  }
  if (
    mapping.wordBoxes.length === 0 ||
    mapping.endWordIndexExclusive - mapping.startWordIndex !== mapping.wordBoxes.length
  ) {
    throw new Error("Tesseract word-span mapping has inconsistent word indexes.");
  }

  let commonTop = Number.NEGATIVE_INFINITY;
  let commonBottom = Number.POSITIVE_INFINITY;
  let enclosingLeft = Number.POSITIVE_INFINITY;
  let enclosingTop = Number.POSITIVE_INFINITY;
  let enclosingRight = Number.NEGATIVE_INFINITY;
  let enclosingBottom = Number.NEGATIVE_INFINITY;

  mapping.wordBoxes.forEach((wordBox, offset) => {
    if (wordBox.wordIndex !== mapping.startWordIndex + offset) {
      throw new Error("Tesseract candidate word indexes are duplicated or non-consecutive.");
    }
    assertBoxInsideImage(wordBox.bbox, imageSize);
    const [left, top, right, bottom] = wordBox.bbox;
    commonTop = Math.max(commonTop, top);
    commonBottom = Math.min(commonBottom, bottom);
    enclosingLeft = Math.min(enclosingLeft, left);
    enclosingTop = Math.min(enclosingTop, top);
    enclosingRight = Math.max(enclosingRight, right);
    enclosingBottom = Math.max(enclosingBottom, bottom);
  });

  if (commonTop >= commonBottom) {
    throw new Error("Mapped Tesseract word boxes do not share one text-line band.");
  }

  const physicalOrder = [...mapping.wordBoxes].sort(
    (first, second) => first.bbox[0] - second.bbox[0] || first.bbox[2] - second.bbox[2],
  );
  for (let index = 1; index < physicalOrder.length; index += 1) {
    const previous = physicalOrder[index - 1].bbox;
    const current = physicalOrder[index].bbox;
    const gap = current[0] - previous[2];
    const maxHeight = Math.max(previous[3] - previous[1], current[3] - current[1]);
    if (gap > maxHeight * MAX_WORD_GAP_HEIGHT_MULTIPLIER) {
      throw new Error("Mapped Tesseract word boxes are separated by an unsafe horizontal gap.");
    }
  }

  const wordBoxes = mapping.wordBoxes.map((wordBox) =>
    Object.freeze({
      wordIndex: wordBox.wordIndex,
      bbox: copyBbox(wordBox.bbox),
    }),
  );

  const enclosingBbox: readonly [number, number, number, number] = copyBbox([
    enclosingLeft,
    enclosingTop,
    enclosingRight,
    enclosingBottom,
  ]);
  return Object.freeze({
    startWordIndex: mapping.startWordIndex,
    endWordIndexExclusive: mapping.endWordIndexExclusive,
    wordBoxes: Object.freeze(wordBoxes),
    enclosingBbox,
  });
}
