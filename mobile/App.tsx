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
  HebrewOcrResult,
  PickedImage,
} from "./modules/tesseract-ocr";

const SYNTHETIC_ASSET = require("./assets/synthetic-redacted-contract.png") as ImageSourcePropType;
const SYNTHETIC_FILENAME = "synthetic_page.png";

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

type LocalOcrState = {
  status: LocalOcrStatus;
  result?: HebrewOcrResult;
  error?: string;
};

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
  const [modelStatus, setModelStatus] = useState<ModelStatus>("checking");
  const [modelMessage, setModelMessage] = useState<string>("");
  const [modelBytes, setModelBytes] = useState<number>(0);
  const [selectedImage, setSelectedImage] = useState<SelectedImage>();
  const [localOcr, setLocalOcr] = useState<LocalOcrState>({ status: "idle" });

  useEffect(() => {
    let active = true;

    void TesseractOcr.isModelInstalledAsync()
      .then((model) => {
        if (!active) {
          return;
        }
        setModelStatus(model.installed ? "ready" : "missing");
        setModelBytes(model.bytes);
        setModelMessage(
          model.installed
            ? "Best Hebrew model is installed on this device."
            : "Best Hebrew model is not installed yet.",
        );
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

  async function handleDownloadModel() {
    setModelStatus("downloading");
    setModelMessage("Downloading the Best Hebrew OCR model. No contract image is uploaded.");

    try {
      const download = await TesseractOcr.downloadHebrewModelAsync();
      setModelStatus("ready");
      setModelBytes(download.bytes);
      setModelMessage(
        `${download.downloaded ? "Downloaded" : "Already installed"} Best model: ${formatBytes(download.bytes)}`,
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
    } catch (error: unknown) {
      setLocalOcr({ status: "error", error: errorMessage(error) });
    }
  }

  async function handleRunLocalOcr() {
    if (modelStatus !== "ready") {
      setLocalOcr({ status: "error", error: "Install the Best Hebrew OCR model first." });
      return;
    }
    if (!selectedImage) {
      setLocalOcr({ status: "error", error: "Select one local contract image first." });
      return;
    }

    setLocalOcr({ status: "running" });
    try {
      const ocrResult = await TesseractOcr.recognizeAsync(selectedImage.uri);
      setLocalOcr({ status: "success", result: ocrResult });
    } catch (error: unknown) {
      setLocalOcr({ status: "error", error: errorMessage(error) });
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

  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Android-only Tesseract OCR spike</Text>
        <Text style={styles.notice}>
          The selected image is copied into the app cache and processed locally on Android. The only network action in this spike is downloading the official Best Hebrew language model once.
        </Text>

        <View style={styles.section}>
          <Text style={styles.label}>Hebrew model</Text>
          <Text style={modelStatus === "error" ? styles.errorText : styles.value}>{modelStatus}</Text>
          <Text style={styles.value}>file size: {formatBytes(modelBytes)}</Text>
          <Text style={modelStatus === "error" ? styles.errorText : styles.caption}>{modelMessage}</Text>
          <Button
            title={modelStatus === "downloading" ? "Downloading Best model..." : "Download Best Hebrew OCR model"}
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
                Source size: {selectedImage.width ?? "?"} x {selectedImage.height ?? "?"}
              </Text>
              <Image source={{ uri: selectedImage.uri }} style={styles.preview} resizeMode="contain" />
            </>
          ) : (
            <Text style={styles.caption}>No image selected.</Text>
          )}
        </View>

        <Button
          title={localOcr.status === "running" ? "Recognizing locally..." : "Run Best Hebrew OCR on device"}
          onPress={handleRunLocalOcr}
          disabled={localOcr.status === "running" || modelStatus !== "ready" || !selectedImage}
        />

        <View style={styles.section}>
          <Text style={styles.label}>Local OCR state</Text>
          <Text style={localOcr.status === "error" ? styles.errorText : styles.value}>{localOcr.status}</Text>
        </View>

        {localOcr.status === "success" && localOcr.result ? (
          <View style={styles.resultBox}>
            <Text style={styles.resultTitle}>Raw Tesseract Best result</Text>
            <Text style={styles.value}>model file: {formatBytes(localOcr.result.modelBytes)}</Text>
            <Text style={styles.value}>elapsed: {localOcr.result.elapsedMs} ms</Text>
            <Text style={styles.value}>mean confidence: {localOcr.result.meanConfidence}</Text>
            <Text style={styles.value}>
              decoded bitmap: {localOcr.result.width} x {localOcr.result.height}
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
