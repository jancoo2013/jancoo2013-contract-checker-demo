import { requireNativeModule } from "expo-modules-core";

export type PickedImage = {
  canceled: boolean;
  uri?: string;
  name?: string;
  width?: number;
  height?: number;
};

export type HebrewModelStatus = {
  installed: boolean;
  bytes: number;
};

export type HebrewModelDownloadResult = {
  installed: boolean;
  downloaded: boolean;
  bytes: number;
};

export type HebrewOcrPageSegmentationMode =
  | "auto"
  | "single_column"
  | "single_block"
  | "sparse_text";

export type HebrewOcrSplitPercent = 35 | 40 | 45;

export type HebrewOcrRegionKind = "header" | "body";

export type HebrewOcrResult = {
  pageSegmentationMode: HebrewOcrPageSegmentationMode;
  modelBytes: number;
  text: string;
  elapsedMs: number;
  meanConfidence: number;
  width: number;
  height: number;
};

export type HebrewOcrRegionResult = {
  region: HebrewOcrRegionKind;
  pageSegmentationMode: HebrewOcrPageSegmentationMode;
  left: number;
  top: number;
  width: number;
  height: number;
  text: string;
  elapsedMs: number;
  meanConfidence: number;
};

export type HebrewZonedOcrResult = {
  splitPercent: HebrewOcrSplitPercent;
  modelBytes: number;
  decodedWidth: number;
  decodedHeight: number;
  totalElapsedMs: number;
  header: HebrewOcrRegionResult;
  body: HebrewOcrRegionResult;
};

type TesseractOcrNativeModule = {
  isModelInstalledAsync(): Promise<HebrewModelStatus>;
  downloadHebrewModelAsync(): Promise<HebrewModelDownloadResult>;
  pickImageAsync(): Promise<PickedImage>;
  recognizeAsync(uri: string, pageSegmentationMode: HebrewOcrPageSegmentationMode): Promise<HebrewOcrResult>;
  recognizeZonedAsync(uri: string, splitPercent: HebrewOcrSplitPercent): Promise<HebrewZonedOcrResult>;
};

export default requireNativeModule<TesseractOcrNativeModule>("TesseractOcr");
