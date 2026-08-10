import { StatusBar } from "expo-status-bar";
import React, { useState } from "react";
import { Button, Image, SafeAreaView, ScrollView, StyleSheet, Text, View } from "react-native";

import DocumentDeskewValidation, {
  type DeskewValidationResult,
} from "../modules/document-deskew-validation";
import TesseractOcr, { type PickedImage } from "../modules/tesseract-ocr";

type RunState =
  | { status: "idle" }
  | { status: "running" }
  | { status: "success"; result: DeskewValidationResult }
  | { status: "error"; message: string };

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error || "Unknown error");
}

export default function GeometryValidationScreen() {
  const [image, setImage] = useState<PickedImage>();
  const [run, setRun] = useState<RunState>({ status: "idle" });

  async function pick() {
    try {
      const picked = await TesseractOcr.pickImageAsync();
      if (picked.canceled) return;
      if (!picked.uri) throw new Error("Android returned no local image URI.");
      setImage(picked);
      setRun({ status: "idle" });
    } catch (error: unknown) {
      setRun({ status: "error", message: message(error) });
    }
  }

  async function normalize() {
    if (!image?.uri) return;
    setRun({ status: "running" });
    try {
      setRun({ status: "success", result: await DocumentDeskewValidation.normalizeAsync(image.uri) });
    } catch (error: unknown) {
      setRun({ status: "error", message: message(error) });
    }
  }

  const result = run.status === "success" ? run.result : undefined;
  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Document deskew · device validation</Text>
        <Text style={styles.notice}>
          Локальный dev-harness. Фото остаётся на телефоне: OCR, upload и backend здесь не вызываются.
        </Text>
        <Button title="Выбрать фото договора" onPress={pick} disabled={run.status === "running"} />
        {image?.uri ? (
          <View style={styles.card}>
            <Text style={styles.label}>Исходник</Text>
            <Text style={styles.meta}>{image.width ?? "?"} × {image.height ?? "?"}</Text>
            <Image source={{ uri: image.uri }} resizeMode="contain" style={styles.image} />
          </View>
        ) : null}
        <Button
          title={run.status === "running" ? "Выравнивание…" : "Проверить выравнивание"}
          onPress={normalize}
          disabled={!image?.uri || run.status === "running"}
        />
        {result ? (
          <>
            <View style={styles.card}>
              <Text style={styles.label}>Результат</Text>
              <Image source={{ uri: result.outputUri }} resizeMode="contain" style={styles.image} />
            </View>
            <View style={styles.metrics}>
              <Text>decision: {result.decision}</Text>
              <Text>angle: {result.dominantTextAngleDegrees}°</Text>
              <Text>deskew: {result.rotationAppliedDegrees}°</Text>
              <Text>confidence: {result.confidence}</Text>
              <Text>preview: {result.previewWidth} × {result.previewHeight}</Text>
              <Text>elapsed: {result.elapsedMs} ms</Text>
              <Text>reasons: {result.rejectionReasons.join(", ") || "—"}</Text>
            </View>
          </>
        ) : null}
        {run.status === "error" ? <Text style={styles.error}>{run.message}</Text> : null}
        <Text style={styles.hint}>
          Для проверки снимайте ровный лист и наклоны примерно ±3°, ±7° и ±10°. Если алгоритм не уверен, full_frame_fallback — нормальный результат.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 18, gap: 14 },
  title: { fontSize: 23, fontWeight: "700", color: "#111827" },
  notice: { color: "#334155", lineHeight: 21 },
  card: { gap: 6, padding: 10, borderWidth: 1, borderColor: "#cbd5e1", borderRadius: 8, backgroundColor: "#fff" },
  label: { fontWeight: "700" },
  meta: { color: "#64748b" },
  image: { width: "100%", height: 320, backgroundColor: "#f1f5f9" },
  metrics: { gap: 4, padding: 10, backgroundColor: "#eef2ff", borderRadius: 8 },
  hint: { color: "#64748b", lineHeight: 20 },
  error: { color: "#b91c1c" },
});
