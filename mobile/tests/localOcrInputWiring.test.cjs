const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.join(__dirname, "..");
const experimentSource = fs.readFileSync(
  path.join(repoRoot, "src", "LocalOcrExperiment.tsx"),
  "utf8",
);
const bridgeSource = fs.readFileSync(
  path.join(repoRoot, "modules", "local-ocr", "src", "index.ts"),
  "utf8",
);
const nativeSource = fs.readFileSync(
  path.join(
    repoRoot,
    "modules",
    "local-ocr",
    "android",
    "src",
    "main",
    "java",
    "com",
    "jancoo",
    "contractchecker",
    "localocr",
    "LocalOcrModule.kt",
  ),
  "utf8",
);

test("wires local image picker into the existing local OCR experiment", () => {
  assert.match(bridgeSource, /pickLocalImage\(\): Promise<LocalImagePickResult \| null>/);
  assert.match(bridgeSource, /recognizeLocalImageUri\(uri: string\): Promise<LocalOcrResult>/);
  assert.match(experimentSource, /LocalOcr\.pickLocalImage\(\)/);
  assert.match(experimentSource, /LocalOcr\.recognizeLocalImageUri\(localImage\.uri\)/);
  assert.match(experimentSource, /detectPiiProposals\(result\.items/);
  assert.match(experimentSource, /mapImageBoxToContainedViewBox\(proposal\.bbox/);
});

test("keeps bundled synthetic image OCR flow available", () => {
  assert.match(experimentSource, /SYNTHETIC_IMAGES/);
  assert.match(experimentSource, /recognizeBundledImage\(selectedImage\.assetName\)/);
  assert.match(nativeSource, /recognizeBundledImage/);
  assert.match(nativeSource, /synthetic-hebrew-pii-large\.png/);
});

test("native local image OCR rejects remote URI schemes", () => {
  assert.match(nativeSource, /scheme == "http" \|\| scheme == "https"/);
  assert.match(nativeSource, /Remote image URI schemes are not supported/);
  assert.match(nativeSource, /scheme == "content" \|\| scheme == "file"/);
});

test("local OCR input path does not introduce fetch upload or cloud calls", () => {
  const combinedSource = [experimentSource, bridgeSource, nativeSource].join("\n");

  for (const forbidden of [/fetch\s*\(/, /XMLHttpRequest/, /new\s+FormData/, /upload\s*\(/i]) {
    assert.equal(
      forbidden.test(combinedSource),
      false,
      `unexpected forbidden call in local OCR input path: ${forbidden}`,
    );
  }
});
