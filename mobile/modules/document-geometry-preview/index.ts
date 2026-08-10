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

type DocumentGeometryPreviewNativeModule = {
  buildPreviewAsync(uri: string): Promise<GeometryPreviewResult>;
};

export default requireNativeModule<DocumentGeometryPreviewNativeModule>(
  "DocumentGeometryPreview",
);
