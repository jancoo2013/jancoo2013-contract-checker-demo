import { requireNativeModule } from "expo-modules-core";

export type LocalOcrItem = {
  text: string;
  confidence: number;
  bbox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
};

export type LocalOcrResult = {
  text: string;
  width: number;
  height: number;
  durationMs: number;
  items: LocalOcrItem[];
};

type LocalOcrModule = {
  recognizeBundledImage(assetName: string): Promise<LocalOcrResult>;
};

export default requireNativeModule<LocalOcrModule>("LocalOcr");
