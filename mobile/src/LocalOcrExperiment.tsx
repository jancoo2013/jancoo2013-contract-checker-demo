import React, { useMemo, useState } from "react";
import {
  Button,
  Image,
  ImageSourcePropType,
  LayoutChangeEvent,
  StyleSheet,
  Text,
  View,
} from "react-native";
import LocalOcr, { LocalOcrResult } from "local-ocr";
import {
  countProposalsByType,
  detectPiiProposals,
  PiiProposal,
} from "./localOcrCandidates";
import { Box, mapImageBoxToContainedViewBox, Size } from "./overlayGeometry";

type OcrStatus = "idle" | "running" | "success" | "error";

type SyntheticImage = {
  label: string;
  assetName:
    | "synthetic-hebrew-pii.png"
    | "synthetic-hebrew-pii-large.png"
    | "synthetic-hebrew-layout.png";
  source: ImageSourcePropType;
};

const SYNTHETIC_IMAGES: SyntheticImage[] = [
  {
    label: "Hebrew PII markers",
    assetName: "synthetic-hebrew-pii.png",
    source: require("../assets/synthetic-hebrew-pii.png") as ImageSourcePropType,
  },
  {
    label: "Hebrew PII large",
    assetName: "synthetic-hebrew-pii-large.png",
    source: require("../assets/synthetic-hebrew-pii-large.png") as ImageSourcePropType,
  },
  {
    label: "Hebrew layout",
    assetName: "synthetic-hebrew-layout.png",
    source: require("../assets/synthetic-hebrew-layout.png") as ImageSourcePropType,
  },
];

export function LocalOcrExperiment() {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [status, setStatus] = useState<OcrStatus>("idle");
  const [result, setResult] = useState<LocalOcrResult | undefined>();
  const [errorMessage, setErrorMessage] = useState<string | undefined>();
  const [viewSize, setViewSize] = useState<Size>({ width: 0, height: 0 });
  const selectedImage = SYNTHETIC_IMAGES[selectedIndex];

  const proposals = useMemo<PiiProposal[]>(
    () =>
      result
        ? detectPiiProposals(result.items, { width: result.width, height: result.height })
        : [],
    [result],
  );
  const countsByType = useMemo(() => countProposalsByType(proposals), [proposals]);

  async function handleRunOcr() {
    setStatus("running");
    setResult(undefined);
    setErrorMessage(undefined);

    try {
      const nextResult = await LocalOcr.recognizeBundledImage(selectedImage.assetName);
      setResult(nextResult);
      setStatus("success");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Local OCR failed.";
      setErrorMessage(message);
      setStatus("error");
    }
  }

  function handleImageLayout(event: LayoutChangeEvent) {
    setViewSize({
      width: event.nativeEvent.layout.width,
      height: event.nativeEvent.layout.height,
    });
  }

  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Local OCR Experiment</Text>
      <Text style={styles.notice}>
        Android research spike. Uses bundled synthetic images and on-device OCR only. No camera,
        gallery, backend, Gemini, model download, or telemetry is used by this block.
      </Text>

      <View style={styles.switchRow}>
        {SYNTHETIC_IMAGES.map((image, index) => (
          <View key={image.assetName} style={styles.switchButton}>
            <Button
              title={image.label}
              onPress={() => {
                setSelectedIndex(index);
                setResult(undefined);
                setErrorMessage(undefined);
                setStatus("idle");
              }}
              disabled={selectedIndex === index || status === "running"}
            />
          </View>
        ))}
      </View>

      <View style={styles.previewFrame} onLayout={handleImageLayout}>
        <Image source={selectedImage.source} style={styles.previewImage} resizeMode="contain" />
        {result
          ? proposals.map((proposal, index) => (
              <ProposalOverlay
                key={`${proposal.type}-${index}`}
                proposal={proposal}
                imageSize={{ width: result.width, height: result.height }}
                viewSize={viewSize}
              />
            ))
          : null}
      </View>

      <Button
        title={status === "running" ? "Running local OCR..." : "Run local OCR"}
        onPress={handleRunOcr}
        disabled={status === "running"}
      />

      <View style={styles.metricsBox}>
        <Text style={styles.value}>OCR state: {status}</Text>
        {result ? <Text style={styles.value}>duration: {result.durationMs} ms</Text> : null}
        {result ? <Text style={styles.value}>text items: {result.items.length}</Text> : null}
        {result ? <Text style={styles.value}>PII proposals: {proposals.length}</Text> : null}
        {result ? (
          <Text style={styles.value}>
            id_field: {countsByType.id_field}; phone_field: {countsByType.phone_field};
            email_field: {countsByType.email_field}
          </Text>
        ) : null}
      </View>

      {result ? (
        <View style={styles.resultBox}>
          <Text style={styles.resultTitle}>Recognized text</Text>
          <Text style={styles.value}>{result.text || "(empty)"}</Text>
        </View>
      ) : null}

      {result ? (
        <View style={styles.diagnosticsBox}>
          <Text style={styles.resultTitle}>OCR item diagnostics</Text>
          <Text style={styles.diagnosticText}>
            {JSON.stringify(
              result.items.map((item, index) => ({
                index,
                text: item.text,
                bbox: item.bbox,
              })),
              null,
              2,
            )}
          </Text>
        </View>
      ) : null}

      {status === "error" ? (
        <View style={styles.errorBox}>
          <Text style={styles.resultTitle}>Local OCR error</Text>
          <Text style={styles.errorText}>{errorMessage}</Text>
        </View>
      ) : null}
    </View>
  );
}

function ProposalOverlay({
  proposal,
  imageSize,
  viewSize,
}: {
  proposal: PiiProposal;
  imageSize: Size;
  viewSize: Size;
}) {
  const box = mapImageBoxToContainedViewBox(proposal.bbox, imageSize, viewSize);

  if (!isVisibleBox(box)) {
    return null;
  }

  return (
    <View
      pointerEvents="none"
      style={[
        styles.overlayBox,
        {
          left: box.x,
          top: box.y,
          width: box.width,
          height: box.height,
        },
      ]}
    />
  );
}

function isVisibleBox(box: Box): boolean {
  return box.width > 0 && box.height > 0;
}

const styles = StyleSheet.create({
  section: {
    gap: 12,
  },
  sectionTitle: {
    color: "#111827",
    fontSize: 20,
    fontWeight: "700",
  },
  notice: {
    color: "#334155",
    fontSize: 15,
    lineHeight: 22,
  },
  switchRow: {
    gap: 10,
  },
  switchButton: {
    alignSelf: "stretch",
  },
  previewFrame: {
    alignSelf: "stretch",
    backgroundColor: "#ffffff",
    borderColor: "#cbd5e1",
    borderRadius: 6,
    borderWidth: 1,
    height: 320,
    overflow: "hidden",
  },
  previewImage: {
    height: "100%",
    width: "100%",
  },
  overlayBox: {
    backgroundColor: "rgba(220, 38, 38, 0.16)",
    borderColor: "#dc2626",
    borderWidth: 2,
    position: "absolute",
  },
  metricsBox: {
    backgroundColor: "#f1f5f9",
    borderColor: "#cbd5e1",
    borderRadius: 6,
    borderWidth: 1,
    gap: 4,
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
  diagnosticsBox: {
    backgroundColor: "#fff7ed",
    borderColor: "#fb923c",
    borderRadius: 6,
    borderWidth: 1,
    gap: 6,
    padding: 12,
  },
  diagnosticText: {
    color: "#111827",
    fontFamily: "monospace",
    fontSize: 12,
    lineHeight: 17,
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
  value: {
    color: "#111827",
    fontSize: 15,
    lineHeight: 21,
  },
  errorText: {
    color: "#b91c1c",
    fontSize: 15,
    lineHeight: 21,
  },
});
