# Contract Checker Mobile Android Tests

This Android-only mobile project now contains two intentionally separate test slices:

1. a local Hebrew OCR spike using Tesseract on the Android device;
2. the existing backend transport test using only a bundled synthetic redacted PNG.

The locally selected OCR image is never passed to the backend transport function.

## Android-only Tesseract OCR spike

The spike uses a local Expo native module backed by Tesseract4Android. It can:

- open the Android system document picker for one image;
- copy the selected image into the app cache;
- download the official `tessdata_fast` and `tessdata_best` Hebrew models separately;
- run Hebrew OCR locally on the Android device;
- display raw text, elapsed time, decoded bitmap size, Tesseract mean confidence, selected model variant, and model file size.

The contract image is not uploaded. OCR output is not uploaded. The only network operations in this spike are explicit model downloads from the official Tesseract repositories:

- Fast: `https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/heb.traineddata`
- Best: `https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/main/heb.traineddata`

The two models are stored independently on device. The Fast model keeps compatibility with the original legacy path used by the first Android OCR spike, so an already downloaded Fast model should not need to be downloaded again.

This is an OCR feasibility test, not a privacy gate or legal-analysis implementation. It does not yet:

- detect or redact PII;
- detect handwriting or manual edits;
- guarantee reading order for RTL legal documents;
- verify OCR text against a gold transcription;
- send locally selected images or OCR output to any backend.

The Fast versus Best comparison is not a legal-quality benchmark. There is no gold transcription yet, so the comparison is manual and observational.

## Requirements

- Node.js LTS.
- Android Studio and an Android SDK suitable for `expo run:android`.
- A physical Android device or emulator.
- A local FastAPI backend only when testing the separate transport slice.

## Install

From `mobile/`:

```bash
npm ci
```

The native `android/` directory is generated and remains outside version control. Regenerate it so Expo discovers the local Tesseract module and applies the JitPack repository config plugin:

```bash
npx expo prebuild --clean --platform android
```

Then build and install the development app:

```bash
npm run android
```

Native module changes require rebuilding the Android app; restarting Metro alone is not enough.

## Test local Hebrew OCR

1. Open the app on Android.
2. Download both `Fast` and `Best` models and wait for both statuses to become `ready`.
3. Tap `Select one image from Android`.
4. Select one clean Hebrew rental-contract page.
5. Select `Fast` and tap `Run Fast OCR on device`.
6. Select `Best` and tap `Run Best OCR on device` without reselecting the image.
7. Compare the two raw outputs on the same selected image.

For the first run, use a clean test page without filled personal details. The spike keeps the selected image in app-local cache, but PII detection and redaction have not been implemented yet.

Record these metrics and observations for each model:

- model variant;
- downloaded model file size;
- elapsed time;
- mean confidence;
- decoded bitmap width and height;
- raw OCR text;
- word spacing and merged Hebrew words;
- clause numbering quality;
- reading order in headers and party details;
- mixed Hebrew/Latin text, for example `As-Is`.

After running both models, restart the app and verify that both installation states and file sizes are still shown correctly. The same image should be reused for the Fast and Best runs within one app session.

## Configure backend transport URL

Create `mobile/.env` from `.env.example` and set:

```bash
EXPO_PUBLIC_API_BASE_URL=http://192.168.1.100:8000
```

Use only the backend URL here. Do not put Gemini API keys, provider tokens, or other secrets in the mobile app.

For an Android emulator, the host machine is usually reachable as:

```bash
EXPO_PUBLIC_API_BASE_URL=http://10.0.2.2:8000
```

For a physical Android device, use the LAN IP address of the computer running FastAPI, for example:

```bash
EXPO_PUBLIC_API_BASE_URL=http://192.168.1.100:8000
```

These local HTTP URLs are for development and debug testing only. Production or release deployment should use HTTPS.

## Run the backend locally

From the repository root, start FastAPI on all interfaces so an emulator or phone can reach it:

```bash
uvicorn contract_checker.api_app:app --host 0.0.0.0 --port 8000
```

For a local startup/import check on the development machine, binding to localhost is enough:

```bash
uvicorn contract_checker.api_app:app --host 127.0.0.1 --port 8000
```

The transport test posts to:

```text
POST /v1/contracts/analyze-redacted
```

## Test the existing transport slice

1. Confirm the backend API URL is configured.
2. Confirm the synthetic asset name is `synthetic_page.png`.
3. Tap `Send synthetic redacted PNG`.

The app sends a multipart request with:

- `pages`: bundled synthetic PNG;
- `privacy_review_confirmed`: `true`;
- `client_request_id`: a generated smoke-test identifier.

The transport button never uses the image selected for local Tesseract OCR.

Expected result: the screen shows a minimal safe response summary with request status, OCR quality status, text usability, risk profile, risk profile summary, and evidence warning count.

Android emulator or physical-device validation should be reported separately when it has actually been run.
