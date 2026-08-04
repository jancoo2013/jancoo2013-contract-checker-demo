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

function copyBbox(
  bbox: readonly [number, number, number, number],
): readonly [number, number, number, number] {
  return Object.freeze([bbox[0], bbox[1], bbox[2], bbox[3]]);
}

/**
 * Build the exact local text surface that a mobile direct-value finder must use.
 *
 * Word order comes from Tesseract's iterator, never from x coordinates. A single
 * ASCII space is inserted between words. The returned word records intentionally
 * omit OCR text; only `sourceText` contains the request-local text surface.
 */
export function buildTesseractWordTextIndex(value: unknown): TesseractWordTextIndex {
  const result: HebrewOcrResult = validateHebrewOcrResult(value);
  const sourceParts: string[] = [];
  const words: IndexedTesseractWord[] = [];
  let offset = 0;

  result.wordBoxes.forEach((wordBox, wordIndex) => {
    if (WORD_WHITESPACE.test(wordBox.text)) {
      throw new Error(`Tesseract word box ${wordIndex} contains whitespace.`);
    }
    if (wordIndex > 0) {
      sourceParts.push(" ");
      offset += 1;
    }

    const start = offset;
    sourceParts.push(wordBox.text);
    offset += wordBox.text.length;
    words.push(
      Object.freeze({
        wordIndex,
        start,
        end: offset,
        confidence: wordBox.confidence,
        bbox: copyBbox(wordBox.bbox),
      }),
    );
  });

  const index = Object.freeze({
    sourceText: sourceParts.join(""),
    words: Object.freeze(words),
  });
  trustedIndexes.add(index);
  return index;
}

/**
 * Resolve one non-empty span from the canonical word text to its exact OCR boxes.
 *
 * The span may begin or end inside a word (for example, punctuation can share a
 * Tesseract box with a value). Output is value-free and boxes are not combined;
 * candidate geometry aggregation belongs to a later layer.
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
  if (index.sourceText[start] === " " || index.sourceText[end - 1] === " ") {
    throw new Error("Text span must begin and end inside a Tesseract word.");
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
