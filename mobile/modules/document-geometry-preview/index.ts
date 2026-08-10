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

type DocumentGeometryPreviewNativeModule = {
  buildPreviewAsync(uri: string): Promise<GeometryPreviewResult>;
  estimateAngleAsync(previewUri: string): Promise<GeometryAngleEstimate>;
};

export default requireNativeModule<DocumentGeometryPreviewNativeModule>(
  "DocumentGeometryPreview",
);
