import type {
  DirectPiiClass,
  DirectPiiWordBoxMatch,
  HebrewOcrResult,
  TesseractWordBox,
} from "../modules/tesseract-ocr";

const EMAIL_RE = /^[A-Z0-9](?:[A-Z0-9._%+-]{0,62}[A-Z0-9])?@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,63}$/i;
const PHONE_RE = /^(?:\+972[ -]?|0)(?:5\d|[23489]|7[0-9])[ -]?\d{3}[ -]?\d{4}$/;
const ISRAELI_ID_RE = /^\d(?:[ -]?\d){8}$/;
const ISRAELI_IBAN_RE = /^IL(?:[ -]?\d){21}$/i;
const SEPARATORS_RE = /[ -]/g;

const DETECTOR_IDS: Record<DirectPiiClass, string> = {
  bank_identifier: "direct-israeli-iban-v0",
  email: "direct-email-v0",
  phone: "direct-israeli-phone-v0",
  israeli_id: "direct-israeli-id-v0",
};

function withoutSeparators(value: string): string {
  return value.replace(SEPARATORS_RE, "");
}

function validEmail(value: string): boolean {
  if (!EMAIL_RE.test(value)) {
    return false;
  }
  const localPart = value.split("@", 1)[0];
  return !localPart.includes("..") && !localPart.startsWith(".") && !localPart.endsWith(".");
}

function validIsraeliId(value: string): boolean {
  const digits = withoutSeparators(value);
  if (!/^\d{9}$/.test(digits) || digits === "000000000") {
    return false;
  }

  let total = 0;
  for (let index = 0; index < digits.length; index += 1) {
    const product = Number(digits[index]) * (index % 2 === 0 ? 1 : 2);
    total += product < 10 ? product : product - 9;
  }
  return total % 10 === 0;
}

function validIsraeliIban(value: string): boolean {
  const normalized = withoutSeparators(value).toUpperCase();
  if (!/^IL\d{21}$/.test(normalized)) {
    return false;
  }

  const rearranged = normalized.slice(4) + normalized.slice(0, 4);
  let remainder = 0;
  for (const character of rearranged) {
    const digits = /[A-Z]/.test(character)
      ? String(character.charCodeAt(0) - "A".charCodeAt(0) + 10)
      : character;
    for (const digit of digits) {
      remainder = (remainder * 10 + Number(digit)) % 97;
    }
  }
  return remainder === 1;
}

function classifyExactWord(text: string): DirectPiiClass | undefined {
  if (ISRAELI_IBAN_RE.test(text) && validIsraeliIban(text)) {
    return "bank_identifier";
  }
  if (validEmail(text)) {
    return "email";
  }
  if (PHONE_RE.test(text)) {
    return "phone";
  }
  if (ISRAELI_ID_RE.test(text) && validIsraeliId(text)) {
    return "israeli_id";
  }
  return undefined;
}

function mapDirectPiiWordBoxes(
  wordBoxes: readonly TesseractWordBox[],
): DirectPiiWordBoxMatch[] {
  const matches: DirectPiiWordBoxMatch[] = [];

  wordBoxes.forEach((wordBox, wordIndex) => {
    const piiClass = classifyExactWord(wordBox.text);
    if (!piiClass) {
      return;
    }

    const detectorId = DETECTOR_IDS[piiClass];
    matches.push({
      matchId: `direct-word-${wordIndex}-${detectorId}`,
      piiClass,
      detectorId,
      wordIndex,
      confidence: wordBox.confidence,
      bbox: [...wordBox.bbox] as [number, number, number, number],
    });
  });

  return matches;
}

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
  const wordBoxes = value.wordBoxes.map((wordBox, index) =>
    validateWordBox(wordBox, width, height, index),
  );
  return {
    ...(value as HebrewOcrResult),
    wordBoxes,
    directPiiWordBoxes: mapDirectPiiWordBoxes(wordBoxes),
  };
}
