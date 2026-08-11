import { StatusBar } from "expo-status-bar";
import React, { useEffect, useMemo, useState } from "react";
import {
  Button,
  Image,
  ImageSourcePropType,
  LayoutChangeEvent,
  Modal,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import DocumentGeometryPreview, {
  type GeometryAngleEstimate,
  type GeometryFullFrameDeskewResult,
  type GeometryPreviewResult,
} from "./modules/document-geometry-preview";
import TesseractOcr, {
  HebrewOcrResult,
  PickedImage,
} from "./modules/tesseract-ocr";
import {
  buildTesseractDevelopmentInspectionOverlay,
  type TesseractDevelopmentInspectionOverlay,
} from "./src/piiDevelopmentOverlayInspection";
import {
  buildTesseractPiiCandidateOverlay,
  type TesseractPiiCandidateOverlay,
} from "./src/piiCandidateOverlay";
import { validateHebrewOcrResult } from "./src/tesseractResult";

const SYNTHETIC_ASSET = require("./assets/synthetic-redacted-contract.png") as ImageSourcePropType;
const SYNTHETIC_FILENAME = "synthetic_page.png";

type RequestStatus = "idle" | "sending" | "success" | "error";
type ModelStatus = "checking" | "missing" | "downloading" | "ready" | "error";
type LocalOcrStatus = "idle" | "running" | "success" | "error";
type GeometryValidationStatus = "idle" | "running" | "success" | "error";

type BackendErrorEnvelope = {
  error?: {
    code?: string;
    message_ru?: string;
  };
};

type AnalyzeRedactedResponse = {
  status: string;
  ocr_quality: {
    status: string;
  };
  text_validation: {
    usable: boolean;
  };
  report: {
    risk_profile: string;
    risk_profile_summary_ru: string;
  };
  evidence_warnings: string[];
};

type ResultState = {
  status: RequestStatus;
  response?: AnalyzeRedactedResponse;
  error?: {
    httpStatus?: number;
    code?: string;
    messageRu: string;
  };
};

type SelectedImage = {
  uri: string;
  name?: string;
  width?: number;
  height?: number;
};

type GeometryValidationState = {
  status: GeometryValidationStatus;
  source?: SelectedImage;
  preview?: GeometryPreviewResult;
  angle?: GeometryAngleEstimate;
  transform?: GeometryFullFrameDeskewResult;
  error?: string;
};

type LocalOcrState = {
  status: LocalOcrStatus;
  result?: HebrewOcrResult;
  error?: string;
};

type PreviewSize = Readonly<{
  width: number;
  height: number;
}>;

type DevelopmentOverlayState =
  | Readonly<{ status: "idle" }>
  | Readonly<{ status: "ready"; overlay: TesseractDevelopmentInspectionOverlay }>
  | Readonly<{ status: "error"; error: string }>;

type PiiCandidateOverlayState =
  | Readonly<{ status: "idle" }>
  | Readonly<{ status: "ready"; overlay: TesseractPiiCandidateOverlay }>
  | Readonly<{ status: "error"; error: string }>;

type OverlayMode = "pii-candidates" | "all-ocr-word-boxes";

function resolveApiBaseUrl(): string {
  return (process.env.EXPO_PUBLIC_API_BASE_URL ?? "").trim().replace(/\/+$/, "");
}

function parseJsonSafely(text: string): unknown {
  if (!text) {
    return undefined;
  }

  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return String(error || "Unknown error");
}

function validateAnalyzeRedactedResponse(value: unknown): AnalyzeRedactedResponse {
  if (!isRecord(value)) {
    throw {
      messageRu: "Backend returned malformed success response.",
    };
  }

  const ocrQuality = value.ocr_quality;
  const textValidation = value.text_validation;
  const report = value.report;

  if (
    typeof value.status !== "string" ||
    !isRecord(ocrQuality) ||
    typeof ocrQuality.status !== "string" ||
    !isRecord(textValidation) ||
    typeof textValidation.usable !== "boolean" ||
    !isRecord(report) ||
    typeof report.risk_profile !== "string" ||
    typeof report.risk_profile_summary_ru !== "string" ||
    !isStringArray(value.evidence_warnings)
  ) {
    throw {
      messageRu: "Backend returned malformed success response.",
    };
  }

  return {
    status: value.status,
    ocr_quality: {
      status: ocrQuality.status,
    },
    text_validation: {
      usable: textValidation.usable,
    },
    report: {
      risk_profile: report.risk_profile,
      risk_profile_summary_ru: report.risk_profile_summary_ru,
    },
    evidence_warnings: value.evidence_warnings,
  };
}

async function postSyntheticPage(apiBaseUrl: string): Promise<AnalyzeRedactedResponse> {
  const assetSource = Image.resolveAssetSource(SYNTHETIC_ASSET);
  const formData = new FormData();

  formData.append("pages", {
    uri: assetSource.uri,
    name: SYNTHETIC_FILENAME,
    type: "image/png",
  } as unknown as Blob);
  formData.append("privacy_review_confirmed", "true");
  formData.append("client_request_id", `mobile-smoke-${Date.now()}`);

  const response = await fetch(`${apiBaseUrl}/v1/contracts/analyze-redacted`, {
    method: "POST",
    body: formData,
  });
  const responseText = await response.text();
  const parsed = parseJsonSafely(responseText);

  if (!response.ok) {
    const envelope = parsed as BackendErrorEnvelope | undefined;
    const error = envelope?.error;

    throw {
      httpStatus: response.status,
      code: error?.code,
      messageRu: error?.message_ru ?? "Backend returned an error without a safe Russian message.",
    };
  }

  return validateAnalyzeRedactedResponse(parsed);
}

export default function App() {
  const apiBaseUrl = useMemo(resolveApiBaseUrl, []);
  const [result, setResult] = useState<ResultState>({ status: "idle" });
  const [modelStatus, setModelStatus] = useState<ModelStatus>("checking");
  const [modelMessage, setModelMessage] = useState<string>("");
  const [geometryValidation, setGeometryValidation] = useState<GeometryValidationState>({ status: "idle" });
  const [fullscreenImageUri, setFullscreenImageUri] = useState<string>();
  const [selectedImage, setSelectedImage] = useState<SelectedImage>();
  const [localOcr, setLocalOcr] = useState<LocalOcrState>({ status: "idle" });
  const [previewSize, setPreviewSize] = useState<PreviewSize>();
  const [showDevelopmentOverlay, setShowDevelopmentOverlay] = useState(true);
  const [overlayMode, setOverlayMode] = useState<OverlayMode>("pii-candidates");

  useEffect(() => {
    let active = true;

    void TesseractOcr.isModelInstalledAsync()
      .then((installed) => {
        if (!active) {
          return;
        }
        setModelStatus(installed ? "ready" : "missing");
        setModelMessage(installed ? "Hebrew model is installed on this device." : "Hebrew model is not installed yet.");
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        setModelStatus("error");
        setModelMessage(errorMessage(error));
      });

    return () => {
      active = false;
    };
  }, []);

  const developmentOverlayState = useMemo<DevelopmentOverlayState>(() => {
    if (localOcr.status !== "success" || !localOcr.result || !previewSize) {
      return { status: "idle" };
    }

    try {
      return {
        status: "ready",
        overlay: buildTesseractDevelopmentInspectionOverlay(
          localOcr.result,
          previewSize.width,
          previewSize.height,
        ),
      };
    } catch (error: unknown) {
      return { status: "error", error: errorMessage(error) };
    }
  }, [localOcr, previewSize]);

  const piiCandidateOverlayState = useMemo<PiiCandidateOverlayState>(() => {
    if (localOcr.status !== "success" || !localOcr.result || !previewSize) {
      return { status: "idle" };
    }

    try {
      return {
        status: "ready",
        overlay: buildTesseractPiiCandidateOverlay(
          localOcr.result,
          previewSize.width,
          previewSize.height,
        ),
      };
    } catch (error: unknown) {
      return { status: "error", error: errorMessage(error) };
    }
  }, [localOcr, previewSize]);

  async function handleGeometryValidation() {
    setFullscreenImageUri(undefined);
    let source: SelectedImage | undefined;
    let preview: GeometryPreviewResult | undefined;

    try {
      const picked: PickedImage = await TesseractOcr.pickImageAsync();
      if (picked.canceled) {
        return;
      }
      if (!picked.uri) {
        throw new Error("Android returned no image URI.");
      }

      setGeometryValidation({ status: "running" });
      source = {
        uri: picked.uri,
        name: picked.name,
        width: picked.width,
        height: picked.height,
      };
      preview = await DocumentGeometryPreview.buildPreviewAsync(source.uri);
      setGeometryValidation({ status: "running", source, preview });

      const angle = await DocumentGeometryPreview.estimateAngleAsync(preview.previewUri);
      const transform = await DocumentGeometryPreview.applyFullFrameDeskewAsync(
        source.uri,
        preview.previewUri,
      );
      setGeometryValidation({ status: "success", source, preview, angle, transform });
    } catch (error: unknown) {
      setGeometryValidation({ status: "error", source, preview, error: errorMessage(error) });
    }
  }

  function handleResetGeometryValidation() {
    setFullscreenImageUri(undefined);
    setGeometryValidation({ status: "idle" });
  }

  async function handleDownloadModel() {
    setModelStatus("downloading");
    setModelMessage("Downloading the Hebrew OCR model. No contract image is uploaded.");

    try {
      const download = await TesseractOcr.downloadHebrewModelAsync();
      setModelStatus("ready");
      setModelMessage(
        `${download.downloaded ? "Downloaded" : "Already installed"}: ${Math.round(download.bytes / 1024)} KB`,
      );
    } catch (error: unknown) {
      setModelStatus("error");
      setModelMessage(errorMessage(error));
    }
  }

  async function handlePickImage() {
    try {
      const picked: PickedImage = await TesseractOcr.pickImageAsync();
      if (picked.canceled) {
        return;
      }
      if (!picked.uri) {
        throw new Error("Android returned no image URI.");
      }

      setSelectedImage({
        uri: picked.uri,
        name: picked.name,
        width: picked.width,
        height: picked.height,
      });
      setLocalOcr({ status: "idle" });
      setShowDevelopmentOverlay(true);
      setOverlayMode("pii-candidates");
    } catch (error: unknown) {
      setLocalOcr({ status: "error", error: errorMessage(error) });
    }
  }

  async function handleRunLocalOcr() {
    if (modelStatus !== "ready") {
      setLocalOcr({ status: "error", error: "Install the Hebrew OCR model first." });
      return;
    }
    if (!selectedImage) {
      setLocalOcr({ status: "error", error: "Select one local contract image first." });
      return;
    }

    setLocalOcr({ status: "running" });
    setShowDevelopmentOverlay(true);
    setOverlayMode("pii-candidates");
    try {
      const ocrResult = validateHebrewOcrResult(await TesseractOcr.recognizeAsync(selectedImage.uri));
      setLocalOcr({ status: "success", result: ocrResult });
    } catch (error: unknown) {
      setLocalOcr({ status: "error", error: errorMessage(error) });
    }
  }

  function handlePreviewLayout(event: LayoutChangeEvent) {
    const { width, height } = event.nativeEvent.layout;
    setPreviewSize((current) =>
      current?.width === width && current.height === height ? current : { width, height },
    );
  }

  async function handleSend() {
    if (!apiBaseUrl) {
      setResult({
        status: "error",
        error: {
          messageRu: "EXPO_PUBLIC_API_BASE_URL is not configured.",
        },
      });
      return;
    }

    setResult({ status: "sending" });

    try {
      const response = await postSyntheticPage(apiBaseUrl);
      setResult({ status: "success", response });
    } catch (error) {
      const safeError = error as ResultState["error"] | undefined;
      setResult({
        status: "error",
        error: {
          httpStatus: safeError?.httpStatus,
          code: safeError?.code,
          messageRu: safeError?.messageRu ?? "Network request failed.",
        },
      });
    }
  }

  const successResponse = result.status === "success" ? result.response : undefined;
  const warningCount = successResponse?.evidence_warnings.length ?? 0;
  const activeOverlayReady =
    overlayMode === "pii-candidates"
      ? piiCandidateOverlayState.status === "ready"
      : developmentOverlayState.status === "ready";
  const activeOverlayOpacity =
    overlayMode === "pii-candidates"
      ? piiCandidateOverlayState.status === "ready"
        ? piiCandidateOverlayState.overlay.opacity
        : 0
      : developmentOverlayState.status === "ready"
        ? developmentOverlayState.overlay.opacity
        : 0;
  const activeOverlayRects =
    overlayMode === "pii-candidates"
      ? piiCandidateOverlayState.status === "ready"
        ? piiCandidateOverlayState.overlay.candidateRects
        : []
      : developmentOverlayState.status === "ready"
        ? developmentOverlayState.overlay.wordRects
        : [];
  const activeOverlayError =
    overlayMode === "pii-candidates"
      ? piiCandidateOverlayState.status === "error"
        ? piiCandidateOverlayState.error
        : undefined
      : developmentOverlayState.status === "error"
        ? developmentOverlayState.error
        : undefined;

  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="dark" />
      <Modal
        visible={Boolean(fullscreenImageUri)}
        animationType="fade"
        onRequestClose={() => setFullscreenImageUri(undefined)}
      >
        <SafeAreaView style={styles.fullscreenBackdrop}>
          {fullscreenImageUri ? (
            <Image source={{ uri: fullscreenImageUri }} style={styles.fullscreenImage} resizeMode="contain" />
          ) : null}
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Close full-screen image"
            onPress={() => setFullscreenImageUri(undefined)}
            style={styles.fullscreenCloseButton}
          >
            <Text style={styles.fullscreenCloseText}>Close</Text>
          </Pressable>
        </SafeAreaView>
      </Modal>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Document geometry validation</Text>
        <Text style={styles.notice}>
          Development-only local check. The selected photo is first validated by the bounded Android geometry module; the UI renders only its bounded source preview and does not run OCR or upload the photo.
        </Text>
        <Button
          title={geometryValidation.status === "running" ? "Processing geometry..." : "Select photo and run geometry"}
          onPress={handleGeometryValidation}
          disabled={geometryValidation.status === "running"}
        />
        <View style={styles.section}>
          <Text style={styles.label}>Geometry state</Text>
          <Text style={geometryValidation.status === "error" ? styles.errorText : styles.value}>
            {geometryValidation.status}
          </Text>
        </View>

        {geometryValidation.source && geometryValidation.preview ? (
          <View style={styles.geometryBox}>
            <Text style={styles.resultTitle}>Bounded source preview</Text>
            <Text style={styles.caption}>{geometryValidation.source.name ?? "selected local photo"}</Text>
            <Text style={styles.caption}>
              source: {geometryValidation.preview.sourceWidth} × {geometryValidation.preview.sourceHeight}; preview: {geometryValidation.preview.previewWidth} × {geometryValidation.preview.previewHeight}
            </Text>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Open bounded source preview full screen"
              onPress={() => setFullscreenImageUri(geometryValidation.preview?.previewUri)}
            >
              <Image source={{ uri: geometryValidation.preview.previewUri }} style={styles.geometryImage} resizeMode="contain" />
            </Pressable>
            <Text style={styles.caption}>Tap image to enlarge.</Text>
          </View>
        ) : null}

        {geometryValidation.status === "success" && geometryValidation.angle && geometryValidation.transform ? (
          <>
            <View style={styles.geometryBox}>
              <Text style={styles.resultTitle}>Full-frame deskew result</Text>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Open full-frame deskew result full screen"
                onPress={() => setFullscreenImageUri(geometryValidation.transform?.outputUri)}
              >
                <Image
                  source={{ uri: geometryValidation.transform.outputUri }}
                  style={styles.geometryImage}
                  resizeMode="contain"
                />
              </Pressable>
              <Text style={styles.caption}>Tap image to enlarge.</Text>
              <Text style={styles.value}>
                output: {geometryValidation.transform.outputWidth} × {geometryValidation.transform.outputHeight}
              </Text>
              <Text style={styles.value}>transform: {geometryValidation.transform.decision}</Text>
              <Text style={styles.value}>
                rotation applied: {geometryValidation.transform.rotationAppliedDegrees.toFixed(2)}°
              </Text>
              <Text style={styles.caption}>
                fallback reasons: {geometryValidation.transform.fallbackReasons.length > 0 ? geometryValidation.transform.fallbackReasons.join(", ") : "none"}
              </Text>
            </View>
            <View style={styles.inspectionBox}>
              <Text style={styles.resultTitle}>Native angle evidence</Text>
              <Text style={styles.value}>
                dominant text angle: {geometryValidation.angle.dominantTextAngleDegrees.toFixed(2)}°
              </Text>
              <Text style={styles.value}>
                requested deskew: {geometryValidation.angle.deskewRotationDegrees.toFixed(2)}°
              </Text>
              <Text style={styles.value}>confidence: {geometryValidation.angle.confidence.toFixed(4)}</Text>
              <Text style={styles.value}>decision: {geometryValidation.angle.decision}</Text>
              <Text style={styles.caption}>
                reasons: {geometryValidation.angle.rejectionReasons.length > 0 ? geometryValidation.angle.rejectionReasons.join(", ") : "none"}
              </Text>
            </View>
          </>
        ) : null}

        {geometryValidation.status === "error" ? (
          <View style={styles.errorBox}>
            <Text style={styles.resultTitle}>Geometry validation error</Text>
            <Text style={styles.errorText}>{geometryValidation.error}</Text>
          </View>
        ) : null}

        {geometryValidation.status !== "idle" ? (
          <View style={styles.geometryActions}>
            <Button
              title="Select another photo"
              onPress={handleGeometryValidation}
              disabled={geometryValidation.status === "running"}
            />
            <Button
              title="Reset"
              onPress={handleResetGeometryValidation}
              disabled={geometryValidation.status === "running"}
            />
          </View>
        ) : null}

        <View style={styles.divider} />

        <Text style={styles.secondaryTitle}>Existing Android-only Tesseract OCR spike</Text>
        <Text style={styles.notice}>
          The separate legacy spike below is unchanged. Its locally selected OCR image is not reused by the geometry validation path above.
        </Text>

        <View style={styles.section}>
          <Text style={styles.label}>Hebrew model</Text>
          <Text style={modelStatus === "error" ? styles.errorText : styles.value}>{modelStatus}</Text>
          <Text style={modelStatus === "error" ? styles.errorText : styles.caption}>{modelMessage}</Text>
          <Button
            title={modelStatus === "downloading" ? "Downloading model..." : "Download Hebrew OCR model"}
            onPress={handleDownloadModel}
            disabled={modelStatus === "checking" || modelStatus === "downloading" || modelStatus === "ready"}
          />
        </View>

        <View style={styles.section}>
          <Text style={styles.label}>Local input image</Text>
          <Button title="Select one image from Android" onPress={handlePickImage} disabled={localOcr.status === "running"} />
          {selectedImage ? (
            <>
              <Text style={styles.value}>{selectedImage.name ?? "selected image"}</Text>
              <Text style={styles.caption}>
                Source size: {selectedImage.width ?? "?"} × {selectedImage.height ?? "?"}
              </Text>
              <View style={styles.previewFrame} onLayout={handlePreviewLayout}>
                <Image source={{ uri: selectedImage.uri }} style={styles.previewImage} resizeMode="contain" />
                {showDevelopmentOverlay && activeOverlayReady
                  ? activeOverlayRects.map((rect, rectIndex) => (
                      <View
                        key={`development-word-${overlayMode}-${rectIndex}-${rect.wordIndex}`}
                        pointerEvents="none"
                        style={[
                          styles.developmentMask,
                          {
                            left: rect.left,
                            top: rect.top,
                            width: rect.width,
                            height: rect.height,
                            opacity: activeOverlayOpacity,
                          },
                        ]}
                      />
                    ))
                  : null}
              </View>
            </>
          ) : (
            <Text style={styles.caption}>No image selected.</Text>
          )}
        </View>

        <Button
          title={localOcr.status === "running" ? "Recognizing locally..." : "Run Hebrew OCR on device"}
          onPress={handleRunLocalOcr}
          disabled={localOcr.status === "running" || modelStatus !== "ready" || !selectedImage}
        />

        <View style={styles.section}>
          <Text style={styles.label}>Local OCR state</Text>
          <Text style={localOcr.status === "error" ? styles.errorText : styles.value}>{localOcr.status}</Text>
        </View>

        {localOcr.status === "success" && localOcr.result ? (
          <View style={styles.inspectionBox}>
            <Text style={styles.resultTitle}>Development overlay inspection</Text>
            <Text style={styles.caption}>
              {overlayMode === "pii-candidates"
                ? "Red semi-transparent rectangles show approved direct-value PII candidates from this local OCR pass: email, Israeli phone, checksum-valid Israeli ID, and checksum-valid IL IBAN. They are not a masking decision, do not prove complete PII coverage, and are never saved or sent."
                : "Red semi-transparent rectangles show every validated Tesseract word box from this local OCR pass. They are not PII decisions and are never saved or sent."}
            </Text>
            {overlayMode === "pii-candidates" && piiCandidateOverlayState.status === "ready" ? (
              <>
                <Text style={styles.value}>
                  candidate rectangles: {piiCandidateOverlayState.overlay.candidateRects.length}
                </Text>
                <Text style={styles.value}>
                  candidates: total {piiCandidateOverlayState.overlay.summary.totalCandidates}, email {piiCandidateOverlayState.overlay.summary.email}, phone {piiCandidateOverlayState.overlay.summary.phone}, ID {piiCandidateOverlayState.overlay.summary.israeliId}, IBAN {piiCandidateOverlayState.overlay.summary.bankIdentifier}
                </Text>
              </>
            ) : null}
            {overlayMode === "all-ocr-word-boxes" && developmentOverlayState.status === "ready" ? (
              <Text style={styles.value}>
                visible rectangles: {developmentOverlayState.overlay.wordRects.length}
              </Text>
            ) : null}
            {activeOverlayReady ? (
              <>
                <Button
                  title={showDevelopmentOverlay ? "Hide overlay" : "Show overlay"}
                  onPress={() => setShowDevelopmentOverlay((visible) => !visible)}
                  disabled={activeOverlayRects.length === 0}
                />
                <Button
                  title={overlayMode === "pii-candidates" ? "Switch to all OCR boxes" : "Switch to PII candidates"}
                  onPress={() =>
                    setOverlayMode((current) =>
                      current === "pii-candidates" ? "all-ocr-word-boxes" : "pii-candidates",
                    )
                  }
                />
              </>
            ) : null}
            {activeOverlayError ? (
              <Text style={styles.errorText}>{activeOverlayError}</Text>
            ) : null}
          </View>
        ) : null}

        {localOcr.status === "success" && localOcr.result ? (
          <View style={styles.resultBox}>
            <Text style={styles.resultTitle}>Raw Tesseract result</Text>
            <Text style={styles.value}>elapsed: {localOcr.result.elapsedMs} ms</Text>
            <Text style={styles.value}>mean confidence: {localOcr.result.meanConfidence}</Text>
            <Text style={styles.value}>word boxes: {localOcr.result.wordBoxes.length}</Text>
            <Text style={styles.value}>
              decoded bitmap: {localOcr.result.width} × {localOcr.result.height}
            </Text>
            <Text selectable style={styles.ocrText}>
              {localOcr.result.text || "(empty OCR result)"}
            </Text>
          </View>
        ) : null}

        {localOcr.status === "error" ? (
          <View style={styles.errorBox}>
            <Text style={styles.resultTitle}>Local OCR error</Text>
            <Text style={styles.errorText}>{localOcr.error}</Text>
          </View>
        ) : null}

        <View style={styles.divider} />

        <Text style={styles.secondaryTitle}>Existing backend transport test</Text>
        <Text style={styles.notice}>
          This separate test still sends only the bundled synthetic redacted PNG. It never sends the locally selected OCR image.
        </Text>

        <View style={styles.section}>
          <Text style={styles.label}>Backend API URL</Text>
          <Text style={apiBaseUrl ? styles.value : styles.errorText}>
            {apiBaseUrl || "Missing EXPO_PUBLIC_API_BASE_URL"}
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.label}>Synthetic asset</Text>
          <Text style={styles.value}>{SYNTHETIC_FILENAME}</Text>
          <Image source={SYNTHETIC_ASSET} style={styles.preview} resizeMode="contain" />
          <Text style={styles.caption}>
            Bundled synthetic PNG only. It is never a user-provided document.
          </Text>
        </View>

        <Button
          title={result.status === "sending" ? "Sending..." : "Send synthetic redacted PNG"}
          onPress={handleSend}
          disabled={result.status === "sending"}
        />

        <View style={styles.section}>
          <Text style={styles.label}>Request state</Text>
          <Text style={styles.value}>{result.status}</Text>
        </View>

        {successResponse ? (
          <View style={styles.resultBox}>
            <Text style={styles.resultTitle}>Safe response summary</Text>
            <Text style={styles.value}>status: {successResponse.status}</Text>
            <Text style={styles.value}>OCR quality: {successResponse.ocr_quality.status}</Text>
            <Text style={styles.value}>
              text usable: {String(successResponse.text_validation.usable)}
            </Text>
            <Text style={styles.value}>risk_profile: {successResponse.report.risk_profile}</Text>
            <Text style={styles.value}>
              risk_profile_summary_ru: {successResponse.report.risk_profile_summary_ru}
            </Text>
            <Text style={styles.value}>evidence warnings: {warningCount}</Text>
          </View>
        ) : null}

        {result.status === "error" ? (
          <View style={styles.errorBox}>
            <Text style={styles.resultTitle}>Safe error summary</Text>
            {result.error?.httpStatus ? (
              <Text style={styles.errorText}>HTTP status: {result.error.httpStatus}</Text>
            ) : null}
            {result.error?.code ? <Text style={styles.errorText}>code: {result.error.code}</Text> : null}
            <Text style={styles.errorText}>{result.error?.messageRu}</Text>
          </View>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: "#f8fafc",
  },
  content: {
    padding: 20,
    gap: 18,
  },
  title: {
    color: "#111827",
    fontSize: 26,
    fontWeight: "700",
  },
  secondaryTitle: {
    color: "#111827",
    fontSize: 21,
    fontWeight: "700",
  },
  notice: {
    color: "#334155",
    fontSize: 16,
    lineHeight: 23,
  },
  section: {
    gap: 6,
  },
  label: {
    color: "#475569",
    fontSize: 13,
    fontWeight: "700",
    textTransform: "uppercase",
  },
  value: {
    color: "#111827",
    fontSize: 15,
    lineHeight: 21,
  },
  caption: {
    color: "#64748b",
    fontSize: 13,
    lineHeight: 18,
  },
  preview: {
    alignSelf: "stretch",
    backgroundColor: "#ffffff",
    borderColor: "#cbd5e1",
    borderRadius: 6,
    borderWidth: 1,
    height: 260,
  },
  geometryBox: {
    backgroundColor: "#ffffff",
    borderColor: "#94a3b8",
    borderRadius: 6,
    borderWidth: 1,
    gap: 6,
    padding: 12,
  },
  geometryImage: {
    alignSelf: "stretch",
    backgroundColor: "#ffffff",
    borderColor: "#cbd5e1",
    borderRadius: 6,
    borderWidth: 1,
    height: 320,
  },
  geometryActions: {
    gap: 10,
  },
  fullscreenBackdrop: {
    backgroundColor: "#000000",
    flex: 1,
    padding: 16,
  },
  fullscreenImage: {
    flex: 1,
    height: "100%",
    width: "100%",
  },
  fullscreenCloseButton: {
    alignItems: "center",
    backgroundColor: "#ffffff",
    borderRadius: 6,
    marginTop: 12,
    padding: 14,
  },
  fullscreenCloseText: {
    color: "#111827",
    fontSize: 16,
    fontWeight: "700",
  },
  previewFrame: {
    alignSelf: "stretch",
    backgroundColor: "#ffffff",
    borderColor: "#cbd5e1",
    borderRadius: 6,
    borderWidth: 1,
    height: 260,
    overflow: "hidden",
    position: "relative",
  },
  previewImage: {
    height: "100%",
    width: "100%",
  },
  developmentMask: {
    backgroundColor: "#ef4444",
    borderColor: "#991b1b",
    borderWidth: 1,
    position: "absolute",
  },
  divider: {
    backgroundColor: "#cbd5e1",
    height: 1,
    marginVertical: 6,
  },
  inspectionBox: {
    backgroundColor: "#fff7ed",
    borderColor: "#f97316",
    borderRadius: 6,
    borderWidth: 1,
    gap: 8,
    padding: 12,
  },
  resultBox: {
    backgroundColor: "#ecfdf5",
    borderColor: "#10b981",
    borderRadius: 6,
    borderWidth: 1,
    gap: 6,
    padding: 12,
  },
  errorBox: {
    backgroundColor: "#fef2f2",
    borderColor: "#ef4444",
    borderRadius: 6,
    borderWidth: 1,
    gap: 6,
    padding: 12,
  },
  resultTitle: {
    color: "#111827",
    fontSize: 16,
    fontWeight: "700",
  },
  ocrText: {
    backgroundColor: "#ffffff",
    borderColor: "#a7f3d0",
    borderRadius: 4,
    borderWidth: 1,
    color: "#111827",
    fontSize: 16,
    lineHeight: 24,
    marginTop: 6,
    minHeight: 120,
    padding: 10,
    textAlign: "right",
    writingDirection: "rtl",
  },
  errorText: {
    color: "#b91c1c",
    fontSize: 15,
    lineHeight: 21,
  },
});
