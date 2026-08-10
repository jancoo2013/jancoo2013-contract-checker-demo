import { requireNativeModule } from "expo-modules-core";

export type DeskewValidationResult = {
  decision: "deskewed_full_frame" | "full_frame_fallback";
  outputUri: string;
  sourceWidth: number;
  sourceHeight: number;
  previewWidth: number;
  previewHeight: number;
  dominantTextAngleDegrees: number;
  deskewRotationDegrees: number;
  rotationAppliedDegrees: number;
  confidence: number;
  foregroundRatio: number;
  threshold: number;
  angleDecision: "accepted" | "rejected";
  rejectionReasons: string[];
  elapsedMs: number;
};

type NativeModule = {
  normalizeAsync(uri: string): Promise<DeskewValidationResult>;
};

export default requireNativeModule<NativeModule>("DocumentDeskewValidation");
