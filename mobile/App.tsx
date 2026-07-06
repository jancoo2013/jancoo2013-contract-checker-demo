import { StatusBar } from "expo-status-bar";
import React, { useMemo, useState } from "react";
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

const SYNTHETIC_ASSET = require("./assets/synthetic-redacted-contract.png") as ImageSourcePropType;
const SYNTHETIC_FILENAME = "synthetic_page.png";

type RequestStatus = "idle" | "sending" | "success" | "error";

type BackendErrorEnvelope = {
  error?: {
    code?: string;
    message_ru?: string;
  };
};

type AnalyzeRedactedResponse = {
  status?: string;
  ocr_quality?: {
    status?: string;
  };
  text_validation?: {
    usable?: boolean;
  };
  analysis?: {
    risk_profile?: string;
    risk_profile_summary_ru?: string;
  };
  evidence_validation?: {
    warnings?: unknown[];
  };
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

  return (parsed ?? {}) as AnalyzeRedactedResponse;
}

export default function App() {
  const apiBaseUrl = useMemo(resolveApiBaseUrl, []);
  const [result, setResult] = useState<ResultState>({ status: "idle" });

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

  const warningCount = result.response?.evidence_validation?.warnings?.length ?? 0;

  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Contract Checker Mobile Transport Test</Text>
        <Text style={styles.notice}>
          Synthetic test asset only. No camera, gallery, or personal document access is used in this
          build.
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

        {result.status === "success" ? (
          <View style={styles.resultBox}>
            <Text style={styles.resultTitle}>Safe response summary</Text>
            <Text style={styles.value}>status: {result.response?.status ?? "not provided"}</Text>
            <Text style={styles.value}>
              OCR quality: {result.response?.ocr_quality?.status ?? "not provided"}
            </Text>
            <Text style={styles.value}>
              text usable: {String(result.response?.text_validation?.usable ?? false)}
            </Text>
            <Text style={styles.value}>
              risk_profile: {result.response?.analysis?.risk_profile ?? "not provided"}
            </Text>
            <Text style={styles.value}>
              risk_profile_summary_ru: {" "}
              {result.response?.analysis?.risk_profile_summary_ru ?? "not provided"}
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
  errorText: {
    color: "#b91c1c",
    fontSize: 15,
    lineHeight: 21,
  },
});
