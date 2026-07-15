# Contract Checker Mobile Android Tests

This Android-only mobile project now contains two intentionally separate test slices:

1. a local Hebrew OCR spike using Tesseract on the Android device;
2. the existing backend transport test using only a bundled synthetic redacted PNG.

The locally selected OCR image is never passed to the backend transport function.

## Android-only Tesseract OCR spike

The spike uses a local Expo native module backed by Tesseract4Android. It can:

- open the Android system document picker for one image;
- copy the selected image into the app cache;
- download the official `tessdata_best` Hebrew model once;
- run Hebrew OCR locally on the Android device;
- display raw text, elapsed time, decoded bitmap size, Tesseract mean confidence, and model file size.
- run the same selected image through controlled page segmentation mode variants.

The contract image is not uploaded. OCR output is not uploaded. The only network operation in this spike is an explicit model download from the official Tesseract repository:

```text
https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/main/heb.traineddata
```

The Best model is stored at:

```text
filesDir/tesseract/best/tessdata/heb.traineddata
```

The legacy Fast model location is not treated as an installed Best model:

```text
filesDir/tesseract/tessdata/heb.traineddata
```

After a successful Best download, the app safely deletes the legacy Fast model file if it exists.

This is an OCR feasibility test, not a privacy gate or legal-analysis implementation. It does not yet:

- detect or redact PII;
- detect handwriting or manual edits;
- guarantee reading order for RTL legal documents;
- verify OCR text against a gold transcription;
- send locally selected images or OCR output to any backend.

This Best-model OCR spike is not a legal-quality benchmark. There is no gold transcription yet, so OCR quality must still be reviewed manually.

Physical Samsung A55 testing confirmed that the Best model can be downloaded and used on-device. In the tested page, switching from the earlier Fast model to `tessdata_best` did not materially improve the OCR result, and deterministic 3x Lanczos upscale from 905 x 1280 to 2715 x 3840 produced effectively identical OCR output. That suggests image resolution is not the main current limitation.

The current experiment isolates Tesseract page segmentation behavior while keeping the model and image processing unchanged. Available modes:

- `Auto`: `TessBaseAPI.PageSegMode.PSM_AUTO`
- `Single column`: `TessBaseAPI.PageSegMode.PSM_SINGLE_COLUMN`
- `Single block`: `TessBaseAPI.PageSegMode.PSM_SINGLE_BLOCK`
- `Sparse text`: `TessBaseAPI.PageSegMode.PSM_SPARSE_TEXT`

All other OCR variables are intentionally unchanged, including the Best model path, bitmap decoding, image sampling, preprocessing behavior, `preserve_interword_spaces=1`, and absence of OCR post-processing.

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
2. Tap `Download Best Hebrew OCR model` and wait for the status to become `ready`.
3. Tap `Select one image from Android`.
4. Select the same clean 2715 x 3840 PNG for every run.
5. Run `Auto`.
6. Run `Single column`.
7. Run `Single block`.
8. Run `Sparse text`.
9. Confirm all four raw results remain visible at the same time.
10. Restart the app and verify that the Best model installation state and file size are still shown correctly.

For the first run, use a clean test page without filled personal details. The spike keeps the selected image in app-local cache, but PII detection and redaction have not been implemented yet.

Compare these metrics and observations across all four page segmentation modes:

- downloaded model file size;
- elapsed time;
- mean confidence;
- decoded bitmap width and height;
- raw OCR text;
- header and party-field reading order;
- word spacing and merged Hebrew words;
- clause numbering quality, especially `1.1` and `2.1.1`;
- mixed Hebrew/Latin text, for example `As-Is`.

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
