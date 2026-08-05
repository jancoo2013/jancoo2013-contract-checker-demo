import {
  buildTesseractDevelopmentOverlay,
  type TesseractCandidateGeometry,
} from "./piiWordBoxMapping.ts";

export const PRODUCTION_MASK_GRAYSCALE = 0;
export const PRODUCTION_MASK_ALPHA = 255;
export const RGBA_BYTES_PER_PIXEL = 4;

const DIMENSION_EPSILON = 1e-9;

type RgbaBytes = Uint8Array | Uint8ClampedArray;

export type PackedRgbaImage = Readonly<{
  width: number;
  height: number;
  pixels: RgbaBytes;
}>;

export type TesseractProductionMaskedImage = Readonly<{
  width: number;
  height: number;
  format: "rgba8888";
  opaqueReplacement: true;
  irreversibleDerivative: true;
  pixels: Uint8Array;
}>;

function isRgbaBytes(value: unknown): value is RgbaBytes {
  return value instanceof Uint8Array || value instanceof Uint8ClampedArray;
}

function assertPositiveSafeInteger(value: unknown, label: string): asserts value is number {
  if (!Number.isSafeInteger(value) || (value as number) <= 0) {
    throw new Error(`${label} must be a positive safe integer.`);
  }
}

function nearlyEqual(first: number, second: number): boolean {
  return Math.abs(first - second) <= DIMENSION_EPSILON;
}

/**
 * Create a new packed RGBA derivative with every trusted candidate word box replaced
 * by fixed black, fully opaque pixels. The source buffer is never mutated or returned.
 *
 * This is a pixel operation only. It does not discover PII or authorize a disposition.
 */
export function renderTesseractProductionMask(
  geometry: TesseractCandidateGeometry,
  source: PackedRgbaImage,
): TesseractProductionMaskedImage {
  if (typeof source !== "object" || source === null) {
    throw new Error("Production mask source image must be an object.");
  }
  assertPositiveSafeInteger(source.width, "Production mask source width");
  assertPositiveSafeInteger(source.height, "Production mask source height");
  if (!isRgbaBytes(source.pixels)) {
    throw new Error("Production mask source pixels must be packed 8-bit RGBA bytes.");
  }

  const expectedByteLength = source.width * source.height * RGBA_BYTES_PER_PIXEL;
  if (!Number.isSafeInteger(expectedByteLength) || source.pixels.byteLength !== expectedByteLength) {
    throw new Error("Production mask source pixel length does not match its dimensions.");
  }

  const overlay = buildTesseractDevelopmentOverlay(geometry, source.width, source.height);
  if (
    !nearlyEqual(overlay.renderedImage.left, 0) ||
    !nearlyEqual(overlay.renderedImage.top, 0) ||
    !nearlyEqual(overlay.renderedImage.width, source.width) ||
    !nearlyEqual(overlay.renderedImage.height, source.height)
  ) {
    throw new Error("Production mask source aspect ratio does not match candidate geometry.");
  }

  const pixels = new Uint8Array(source.pixels);
  for (const rect of overlay.wordRects) {
    const left = Math.max(0, Math.floor(rect.left));
    const top = Math.max(0, Math.floor(rect.top));
    const right = Math.min(source.width, Math.ceil(rect.left + rect.width));
    const bottom = Math.min(source.height, Math.ceil(rect.top + rect.height));
    if (left >= right || top >= bottom) {
      throw new Error("Production mask contains an empty projected word rectangle.");
    }

    for (let y = top; y < bottom; y += 1) {
      for (let x = left; x < right; x += 1) {
        const offset = (y * source.width + x) * RGBA_BYTES_PER_PIXEL;
        pixels[offset] = PRODUCTION_MASK_GRAYSCALE;
        pixels[offset + 1] = PRODUCTION_MASK_GRAYSCALE;
        pixels[offset + 2] = PRODUCTION_MASK_GRAYSCALE;
        pixels[offset + 3] = PRODUCTION_MASK_ALPHA;
      }
    }
  }

  return Object.freeze({
    width: source.width,
    height: source.height,
    format: "rgba8888" as const,
    opaqueReplacement: true as const,
    irreversibleDerivative: true as const,
    pixels,
  });
}
