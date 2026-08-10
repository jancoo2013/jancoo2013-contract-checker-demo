# Android Document Geometry Validation v1

Status: bounded device-validation gate inserted by product-owner decision before `serverless-gpu-ocr-viability-benchmark-v1`.

This validation does not reopen or modify the frozen Python geometry baseline. Its purpose is to verify that a bounded Android deskew implementation behaves acceptably on the target Samsung A55 before remote OCR work begins.

## 1. Scope

The device-validation slice is deliberately narrower than the complete frozen geometry block:

```text
local Android image
→ bounded local decode + EXIF orientation
→ bounded grayscale preview
→ local-contrast text/ink mask
→ bounded text-angle estimate
→ meaningful source-edge deskew-loss guard
→ full-resolution deskew in the original frame when accepted
→ otherwise full-frame fallback
```

No crop is applied by the Android validation runtime in this gate. Crop behavior remains frozen in the Python reference and is not reimplemented merely for this phone check.

## 2. Two bounded implementation PRs

To keep the normal 400-line implementation limit:

1. PR #211 — `android-document-deskew-validation-runtime-v1`
   - local Expo/Kotlin module only;
   - no user-facing entry change yet;
   - no OCR call, upload, backend, provider, or new dependency.
2. `android-document-geometry-validation-ui-v1`
   - thin dev UI and validation entry using the runtime from PR #211;
   - source/result preview, angle, decision, confidence, elapsed time and rejection reasons;
   - no geometry-algorithm expansion.

After the UI PR is merged, run the manual Samsung A55 validation in section 6. The serverless GPU OCR benchmark stays blocked until that device run is recorded.

## 3. Android runtime contract

The runtime is local-only and accepts only a local file URI already materialized in app cache by the existing Android picker.

Bounds:

- maximum input file size: 64 MiB;
- maximum source long side: 8192 px;
- maximum decoded source pixels for this dev harness: 16,000,000;
- preview long side: 1800 px;
- angle-analysis long side: 900 px;
- angle search: -12° through +12° in 1° steps;
- accepted estimate keeps the frozen confidence/projection/peak thresholds;
- a search-limit result is rejected;
- meaningful source-edge loss blocks physical deskew;
- rejected/unsafe results return full-frame fallback with zero applied rotation.

The 16 MP Android cap is intentionally stricter than the frozen Python 32 MP research contract. It is a device-validation memory guard, not a change to the frozen product geometry contract. For Samsung A55 testing, use the ordinary camera resolution rather than 50 MP mode.

The native result exposes only value-free geometry diagnostics and a local output URI. It does not expose text or OCR results.

## 4. Intentional implementation differences from the Python reference

This is a behavioral mobile port, not a bit-for-bit Pillow port.

- Python local background: Pillow `GaussianBlur`.
- Android validation local background: three bounded separable box-blur passes approximating the same low-frequency background role.
- Python physical rotation: Pillow BICUBIC.
- Android validation physical rotation: Android filtered `Canvas` rotation.
- Python frozen block may crop after all bounds checks.
- Android validation gate performs deskew only and keeps the full frame.

Therefore the validation asks whether the Android implementation is visually and operationally useful on real phone photographs. It does not claim pixel-identical parity with the Python research reference.

A systematic Android/Python behavioral mismatch may justify a bounded Android-port correction. It does not automatically invalidate the frozen Python crop/geometry contract unless the evidence satisfies the reopen criteria in `docs/DOCUMENT_GEOMETRY_FREEZE_CRITERIA_V1.md`.

## 5. Privacy and security boundary

For this device-validation gate:

- selected images stay on the phone;
- input is copied only into app-local cache by the existing picker;
- deskew output is written only to app-local cache;
- the previous deskew output is deleted before a new result is saved;
- no OCR model is invoked;
- no contract image or derived image is uploaded;
- no backend request is made;
- no Gemini/LLM call is made;
- no image pixels, filenames, URIs, or document contents are logged by the new module;
- no new network destination, dependency, Android permission, or provider capability is introduced.

The existing mobile repository still contains older test/spike code, but the dedicated validation UI must not invoke those network/OCR paths during this gate.

## 6. Samsung A55 manual validation set

Use owner-controlled photographs on the device. They may contain real contract material because processing remains local, but do not publish screenshots, logs, images, filenames, or artifacts containing PII to GitHub/CI.

Minimum visual set:

1. approximately 0° page;
2. approximately +3° and -3°;
3. approximately +7° and -7°;
4. approximately +10° and -10°;
5. page with text reasonably close to an edge;
6. sparse/signature-style page;
7. at least two different capture distances;
8. at least two ordinary indoor lighting conditions.

Do not manufacture ever-smaller adversarial marks for this device gate. The frozen meaningful-content contract remains the stop rule.

## 7. Pass/fail criteria

PASS for this gate requires all of the following on the target phone:

- APK installs and launches;
- local image selection succeeds;
- no crash/OOM on the ordinary-resolution validation set;
- approximately horizontal pages remain stable rather than receiving a large false rotation;
- clear ±3°/±7°/±10° examples are generally corrected in the expected direction;
- accepted results look materially straighter by visual inspection;
- uncertain cases may fall back to the original full frame;
- meaningful source-edge loss must not be converted into an applied physical rotation;
- no visible 90°/180° EXIF-orientation mistake appears;
- no evidence appears that the selected image left the device through this validation flow.

The goal is not perfect angle recovery to a fraction of a degree. The product criterion is a visibly useful, conservative deskew that prefers fallback over a destructive transform.

FAIL/reopen requires a concrete reproducible device case such as a systematic wrong-direction rotation, large false rotation on a level page, repeated failure on ordinary ±3°–10° pages, EXIF orientation error, crash/OOM within the documented bounds, or meaningful edge content being physically clipped despite the guard.

## 8. Evidence to record after the device run

Record only non-sensitive facts in repository state:

- device model and Android major version;
- APK/final commit SHA tested;
- count of validation photos;
- counts of accepted deskew, full-frame fallback, runtime error/crash;
- approximate angle buckets tested;
- qualitative pass/fail summary without document contents;
- any concrete reproducible defect described without PII.

Do not commit the photographs, screenshots, raw logs, output images, or recoverable contract data.

## 9. Next-step rule

Until the Samsung A55 run is recorded as acceptable, do not start `serverless-gpu-ocr-viability-benchmark-v1`.

After an acceptable device-validation result is recorded and the temporary validation UI/entry is no longer needed, restore the normal mobile entry in the bounded state/cleanup step and return the canonical next step to `serverless-gpu-ocr-viability-benchmark-v1`.
