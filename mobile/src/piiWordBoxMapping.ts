import type { HebrewOcrResult } from "../modules/tesseract-ocr";
import { validateHebrewOcrResult } from "./tesseractResult.ts";

export const MAX_MAPPED_WORD_BOXES = 64;

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

const trustedIndexes = new WeakSet<object>();
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
  trustedIndexes.add(index);
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

  return Object.freeze({
    startWordIndex: firstWord.wordIndex,
    endWordIndexExclusive: lastWord.wordIndex + 1,
    wordBoxes: Object.freeze(mappedWordBoxes),
  });
}
