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

type DocumentGeometryPreviewNativeModule = {
  buildPreviewAsync(uri: string): Promise<GeometryPreviewResult>;
  estimateAngleAsync(previewUri: string): Promise<GeometryAngleEstimate>;
  applyFullFrameDeskewAsync(
    uri: string,
    previewUri: string,
  ): Promise<GeometryFullFrameDeskewResult>;
};

export default requireNativeModule<DocumentGeometryPreviewNativeModule>(
  "DocumentGeometryPreview",
);
