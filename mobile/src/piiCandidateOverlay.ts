import type { HebrewOcrResult } from "../modules/tesseract-ocr/index.ts";
import {
  DEVELOPMENT_OVERLAY_OPACITY,
  buildTesseractCandidateGeometry,
  buildTesseractDevelopmentOverlay,
  buildTesseractWordTextIndex,
  mapTextSpanToTesseractWordBoxes,
  type TesseractDevelopmentOverlayRect,
} from "./piiWordBoxMapping.ts";
import {
  findDirectValueMatches,
  type DirectPiiClass,
} from "./piiDirectPatterns.ts";
import { validateHebrewOcrResult } from "./tesseractResult.ts";

export type TesseractPiiCandidateOverlayRect = TesseractDevelopmentOverlayRect & Readonly<{
  piiClass: DirectPiiClass;
  candidateIndex: number;
}>;

export type TesseractPiiCandidateOverlay = Readonly<{
  developmentOnly: true;
  inspectionOnly: "approved-direct-value-candidates";
  notMaskDecision: true;
  notCompletePiiCoverage: true;
  opacity: typeof DEVELOPMENT_OVERLAY_OPACITY;
  renderedImage: Readonly<{
    left: number;
    top: number;
    width: number;
    height: number;
  }>;
  candidateRects: readonly TesseractPiiCandidateOverlayRect[];
  summary: Readonly<{
    totalCandidates: number;
    bankIdentifier: number;
    email: number;
    phone: number;
    israeliId: number;
  }>;
}>;

function validateViewport(viewportWidth: number, viewportHeight: number): void {
  if (
    !Number.isFinite(viewportWidth) ||
    !Number.isFinite(viewportHeight) ||
    viewportWidth <= 0 ||
    viewportHeight <= 0
  ) {
    throw new Error("PII candidate overlay viewport dimensions must be finite and positive.");
  }
}

function buildRenderedImage(
  result: HebrewOcrResult,
  viewportWidth: number,
  viewportHeight: number,
): TesseractPiiCandidateOverlay["renderedImage"] {
  const scale = Math.min(viewportWidth / result.width, viewportHeight / result.height);
  const width = result.width * scale;
  const height = result.height * scale;
  return Object.freeze({
    left: (viewportWidth - width) / 2,
    top: (viewportHeight - height) / 2,
    width,
    height,
  });
}

/**
 * Build a development-only overlay for approved direct-value PII candidates.
 *
 * This does not authorize masking and does not claim complete PII coverage. The output
 * contains only class labels, projected rectangles, and counts; matched values and source
 * offsets never leave this function.
 */
export function buildTesseractPiiCandidateOverlay(
  value: unknown,
  viewportWidth: number,
  viewportHeight: number,
): TesseractPiiCandidateOverlay {
  validateViewport(viewportWidth, viewportHeight);
  const result = validateHebrewOcrResult(value);
  const renderedImage = buildRenderedImage(result, viewportWidth, viewportHeight);
  const index = buildTesseractWordTextIndex(result);
  const candidateRects: TesseractPiiCandidateOverlayRect[] = [];
  const counts: Record<DirectPiiClass, number> = {
    bank_identifier: 0,
    email: 0,
    phone: 0,
    israeli_id: 0,
  };

  for (const [candidateIndex, match] of findDirectValueMatches(index.sourceText).entries()) {
    const mapping = mapTextSpanToTesseractWordBoxes(index, match.start, match.end);
    const geometry = buildTesseractCandidateGeometry(mapping);
    const overlay = buildTesseractDevelopmentOverlay(geometry, viewportWidth, viewportHeight);

    if (
      overlay.renderedImage.left !== renderedImage.left ||
      overlay.renderedImage.top !== renderedImage.top ||
      overlay.renderedImage.width !== renderedImage.width ||
      overlay.renderedImage.height !== renderedImage.height
    ) {
      throw new Error("Trusted PII overlay disagrees with the inspection viewport.");
    }

    counts[match.piiClass] += 1;
    for (const rect of overlay.wordRects) {
      candidateRects.push(Object.freeze({
        candidateIndex,
        piiClass: match.piiClass,
        wordIndex: rect.wordIndex,
        left: rect.left,
        top: rect.top,
        width: rect.width,
        height: rect.height,
      }));
    }
  }

  return Object.freeze({
    developmentOnly: true as const,
    inspectionOnly: "approved-direct-value-candidates" as const,
    notMaskDecision: true as const,
    notCompletePiiCoverage: true as const,
    opacity: DEVELOPMENT_OVERLAY_OPACITY,
    renderedImage,
    candidateRects: Object.freeze(candidateRects),
    summary: Object.freeze({
      totalCandidates: counts.bank_identifier + counts.email + counts.phone + counts.israeli_id,
      bankIdentifier: counts.bank_identifier,
      email: counts.email,
      phone: counts.phone,
      israeliId: counts.israeli_id,
    }),
  });
}
