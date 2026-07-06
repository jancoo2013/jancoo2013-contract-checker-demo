import type { LocalOcrItem } from "local-ocr";
import type { Box } from "./overlayGeometry";

export type CandidateType = "id_like" | "phone_like" | "email_like";

export type PiiCandidate = {
  type: CandidateType;
  text: string;
  bbox: Box;
};

type LineToken = LocalOcrItem & {
  charStart: number;
  charEnd: number;
  sourceIndex: number;
};

type LineGroup = {
  tokens: LineToken[];
  text: string;
};

type TextSpan = {
  start: number;
  end: number;
};

const CANDIDATE_PATTERNS: Array<{ type: CandidateType; pattern: RegExp }> = [
  { type: "email_like", pattern: /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi },
  { type: "phone_like", pattern: /0\d{1,2}[\s.-]?\d{3}[\s.-]?\d{4}/g },
  { type: "id_like", pattern: /(?:\d[\s.-]?){9}/g },
];

export function detectPiiCandidates(items: LocalOcrItem[]): PiiCandidate[] {
  const candidates: PiiCandidate[] = [];

  for (const line of buildLineGroups(items)) {
    const phoneSpans = findMatchSpans(line.text, getPattern("phone_like"));

    for (const { type, pattern } of CANDIDATE_PATTERNS) {
      pattern.lastIndex = 0;

      for (const match of line.text.matchAll(pattern)) {
        const start = match.index ?? 0;
        const end = start + match[0].length;
        const tokens = line.tokens.filter(
          (token) => token.charStart < end && token.charEnd > start,
        );

        if (tokens.length === 0) {
          continue;
        }

        const matchedText = match[0].trim();
        if (
          type === "id_like" &&
          (countDigits(matchedText) !== 9 ||
            overlapsAnySpan(start, end, phoneSpans) ||
            hasExtraDigitInsideBoundaryToken(tokens, start, end))
        ) {
          continue;
        }

        candidates.push({
          type,
          text: matchedText,
          bbox: unionBoxes(tokens.map((token) => token.bbox)),
        });
      }
    }
  }

  return candidates;
}

export function countCandidatesByType(candidates: PiiCandidate[]): Record<CandidateType, number> {
  return candidates.reduce<Record<CandidateType, number>>(
    (counts, candidate) => {
      counts[candidate.type] += 1;
      return counts;
    },
    { id_like: 0, phone_like: 0, email_like: 0 },
  );
}

function buildLineGroups(items: LocalOcrItem[]): LineGroup[] {
  const tokens = items
    .map((item, sourceIndex) => ({ ...item, sourceIndex }))
    .filter((item) => item.text.trim())
    .sort((a, b) => centerY(a.bbox) - centerY(b.bbox) || a.bbox.x - b.bbox.x);
  const groups: Array<Array<LocalOcrItem & { sourceIndex: number }>> = [];

  for (const token of tokens) {
    const tokenCenter = centerY(token.bbox);
    const matchedGroup = groups.find((group) => {
      const averageHeight =
        group.reduce((sum, item) => sum + item.bbox.height, 0) / Math.max(group.length, 1);
      const groupCenter =
        group.reduce((sum, item) => sum + centerY(item.bbox), 0) / Math.max(group.length, 1);
      return Math.abs(tokenCenter - groupCenter) <= Math.max(12, averageHeight * 0.75);
    });

    if (matchedGroup) {
      matchedGroup.push(token);
    } else {
      groups.push([token]);
    }
  }

  return groups.map((group) => buildLineText(group.sort((a, b) => a.sourceIndex - b.sourceIndex)));
}

function buildLineText(tokens: Array<LocalOcrItem & { sourceIndex: number }>): LineGroup {
  let cursor = 0;
  const lineTokens: LineToken[] = [];
  const pieces: string[] = [];
  let previousText = "";

  for (const token of tokens) {
    const text = token.text.trim();
    const separator = pieces.length > 0 && needsSeparator(previousText, text) ? " " : "";
    if (separator) {
      pieces.push(separator);
      cursor += separator.length;
    }

    const charStart = cursor;
    pieces.push(text);
    cursor += text.length;
    lineTokens.push({ ...token, charStart, charEnd: cursor, sourceIndex: token.sourceIndex });
    previousText = text;
  }

  return {
    tokens: lineTokens,
    text: pieces.join(""),
  };
}

function centerY(box: Box): number {
  return box.y + box.height / 2;
}

function countDigits(value: string): number {
  return (value.match(/\d/g) ?? []).length;
}

function getPattern(type: CandidateType): RegExp {
  const pattern = CANDIDATE_PATTERNS.find((candidate) => candidate.type === type)?.pattern;
  if (!pattern) {
    throw new Error(`Missing candidate pattern: ${type}`);
  }
  return pattern;
}

function findMatchSpans(text: string, pattern: RegExp): TextSpan[] {
  pattern.lastIndex = 0;
  return Array.from(text.matchAll(pattern), (match) => {
    const start = match.index ?? 0;
    return { start, end: start + match[0].length };
  });
}

function overlapsAnySpan(start: number, end: number, spans: TextSpan[]): boolean {
  return spans.some((span) => start < span.end && end > span.start);
}

function hasExtraDigitInsideBoundaryToken(
  tokens: LineToken[],
  start: number,
  end: number,
): boolean {
  return tokens.some((token) => {
    const text = token.text.trim();
    const overlapStart = Math.max(start, token.charStart) - token.charStart;
    const overlapEnd = Math.min(end, token.charEnd) - token.charStart;
    const before = text.slice(0, Math.max(0, overlapStart));
    const after = text.slice(Math.max(0, overlapEnd));
    return /\d/.test(before) || /\d/.test(after);
  });
}

function needsSeparator(previousText: string, currentText: string): boolean {
  return !isJoinerToken(previousText) && !isJoinerToken(currentText);
}

function isJoinerToken(value: string): boolean {
  return /^[.@-]$/.test(value);
}

function unionBoxes(boxes: Box[]): Box {
  const left = Math.min(...boxes.map((box) => box.x));
  const top = Math.min(...boxes.map((box) => box.y));
  const right = Math.max(...boxes.map((box) => box.x + box.width));
  const bottom = Math.max(...boxes.map((box) => box.y + box.height));

  return {
    x: left,
    y: top,
    width: right - left,
    height: bottom - top,
  };
}
