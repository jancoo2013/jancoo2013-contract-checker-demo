import type { HebrewOcrResult } from "../modules/tesseract-ocr/index.ts";
import {
  DEVELOPMENT_OVERLAY_OPACITY,
  buildTesseractCandidateGeometry,
  buildTesseractDevelopmentOverlay,
  buildTesseractWordTextIndex,
  mapTextSpanToTesseractWordBoxes,
  type TesseractDevelopmentOverlayRect,
} from "./piiWordBoxMapping.ts";
import { validateHebrewOcrResult } from "./tesseractResult.ts";

export type TesseractDevelopmentInspectionOverlay = Readonly<{
  developmentOnly: true;
  inspectionOnly: "all-ocr-word-boxes";
  notPiiDecision: true;
  opacity: typeof DEVELOPMENT_OVERLAY_OPACITY;
  renderedImage: Readonly<{
    left: number;
    top: number;
    width: number;
    height: number;
  }>;
  wordRects: readonly TesseractDevelopmentOverlayRect[];
}>;

function validateViewport(viewportWidth: number, viewportHeight: number): void {
  if (
    !Number.isFinite(viewportWidth) ||
    !Number.isFinite(viewportHeight) ||
    viewportWidth <= 0 ||
    viewportHeight <= 0
  ) {
    throw new Error("Development inspection viewport dimensions must be finite and positive.");
  }
}

function buildRenderedImage(
  result: HebrewOcrResult,
  viewportWidth: number,
  viewportHeight: number,
): TesseractDevelopmentInspectionOverlay["renderedImage"] {
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
 * Build a development-only overlay for every validated Tesseract word box.
 *
 * This is intentionally not a PII decision. Each word is routed independently through
 * the trusted text-index -> span mapping -> candidate geometry -> overlay path so the
 * Android screen can visually verify coordinate alignment on a real local image.
 */
export function buildTesseractDevelopmentInspectionOverlay(
  value: unknown,
  viewportWidth: number,
  viewportHeight: number,
): TesseractDevelopmentInspectionOverlay {
  validateViewport(viewportWidth, viewportHeight);
  const result = validateHebrewOcrResult(value);
  const index = buildTesseractWordTextIndex(result);
  const renderedImage = buildRenderedImage(result, viewportWidth, viewportHeight);
  const wordRects: TesseractDevelopmentOverlayRect[] = [];

  for (const word of index.words) {
    const mapping = mapTextSpanToTesseractWordBoxes(index, word.start, word.end);
    const geometry = buildTesseractCandidateGeometry(mapping);
    const overlay = buildTesseractDevelopmentOverlay(geometry, viewportWidth, viewportHeight);

    if (
      overlay.renderedImage.left !== renderedImage.left ||
      overlay.renderedImage.top !== renderedImage.top ||
      overlay.renderedImage.width !== renderedImage.width ||
      overlay.renderedImage.height !== renderedImage.height
    ) {
      throw new Error("Trusted development overlay disagrees with the inspection viewport.");
    }

    wordRects.push(...overlay.wordRects);
  }

  return Object.freeze({
    developmentOnly: true as const,
    inspectionOnly: "all-ocr-word-boxes" as const,
    notPiiDecision: true as const,
    opacity: DEVELOPMENT_OVERLAY_OPACITY,
    renderedImage,
    wordRects: Object.freeze(wordRects),
  });
}
