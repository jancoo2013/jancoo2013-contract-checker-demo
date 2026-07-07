import type { LocalOcrItem } from "local-ocr";
import type { Box, Size } from "./overlayGeometry";

export type ProposalType = "id_field" | "phone_field" | "email_field";

export type PiiProposal = {
  type: ProposalType;
  bbox: Box;
  anchorBbox: Box;
  anchorText: string;
};

type OcrToken = LocalOcrItem & {
  sourceIndex: number;
};

type LineGroup = {
  tokens: OcrToken[];
  bbox: Box;
};

type AnchorMatch = {
  type: ProposalType;
  tokens: OcrToken[];
  bbox: Box;
  text: string;
};

const MAX_ANCHOR_WINDOW = 4;
const HORIZONTAL_GAP_PX = 4;

const ANCHORS: Record<ProposalType, string[]> = {
  id_field: [
    'ת"ז',
    "ת״ז",
    "ת.ז.",
    "תז",
    "תעודת זהות",
    "מספר זהות",
    "מס' זהות",
    "מס׳ זהות",
  ],
  phone_field: ["טלפון", "טל'", "טל׳", "נייד", "פלאפון"],
  email_field: ['דוא"ל', "דוא״ל", "דואל", "דואר אלקטרוני", "אימייל"],
};

const NORMALIZED_ANCHOR_TYPES = new Map<string, ProposalType>();

for (const [type, anchors] of Object.entries(ANCHORS) as Array<[ProposalType, string[]]>) {
  for (const anchor of anchors) {
    NORMALIZED_ANCHOR_TYPES.set(normalizeAnchorText(anchor), type);
  }
}

export function detectPiiProposals(items: LocalOcrItem[], imageSize: Size): PiiProposal[] {
  const proposals: PiiProposal[] = [];

  for (const line of buildLineGroups(items)) {
    const anchors = findAnchorMatches(line);
    proposals.push(...buildValueRegionProposals(line, anchors, imageSize));
  }

  return proposals;
}

export function countProposalsByType(proposals: PiiProposal[]): Record<ProposalType, number> {
  return proposals.reduce<Record<ProposalType, number>>(
    (counts, proposal) => {
      counts[proposal.type] += 1;
      return counts;
    },
    { id_field: 0, phone_field: 0, email_field: 0 },
  );
}

function buildLineGroups(items: LocalOcrItem[]): LineGroup[] {
  const tokens = items
    .map((item, sourceIndex) => ({ ...item, sourceIndex }))
    .filter((item) => item.text.trim())
    .sort((a, b) => centerY(a.bbox) - centerY(b.bbox) || a.bbox.x - b.bbox.x);
  const groups: OcrToken[][] = [];

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

  return groups.map((group) => ({
    tokens: group,
    bbox: unionBoxes(group.map((token) => token.bbox)),
  }));
}

function findAnchorMatches(line: LineGroup): AnchorMatch[] {
  const matches = new Map<string, AnchorMatch>();
  const sourceOrder = [...line.tokens].sort((a, b) => a.sourceIndex - b.sourceIndex);
  const visualRtlOrder = [...line.tokens].sort(
    (a, b) => b.bbox.x + b.bbox.width - (a.bbox.x + a.bbox.width),
  );

  for (const orderedTokens of [sourceOrder, visualRtlOrder]) {
    for (let start = 0; start < orderedTokens.length; start += 1) {
      for (
        let size = 1;
        size <= MAX_ANCHOR_WINDOW && start + size <= orderedTokens.length;
        size += 1
      ) {
        const tokens = orderedTokens.slice(start, start + size);
        const normalized = normalizeAnchorText(tokens.map((token) => token.text).join(" "));
        const type = NORMALIZED_ANCHOR_TYPES.get(normalized);

        if (!type) {
          continue;
        }

        const key = `${type}:${tokens
          .map((token) => token.sourceIndex)
          .sort((a, b) => a - b)
          .join(",")}`;

        if (!matches.has(key)) {
          matches.set(key, {
            type,
            tokens,
            bbox: unionBoxes(tokens.map((token) => token.bbox)),
            text: tokens.map((token) => token.text.trim()).join(" "),
          });
        }
      }
    }
  }

  return Array.from(matches.values());
}

function buildValueRegionProposals(
  line: LineGroup,
  anchors: AnchorMatch[],
  imageSize: Size,
): PiiProposal[] {
  const sortedAnchors = [...anchors].sort(
    (a, b) => b.bbox.x + b.bbox.width - (a.bbox.x + a.bbox.width),
  );
  const proposals: PiiProposal[] = [];

  for (let index = 0; index < sortedAnchors.length; index += 1) {
    const anchor = sortedAnchors[index];
    const nextAnchorOnLeft = sortedAnchors[index + 1];
    const left = clamp(
      nextAnchorOnLeft ? nextAnchorOnLeft.bbox.x + nextAnchorOnLeft.bbox.width + HORIZONTAL_GAP_PX : 0,
      0,
      imageSize.width,
    );
    const right = clamp(anchor.bbox.x - HORIZONTAL_GAP_PX, 0, imageSize.width);

    if (right <= left) {
      continue;
    }

    const verticalPadding = Math.min(12, Math.max(4, Math.round(line.bbox.height * 0.25)));
    const top = clamp(line.bbox.y - verticalPadding, 0, imageSize.height);
    const bottom = clamp(line.bbox.y + line.bbox.height + verticalPadding, 0, imageSize.height);

    proposals.push({
      type: anchor.type,
      bbox: {
        x: left,
        y: top,
        width: right - left,
        height: Math.max(0, bottom - top),
      },
      anchorBbox: anchor.bbox,
      anchorText: anchor.text,
    });
  }

  return proposals;
}

function normalizeAnchorText(value: string): string {
  return value
    .normalize("NFKC")
    .replace(/[״׳"'\u2018\u2019\u201c\u201d`´]/g, '"')
    .replace(/\s*"\s*/g, '"')
    .replace(/\s*\.\s*/g, ".")
    .replace(/\./g, "")
    .replace(/^[\s:：;,]+|[\s:：;,]+$/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function centerY(box: Box): number {
  return box.y + box.height / 2;
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

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
