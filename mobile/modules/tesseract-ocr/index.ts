import { requireNativeModule } from "expo-modules-core";

export type PickedImage = {
  canceled: boolean;
  uri?: string;
  name?: string;
  width?: number;
  height?: number;
};

export type HebrewModelVariant = "fast" | "best";

export type HebrewModelStatus = {
  variant: HebrewModelVariant;
  installed: boolean;
  bytes: number;
};

export type HebrewModelDownloadResult = {
  variant: HebrewModelVariant;
  installed: boolean;
  downloaded: boolean;
  bytes: number;
};

export type HebrewOcrResult = {
  variant: HebrewModelVariant;
  modelInstalled: boolean;
  modelBytes: number;
  text: string;
  elapsedMs: number;
  meanConfidence: number;
  width: number;
  height: number;
};

type TesseractOcrNativeModule = {
  isModelInstalledAsync(variant: HebrewModelVariant): Promise<HebrewModelStatus>;
  downloadHebrewModelAsync(variant: HebrewModelVariant): Promise<HebrewModelDownloadResult>;
  pickImageAsync(): Promise<PickedImage>;
  recognizeAsync(uri: string, variant: HebrewModelVariant): Promise<HebrewOcrResult>;
};

export default requireNativeModule<TesseractOcrNativeModule>("TesseractOcr");
