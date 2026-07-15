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

export type HebrewOcrResult = {
  modelBytes: number;
  text: string;
  elapsedMs: number;
  meanConfidence: number;
  width: number;
  height: number;
};

type TesseractOcrNativeModule = {
  isModelInstalledAsync(): Promise<HebrewModelStatus>;
  downloadHebrewModelAsync(): Promise<HebrewModelDownloadResult>;
  pickImageAsync(): Promise<PickedImage>;
  recognizeAsync(uri: string): Promise<HebrewOcrResult>;
};

export default requireNativeModule<TesseractOcrNativeModule>("TesseractOcr");
