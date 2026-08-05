import { requireNativeModule } from "expo-modules-core";

import { validateHebrewOcrForPiiMasking } from "../../src/tesseractResult";

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

export type HebrewOcrResult = {
  text: string;
  wordBoxes: TesseractWordBox[];
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

const nativeModule = requireNativeModule<TesseractOcrNativeModule>("TesseractOcr");

const tesseractOcr: TesseractOcrNativeModule = {
  isModelInstalledAsync: () => nativeModule.isModelInstalledAsync(),
  downloadHebrewModelAsync: () => nativeModule.downloadHebrewModelAsync(),
  pickImageAsync: () => nativeModule.pickImageAsync(),
  recognizeAsync: async (uri: string) =>
    validateHebrewOcrForPiiMasking(await nativeModule.recognizeAsync(uri)),
};

export default tesseractOcr;
