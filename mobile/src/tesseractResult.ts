import type { HebrewOcrResult, TesseractWordBox } from "../modules/tesseract-ocr";

export const MAX_TESSERACT_WORD_BOXES = 5_000;
const MAX_WORD_TEXT_CHARS = 256;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function validateWordBox(
  value: unknown,
  imageWidth: number,
  imageHeight: number,
  index: number,
): TesseractWordBox {
  if (!isRecord(value)) {
    throw new Error(`Tesseract word box ${index} is not an object.`);
  }
  if (
    typeof value.text !== "string" ||
    value.text.trim().length === 0 ||
    value.text.length > MAX_WORD_TEXT_CHARS
  ) {
    throw new Error(`Tesseract word box ${index} has invalid text.`);
  }
  if (!isFiniteNumber(value.confidence) || value.confidence < 0 || value.confidence > 100) {
    throw new Error(`Tesseract word box ${index} has invalid confidence.`);
  }
  if (
    !Array.isArray(value.bbox) ||
    value.bbox.length !== 4 ||
    !value.bbox.every(Number.isInteger)
  ) {
    throw new Error(`Tesseract word box ${index} has invalid coordinates.`);
  }

  const [left, top, right, bottom] = value.bbox as number[];
  if (
    left < 0 ||
    top < 0 ||
    right > imageWidth ||
    bottom > imageHeight ||
    left >= right ||
    top >= bottom
  ) {
    throw new Error(`Tesseract word box ${index} is outside the decoded bitmap.`);
  }

  return value as TesseractWordBox;
}

export function validateHebrewOcrResult(value: unknown): HebrewOcrResult {
  if (!isRecord(value)) {
    throw new Error("Tesseract OCR result is not an object.");
  }
  if (
    typeof value.text !== "string" ||
    !isFiniteNumber(value.elapsedMs) ||
    value.elapsedMs < 0 ||
    !isFiniteNumber(value.meanConfidence) ||
    value.meanConfidence < 0 ||
    value.meanConfidence > 100 ||
    !Number.isInteger(value.width) ||
    (value.width as number) <= 0 ||
    !Number.isInteger(value.height) ||
    (value.height as number) <= 0
  ) {
    throw new Error("Tesseract OCR result has invalid summary fields.");
  }
  if (!Array.isArray(value.wordBoxes) || value.wordBoxes.length > MAX_TESSERACT_WORD_BOXES) {
    throw new Error("Tesseract OCR result has an invalid word-box batch.");
  }

  const width = value.width as number;
  const height = value.height as number;
  value.wordBoxes.forEach((wordBox, index) => validateWordBox(wordBox, width, height, index));
  return value as HebrewOcrResult;
}
