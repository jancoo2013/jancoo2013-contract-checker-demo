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
};

type LineGroup = {
  tokens: LineToken[];
  text: string;
};

const CANDIDATE_PATTERNS: Array<{ type: CandidateType; pattern: RegExp }> = [
  { type: "email_like", pattern: /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi },
  { type: "phone_like", pattern: /0\d{1,2}[\s.-]?\d{3}[\s.-]?\d{4}/g },
  { type: "id_like", pattern: /(?:\d[\s.-]?){9}/g },
];

export function detectPiiCandidates(items: LocalOcrItem[]): PiiCandidate[] {
  const candidates: PiiCandidate[] = [];

  for (const line of buildLineGroups(items)) {
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
        if (type === "id_like" && countDigits(matchedText) !== 9) {
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
    .filter((item) => item.text.trim())
    .sort((a, b) => centerY(a.bbox) - centerY(b.bbox) || a.bbox.x - b.bbox.x);
  const groups: LocalOcrItem[][] = [];

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

  return groups.map((group) => buildLineText(group.sort((a, b) => a.bbox.x - b.bbox.x)));
}

function buildLineText(tokens: LocalOcrItem[]): LineGroup {
  let cursor = 0;
  const lineTokens: LineToken[] = [];
  const pieces: string[] = [];

  for (const token of tokens) {
    if (pieces.length > 0) {
      pieces.push(" ");
      cursor += 1;
    }

    const text = token.text.trim();
    const charStart = cursor;
    pieces.push(text);
    cursor += text.length;
    lineTokens.push({ ...token, charStart, charEnd: cursor });
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
