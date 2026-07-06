# Contract Checker Mobile Transport Test

This is the first Android-first mobile transport slice for the contract checker backend.

This build uses a bundled synthetic test image only.

It does not include camera, gallery picker, or document-picker UI or packages.

Do not use real contracts with this transport-test build.

## Local OCR Experiment

The app includes an Android-only on-device OCR research block called `Local OCR Experiment`.

It uses only bundled synthetic Hebrew PNG assets:

- `assets/synthetic-hebrew-pii.png`;
- `assets/synthetic-hebrew-layout.png`.

Tap `Run local OCR` to run the local OCR module. The block shows:

- OCR state;
- local OCR run duration in milliseconds;
- recognized text;
- OCR text item count;
- deterministic local PII candidate count;
- counts for `id_like`, `phone_like`, and `email_like`;
- red overlay rectangles for detected candidates.

This block does not use camera, gallery, document picker, backend calls, Gemini calls, model downloads, or telemetry. It is not production OCR and must not be tested with real contracts.

The selected OCR stack and tradeoffs are documented in `docs/on-device-ocr-spike.md`.

`durationMs` is the local run duration for bitmap decode, Tesseract API setup/init, OCR, and iterator extraction. It does not include the first app-private `heb.traineddata` copy, because that happens before the timer starts.

### Offline OCR Checks

Test A checks only that the local OCR call does not need network during a Metro-backed development session:

1. Start Metro.
2. Open the development build.
3. Wait until the app UI is loaded.
4. Enable airplane mode.
5. Keep the app open.
6. Tap `Run local OCR`.
7. Confirm that text, item counts, candidate counts, duration, and overlays appear.

Test B checks cold-start offline behavior and should be run only with an installed build that has an embedded JS bundle or standalone-like packaging:

1. Install the embedded-bundle build.
2. Enable airplane mode.
3. Force close and reopen the app.
4. Run `Local OCR Experiment` on both bundled synthetic images.
5. Confirm that text, item counts, candidate counts, duration, and overlays appear without network access.

Do not claim this check has passed until it has actually been run on a device.

The app config explicitly adds no Android permissions and disables Android backup with `allowBackup: false`. A local Expo prebuild inspection generated `android.permission.INTERNET`, `android.permission.VIBRATE`, and `android.permission.SYSTEM_ALERT_WINDOW`. Legacy `READ_EXTERNAL_STORAGE` and `WRITE_EXTERNAL_STORAGE` entries are blocked with `tools:node="remove"`. No `CAMERA`, `READ_MEDIA_IMAGES`, `RECORD_AUDIO`, location, or contacts permission was present. The generated native `android/` directory is not committed.

## Requirements

- Node.js LTS.
- A local FastAPI backend from this repository.
- Android development environment for `expo run:android`.

## Install

```bash
npm install
```

After `package-lock.json` is present, use the reproducible install path:

```bash
npm ci
```

## Configure Backend URL

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

## Run The Backend Locally

From the repository root, start FastAPI on all interfaces so an emulator or phone can reach it:

```bash
uvicorn contract_checker.api_app:app --host 0.0.0.0 --port 8000
```

For a local startup/import check on the development machine, binding to localhost is enough:

```bash
uvicorn contract_checker.api_app:app --host 127.0.0.1 --port 8000
```

The mobile screen posts to:

```text
POST /v1/contracts/analyze-redacted
```

## Run Mobile

From `mobile/`:

```bash
npm run android
```

For an already installed development build, start Metro with:

```bash
npm run start
```

## Test The Transport Slice

1. Open the app.
2. Confirm the backend API URL is configured.
3. Confirm the synthetic asset name is `synthetic_page.png`.
4. Tap `Send synthetic redacted PNG`.

The app sends a multipart request with:

- `pages`: bundled synthetic PNG;
- `privacy_review_confirmed`: `true`;
- `client_request_id`: a generated smoke-test identifier.

Expected result: the screen shows a minimal safe response summary with request status, OCR quality status, text usability, risk profile, risk profile summary, and evidence warning count.

Android emulator or physical-device validation should be reported separately when it has actually been run.
