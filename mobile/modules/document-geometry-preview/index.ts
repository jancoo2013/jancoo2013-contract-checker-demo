import { requireNativeModule } from "expo-modules-core";

export type GeometryPreviewResult = Readonly<{
  previewUri: string;
  sourceWidth: number;
  sourceHeight: number;
  orientedWidth: number;
  orientedHeight: number;
  previewWidth: number;
  previewHeight: number;
  exifOrientation: number;
}>;

export type GeometryAngleEstimate = Readonly<{
  dominantTextAngleDegrees: number;
  deskewRotationDegrees: number;
  confidence: number;
  decision: "accepted" | "rejected";
  rejectionReasons: readonly string[];
  foregroundRatio: number;
  projectionGain: number;
  peakMargin: number;
}>;

export type GeometryContentRegionEstimate = Readonly<{
  coordinateSpace: "source_preview" | "deskewed_preview";
  previewWidth: number;
  previewHeight: number;
  deskewRotationDegrees: number;
  decision: "accepted" | "rotation_only" | "full_frame_fallback";
  confidence: number;
  lineBands: readonly (readonly [number, number, number, number])[];
  candidateContentBounds: readonly [number, number, number, number] | null;
  safeCropBounds: readonly [number, number, number, number] | null;
  rejectionReasons: readonly string[];
}>;

export type GeometryFullFrameDeskewResult = Readonly<{
  outputUri: string;
  decision: "deskewed_full_frame" | "full_frame_fallback";
  sourceWidth: number;
  sourceHeight: number;
  orientedWidth: number;
  orientedHeight: number;
  outputWidth: number;
  outputHeight: number;
  exifOrientation: number;
  rotationAppliedDegrees: number;
  fallbackReasons: readonly string[];
}>;

export type PreparedDocumentResult = Readonly<{
  outputUri: string;
  decision: "cropped_grayscale" | "full_frame_grayscale_fallback";
  colorMode: "grayscale";
  sourceWidth: number;
  sourceHeight: number;
  orientedWidth: number;
  orientedHeight: number;
  outputWidth: number;
  outputHeight: number;
  exifOrientation: number;
  rotationAppliedDegrees: number;
  cropBoxSource: readonly [number, number, number, number] | null;
  fallbackReasons: readonly string[];
}>;

type DocumentGeometryPreviewNativeModule = {
  buildPreviewAsync(uri: string): Promise<GeometryPreviewResult>;
  estimateAngleAsync(previewUri: string): Promise<GeometryAngleEstimate>;
  estimateContentRegionAsync(previewUri: string): Promise<GeometryContentRegionEstimate>;
  applyFullFrameDeskewAsync(
    uri: string,
    previewUri: string,
  ): Promise<GeometryFullFrameDeskewResult>;
  prepareDocumentAsync(
    uri: string,
    previewUri: string,
  ): Promise<PreparedDocumentResult>;
};

export default requireNativeModule<DocumentGeometryPreviewNativeModule>(
  "DocumentGeometryPreview",
);
