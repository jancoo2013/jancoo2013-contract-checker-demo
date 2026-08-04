import { requireNativeModule } from "expo-modules-core";

export type PickedImage = {
  canceled: boolean;
  uri?: string;
  name?: string;
  width?: number;
  height?: number;
};

export type HebrewModelDownloadResult = {
  installed: boolean;
  downloaded: boolean;
  bytes: number;
};

export type TesseractWordBox = {
  text: string;
  confidence: number;
  bbox: [number, number, number, number];
};

export type DirectPiiClass = "bank_identifier" | "email" | "phone" | "israeli_id";

export type DirectPiiWordBoxMatch = {
  matchId: string;
  piiClass: DirectPiiClass;
  detectorId: string;
  wordIndex: number;
  confidence: number;
  bbox: [number, number, number, number];
};

export type HebrewOcrResult = {
  text: string;
  wordBoxes: TesseractWordBox[];
  directPiiWordBoxes?: DirectPiiWordBoxMatch[];
  elapsedMs: number;
  meanConfidence: number;
  width: number;
  height: number;
};

type TesseractOcrNativeModule = {
  isModelInstalledAsync(): Promise<boolean>;
  downloadHebrewModelAsync(): Promise<HebrewModelDownloadResult>;
  pickImageAsync(): Promise<PickedImage>;
  recognizeAsync(uri: string): Promise<HebrewOcrResult>;
};

export default requireNativeModule<TesseractOcrNativeModule>("TesseractOcr");
