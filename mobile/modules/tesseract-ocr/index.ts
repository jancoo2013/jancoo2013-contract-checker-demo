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

export type HebrewOcrResult = {
  text: string;
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
