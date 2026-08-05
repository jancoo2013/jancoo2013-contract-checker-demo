import type { HebrewOcrResult, TesseractWordBox } from "../modules/tesseract-ocr";

export const MAX_TESSERACT_WORD_BOXES = 5_000;
export const MIN_TESSERACT_PII_MEAN_CONFIDENCE = 60;
const MAX_WORD_TEXT_CHARS = 256;
const WORD_WHITESPACE = /\s/u;

export type TesseractPiiQualityBlockReason =
  | "no_word_boxes"
  | "mean_confidence_below_threshold"
  | "ambiguous_word_boxes";

export type TesseractPiiQualityAssessment = Readonly<{
  usableForPiiMasking: boolean;
  blockingReasons: readonly TesseractPiiQualityBlockReason[];
  diagnostics: Readonly<{
    meanConfidence: number;
    minimumMeanConfidence: typeof MIN_TESSERACT_PII_MEAN_CONFIDENCE;
    wordBoxCount: number;
    ambiguousWordBoxCount: number;
  }>;
}>;

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

function validateHebrewOcrStructure(value: unknown): HebrewOcrResult {
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

function assessValidatedResult(result: HebrewOcrResult): TesseractPiiQualityAssessment {
  const ambiguousWordBoxCount = result.wordBoxes.reduce(
    (count, wordBox) => count + (WORD_WHITESPACE.test(wordBox.text) ? 1 : 0),
    0,
  );
  const blockingReasons: TesseractPiiQualityBlockReason[] = [];

  if (result.wordBoxes.length === 0) {
    blockingReasons.push("no_word_boxes");
  }
  if (result.meanConfidence < MIN_TESSERACT_PII_MEAN_CONFIDENCE) {
    blockingReasons.push("mean_confidence_below_threshold");
  }
  if (ambiguousWordBoxCount > 0) {
    blockingReasons.push("ambiguous_word_boxes");
  }

  return Object.freeze({
    usableForPiiMasking: blockingReasons.length === 0,
    blockingReasons: Object.freeze(blockingReasons),
    diagnostics: Object.freeze({
      meanConfidence: result.meanConfidence,
      minimumMeanConfidence: MIN_TESSERACT_PII_MEAN_CONFIDENCE,
      wordBoxCount: result.wordBoxes.length,
      ambiguousWordBoxCount,
    }),
  });
}

export function assessHebrewOcrForPiiMasking(value: unknown): TesseractPiiQualityAssessment {
  return assessValidatedResult(validateHebrewOcrStructure(value));
}

function qualityBlockMessage(assessment: TesseractPiiQualityAssessment): string {
  const details: string[] = [];
  const { diagnostics, blockingReasons } = assessment;

  if (blockingReasons.includes("no_word_boxes")) {
    details.push("no OCR word boxes were returned");
  }
  if (blockingReasons.includes("mean_confidence_below_threshold")) {
    details.push(
      `mean confidence ${diagnostics.meanConfidence} is below ${diagnostics.minimumMeanConfidence}`,
    );
  }
  if (blockingReasons.includes("ambiguous_word_boxes")) {
    const count = diagnostics.ambiguousWordBoxCount;
    details.push(`${count} ambiguous word box${count === 1 ? "" : "es"} contains whitespace`);
  }

  return `OCR unusable — masking blocked: ${details.join("; ")}.`;
}

/** Validate the native bridge structure without making a PII usability decision. */
export function validateHebrewOcrResult(value: unknown): HebrewOcrResult {
  return validateHebrewOcrStructure(value);
}

/**
 * Validate one runtime Tesseract result and fail closed before any PII authorization.
 *
 * Low mean confidence, an empty word batch, or whitespace-bearing word boxes prevent
 * the runtime result from reaching candidate overlay construction. Diagnostics remain
 * value-free; structurally valid synthetic fixtures may still use the structural validator.
 */
export function validateHebrewOcrForPiiMasking(value: unknown): HebrewOcrResult {
  const result = validateHebrewOcrStructure(value);
  const assessment = assessValidatedResult(result);
  if (!assessment.usableForPiiMasking) {
    throw new Error(qualityBlockMessage(assessment));
  }
  return result;
}
