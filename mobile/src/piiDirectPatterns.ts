export type DirectPiiClass = "bank_identifier" | "email" | "phone" | "israeli_id";

export type DirectValueMatch = Readonly<{
  piiClass: DirectPiiClass;
  start: number;
  end: number;
  detectorId: string;
}>;

const EMAIL_PATTERN = /(?<![A-Z0-9._%+-])[A-Z0-9](?:[A-Z0-9._%+-]{0,62}[A-Z0-9])?@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,63}(?![A-Z0-9-])/giu;
const PHONE_PATTERN = /(?<!\d)(?:\+972[ -]?|0)(?:5\d|[23489]|7[0-9])[ -]?\d{3}[ -]?\d{4}(?!\d)/gu;
const ISRAELI_ID_PATTERN = /(?<!\d)\d(?:[ -]?\d){8}(?!\d)/gu;
const ISRAELI_IBAN_PATTERN = /(?<![A-Z0-9])IL(?:[ -]?\d){21}(?![A-Z0-9@])/giu;
const SEPARATORS = new Set([" ", "-"]);
const PRIORITY: readonly DirectPiiClass[] = ["bank_identifier", "email", "phone", "israeli_id"];

const DETECTOR_IDS: Readonly<Record<DirectPiiClass, string>> = Object.freeze({
  bank_identifier: "direct-israeli-iban-v0",
  email: "direct-email-v0",
  phone: "direct-israeli-phone-v0",
  israeli_id: "direct-israeli-id-v0",
});

function withoutSeparators(value: string): string {
  let normalized = "";
  for (const character of value) {
    if (!SEPARATORS.has(character)) {
      normalized += character;
    }
  }
  return normalized;
}

function validEmail(value: string): boolean {
  const localPart = value.split("@", 1)[0] ?? "";
  return !localPart.includes("..") && !localPart.startsWith(".") && !localPart.endsWith(".");
}

function validIsraeliId(value: string): boolean {
  const digits = withoutSeparators(value);
  if (!/^\d{9}$/u.test(digits) || digits === "000000000") {
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
  if (!/^IL\d{21}$/u.test(normalized)) {
    return false;
  }

  const rearranged = normalized.slice(4) + normalized.slice(0, 4);
  let remainder = 0;
  for (const character of rearranged) {
    const digits = /[A-Z]/u.test(character)
      ? String(character.charCodeAt(0) - "A".charCodeAt(0) + 10)
      : character;
    for (const digit of digits) {
      remainder = (remainder * 10 + Number(digit)) % 97;
    }
  }
  return remainder === 1;
}

function isPartialSeparatedNumber(text: string, start: number, end: number): boolean {
  const before = start >= 2 && SEPARATORS.has(text[start - 1] ?? "") && /\d/u.test(text[start - 2] ?? "");
  const after = end + 1 < text.length && SEPARATORS.has(text[end] ?? "") && /\d/u.test(text[end + 1] ?? "");
  return before || after;
}

function collectMatches(
  text: string,
  piiClass: DirectPiiClass,
  pattern: RegExp,
  validator: (value: string) => boolean,
): DirectValueMatch[] {
  const matches: DirectValueMatch[] = [];
  for (const found of text.matchAll(pattern)) {
    const value = found[0];
    const start = found.index;
    if (typeof value !== "string" || typeof start !== "number") {
      continue;
    }
    const end = start + value.length;
    if (piiClass !== "email" && isPartialSeparatedNumber(text, start, end)) {
      continue;
    }
    if (!validator(value)) {
      continue;
    }
    matches.push(Object.freeze({
      piiClass,
      start,
      end,
      detectorId: DETECTOR_IDS[piiClass],
    }));
  }
  return matches;
}

function overlaps(left: DirectValueMatch, right: DirectValueMatch): boolean {
  return left.start < right.end && right.start < left.end;
}

/**
 * Android parity port of the approved Python direct-value finder.
 * Returns high-confidence, non-overlapping, value-free span references only.
 */
export function findDirectValueMatches(text: string): readonly DirectValueMatch[] {
  if (typeof text !== "string") {
    throw new TypeError("text must be a string");
  }
  if (!text) {
    return Object.freeze([]);
  }

  const byClass: Readonly<Record<DirectPiiClass, DirectValueMatch[]>> = {
    bank_identifier: collectMatches(text, "bank_identifier", ISRAELI_IBAN_PATTERN, validIsraeliIban),
    email: collectMatches(text, "email", EMAIL_PATTERN, validEmail),
    phone: collectMatches(text, "phone", PHONE_PATTERN, () => true),
    israeli_id: collectMatches(text, "israeli_id", ISRAELI_ID_PATTERN, validIsraeliId),
  };

  const accepted: DirectValueMatch[] = [];
  for (const piiClass of PRIORITY) {
    const candidates = [...byClass[piiClass]].sort(
      (left, right) => left.start - right.start || left.end - right.end || left.detectorId.localeCompare(right.detectorId),
    );
    for (const match of candidates) {
      if (!accepted.some((existing) => overlaps(match, existing))) {
        accepted.push(match);
      }
    }
  }

  accepted.sort(
    (left, right) => left.start - right.start || left.end - right.end || left.detectorId.localeCompare(right.detectorId),
  );
  return Object.freeze(accepted);
}
