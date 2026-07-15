import { StatusBar } from "expo-status-bar";
import React, { useEffect, useMemo, useState } from "react";
import {
  Button,
  Image,
  ImageSourcePropType,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import TesseractOcr, {
  HebrewModelVariant,
  HebrewOcrResult,
  PickedImage,
} from "./modules/tesseract-ocr";

const SYNTHETIC_ASSET = require("./assets/synthetic-redacted-contract.png") as ImageSourcePropType;
const SYNTHETIC_FILENAME = "synthetic_page.png";
const MODEL_VARIANTS: Array<{ variant: HebrewModelVariant; label: string }> = [
  { variant: "fast", label: "Fast" },
  { variant: "best", label: "Best" },
];

type RequestStatus = "idle" | "sending" | "success" | "error";
type ModelStatus = "checking" | "missing" | "downloading" | "ready" | "error";
type LocalOcrStatus = "idle" | "running" | "success" | "error";

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

type ModelState = {
  status: ModelStatus;
  message: string;
  bytes?: number;
};

type LocalOcrState = {
  status: LocalOcrStatus;
  result?: HebrewOcrResult;
  error?: string;
};

type ModelStates = Record<HebrewModelVariant, ModelState>;
type LocalOcrStates = Record<HebrewModelVariant, LocalOcrState>;

function initialModelStates(): ModelStates {
  return {
    fast: { status: "checking", message: "" },
    best: { status: "checking", message: "" },
  };
}

function initialLocalOcrStates(): LocalOcrStates {
  return {
    fast: { status: "idle" },
    best: { status: "idle" },
  };
}

function modelLabel(variant: HebrewModelVariant): string {
  return variant === "fast" ? "Fast" : "Best";
}

function formatBytes(bytes?: number): string {
  if (!bytes) {
    return "0 KB";
  }
  return bytes >= 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
    : `${Math.round(bytes / 1024)} KB`;
}

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
  const [modelStates, setModelStates] = useState<ModelStates>(initialModelStates);
  const [selectedModelVariant, setSelectedModelVariant] = useState<HebrewModelVariant>("fast");
  const [selectedImage, setSelectedImage] = useState<SelectedImage>();
  const [localOcrByVariant, setLocalOcrByVariant] = useState<LocalOcrStates>(initialLocalOcrStates);

  useEffect(() => {
    let active = true;

    for (const { variant } of MODEL_VARIANTS) {
      void TesseractOcr.isModelInstalledAsync(variant)
        .then((model) => {
          if (!active) {
            return;
          }
          setModelStates((current) => ({
            ...current,
            [variant]: {
              status: model.installed ? "ready" : "missing",
              bytes: model.bytes,
              message: model.installed
                ? `${modelLabel(variant)} Hebrew model is installed on this device.`
                : `${modelLabel(variant)} Hebrew model is not installed yet.`,
            },
          }));
        })
        .catch((error: unknown) => {
          if (!active) {
            return;
          }
          setModelStates((current) => ({
            ...current,
            [variant]: {
              ...current[variant],
              status: "error",
              message: errorMessage(error),
            },
          }));
        });
    }

    return () => {
      active = false;
    };
  }, []);

  async function handleDownloadModel(variant: HebrewModelVariant) {
    setModelStates((current) => ({
      ...current,
      [variant]: {
        ...current[variant],
        status: "downloading",
        message: `Downloading the ${modelLabel(variant)} Hebrew OCR model. No contract image is uploaded.`,
      },
    }));

    try {
      const download = await TesseractOcr.downloadHebrewModelAsync(variant);
      setModelStates((current) => ({
        ...current,
        [variant]: {
          status: "ready",
          bytes: download.bytes,
          message: `${download.downloaded ? "Downloaded" : "Already installed"} ${modelLabel(
            variant,
          )}: ${formatBytes(download.bytes)}`,
        },
      }));
    } catch (error: unknown) {
      setModelStates((current) => ({
        ...current,
        [variant]: {
          ...current[variant],
          status: "error",
          message: errorMessage(error),
        },
      }));
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
      setLocalOcrByVariant(initialLocalOcrStates());
    } catch (error: unknown) {
      setLocalOcrByVariant((current) => ({
        ...current,
        [selectedModelVariant]: { status: "error", error: errorMessage(error) },
      }));
    }
  }

  async function handleRunLocalOcr(variant: HebrewModelVariant) {
    const modelState = modelStates[variant];
    if (modelState.status !== "ready") {
      setLocalOcrByVariant((current) => ({
        ...current,
        [variant]: { status: "error", error: `Install the ${modelLabel(variant)} Hebrew OCR model first.` },
      }));
      return;
    }
    if (!selectedImage) {
      setLocalOcrByVariant((current) => ({
        ...current,
        [variant]: { status: "error", error: "Select one local contract image first." },
      }));
      return;
    }

    setLocalOcrByVariant((current) => ({
      ...current,
      [variant]: { status: "running" },
    }));
    try {
      const ocrResult = await TesseractOcr.recognizeAsync(selectedImage.uri, variant);
      setLocalOcrByVariant((current) => ({
        ...current,
        [variant]: { status: "success", result: ocrResult },
      }));
    } catch (error: unknown) {
      setLocalOcrByVariant((current) => ({
        ...current,
        [variant]: { status: "error", error: errorMessage(error) },
      }));
    }
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
  const selectedModelState = modelStates[selectedModelVariant];
  const selectedOcrState = localOcrByVariant[selectedModelVariant];
  const anyOcrRunning = MODEL_VARIANTS.some(({ variant }) => localOcrByVariant[variant].status === "running");

  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Android-only Tesseract OCR spike</Text>
        <Text style={styles.notice}>
          The selected image is copied into the app cache and processed locally on Android. The only network action in this spike is downloading official Hebrew language models for local OCR comparison.
        </Text>

        <View style={styles.section}>
          <Text style={styles.label}>Hebrew models</Text>
          {MODEL_VARIANTS.map(({ variant, label }) => {
            const state = modelStates[variant];
            return (
              <View key={variant} style={styles.modelBox}>
                <Text style={styles.resultTitle}>{label}</Text>
                <Text style={state.status === "error" ? styles.errorText : styles.value}>status: {state.status}</Text>
                <Text style={styles.value}>file size: {formatBytes(state.bytes)}</Text>
                <Text style={state.status === "error" ? styles.errorText : styles.caption}>{state.message}</Text>
                <Button
                  title={state.status === "downloading" ? `Downloading ${label}...` : `Download ${label} model`}
                  onPress={() => handleDownloadModel(variant)}
                  disabled={state.status === "checking" || state.status === "downloading" || state.status === "ready"}
                />
              </View>
            );
          })}
        </View>

        <View style={styles.section}>
          <Text style={styles.label}>Local input image</Text>
          <Button title="Select one image from Android" onPress={handlePickImage} disabled={anyOcrRunning} />
          {selectedImage ? (
            <>
              <Text style={styles.value}>{selectedImage.name ?? "selected image"}</Text>
              <Text style={styles.caption}>
                Source size: {selectedImage.width ?? "?"} x {selectedImage.height ?? "?"}
              </Text>
              <Image source={{ uri: selectedImage.uri }} style={styles.preview} resizeMode="contain" />
            </>
          ) : (
            <Text style={styles.caption}>No image selected.</Text>
          )}
        </View>

        <View style={styles.section}>
          <Text style={styles.label}>OCR model to run</Text>
          <View style={styles.variantRow}>
            {MODEL_VARIANTS.map(({ variant, label }) => (
              <View key={variant} style={styles.variantButton}>
                <Button
                  title={selectedModelVariant === variant ? `${label} selected` : `Use ${label}`}
                  onPress={() => setSelectedModelVariant(variant)}
                  disabled={anyOcrRunning}
                />
              </View>
            ))}
          </View>
          <Text style={selectedModelState.status === "error" ? styles.errorText : styles.caption}>
            Selected model: {modelLabel(selectedModelVariant)}; status: {selectedModelState.status}; size:{" "}
            {formatBytes(selectedModelState.bytes)}
          </Text>
        </View>

        <Button
          title={
            selectedOcrState.status === "running"
              ? `Recognizing with ${modelLabel(selectedModelVariant)}...`
              : `Run ${modelLabel(selectedModelVariant)} OCR on device`
          }
          onPress={() => handleRunLocalOcr(selectedModelVariant)}
          disabled={selectedOcrState.status === "running" || selectedModelState.status !== "ready" || !selectedImage}
        />

        <View style={styles.section}>
          <Text style={styles.label}>Local OCR results</Text>
          {MODEL_VARIANTS.map(({ variant, label }) => {
            const state = localOcrByVariant[variant];
            return (
              <View key={variant} style={state.status === "error" ? styles.errorBox : styles.resultBox}>
                <Text style={styles.resultTitle}>{label} raw Tesseract result</Text>
                <Text style={state.status === "error" ? styles.errorText : styles.value}>state: {state.status}</Text>
                {state.status === "success" && state.result ? (
                  <>
                    <Text style={styles.value}>model variant: {state.result.variant}</Text>
                    <Text style={styles.value}>model file: {formatBytes(state.result.modelBytes)}</Text>
                    <Text style={styles.value}>elapsed: {state.result.elapsedMs} ms</Text>
                    <Text style={styles.value}>mean confidence: {state.result.meanConfidence}</Text>
                    <Text style={styles.value}>
                      decoded bitmap: {state.result.width} x {state.result.height}
                    </Text>
                    <Text selectable style={styles.ocrText}>
                      {state.result.text || "(empty OCR result)"}
                    </Text>
                  </>
                ) : null}
                {state.status === "error" ? <Text style={styles.errorText}>{state.error}</Text> : null}
              </View>
            );
          })}
        </View>

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
    gap: 8,
  },
  modelBox: {
    backgroundColor: "#eef2ff",
    borderColor: "#c7d2fe",
    borderRadius: 6,
    borderWidth: 1,
    gap: 6,
    padding: 12,
  },
  variantRow: {
    flexDirection: "row",
    gap: 10,
  },
  variantButton: {
    flex: 1,
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
  divider: {
    backgroundColor: "#cbd5e1",
    height: 1,
    marginVertical: 6,
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
