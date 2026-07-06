# On-Device OCR Spike

This spike tests Android-only local OCR over bundled synthetic Hebrew PNG assets.

It does not add camera, gallery, document picker, PDF import, scanner UI, backend calls, Gemini image calls, telemetry, or runtime model download.

## Primary Sources

- Google ML Kit Text Recognition v2 supported languages: https://developers.google.com/ml-kit/vision/text-recognition/v2/languages
- Google ML Kit Text Recognition v2 Android docs: https://developers.google.com/ml-kit/vision/text-recognition/v2/android
- Tesseract4Android repository and usage docs: https://github.com/adaptech-cz/Tesseract4Android
- Tesseract4Android `TessBaseAPI` / iterator source: https://github.com/adaptech-cz/Tesseract4Android/tree/master/tesseract4android/src/main/java/com/googlecode/tesseract/android
- Official Tesseract `tessdata_fast`: https://github.com/tesseract-ocr/tessdata_fast

## Candidates

| Candidate | Primary source check | Decision | Reason |
| --- | --- | --- | --- |
| Google ML Kit Text Recognition v2 | Official supported-language table lists Latin plus separate Chinese, Devanagari, Japanese, and Korean script recognizers. Hebrew is not listed in the supported, experimental, or mapped language sections. | Rejected | The current primary docs do not explicitly confirm Hebrew support, so this task treats it as not viable for Hebrew OCR. |
| Tesseract4Android + Tesseract `heb.traineddata` | Tesseract4Android documents Android usage with `TessBaseAPI`, APK asset extraction into app-private files, and a result iterator with word-level bounding boxes. Official `tessdata_fast` includes `heb.traineddata`. | Selected | Offline Android OCR, bundled Hebrew model, no runtime model download, word text plus original-image coordinates available. |
| React Native / Expo ML Kit wrappers | Wrappers ultimately rely on the underlying ML Kit language support. | Rejected | Without explicit current ML Kit Hebrew support in primary docs, a wrapper does not satisfy the Hebrew/offline/boxes requirement. |

## Selected Stack

- Android native local Expo module: `mobile/modules/local-ocr`.
- OCR engine: `cz.adaptech.tesseract4android:tesseract4android:4.9.0`.
- Model: official Tesseract `tessdata_fast/heb.traineddata`.
- Pinned source ref: `tesseract-ocr/tessdata_fast@87416418657359cb625c412a48b6e1d6d41c29bd`.
- Bundled asset path: `mobile/modules/local-ocr/android/src/main/assets/tessdata/heb.traineddata`.
- SHA-256: `11F9E43AB227F786352A50F75C94C2E9906F1BABA86D93276DA19DA7CE0904DB`.
- Size: `961404` bytes.
- License note: `tessdata_fast` data is documented as Apache-2.0.

The module copies `heb.traineddata` from APK assets into `context.filesDir/local_ocr_tesseract/tessdata/` when needed. That is app-private internal storage. The app does not use shared or external storage for OCR data.

## Synthetic Assets

- `mobile/assets/synthetic-hebrew-pii.png`: Hebrew synthetic test page with a 9-digit ID-like value, Israeli-phone-like value, `.invalid` email, and `SYNTHETIC_TEST_IMAGE_ONLY` marker.
- `mobile/assets/synthetic-hebrew-layout.png`: Hebrew synthetic layout page with numbered clauses and a small table-like region.

These are not user documents.

## Candidate Detection

The React Native layer groups OCR word items into approximate lines, runs deterministic local regex checks, and draws candidate overlays from the union of participating word boxes:

- `id_like`
- `phone_like`
- `email_like`

Out of scope for this spike:

- names;
- addresses;
- signatures;
- handwriting;
- contextual PII;
- production privacy decisions.

## Local-Only Boundary

The `Run local OCR` action:

- does not call `fetch`;
- does not call the backend;
- does not call Gemini;
- does not upload images or OCR text;
- does not download OCR models;
- does not emit telemetry;
- stores recent OCR output only in React component state.

The existing `Send synthetic redacted PNG` transport test remains separate and unchanged.

## Unresolved Risks

- OCR quality on real Israeli lease photos is not proven by synthetic assets.
- Hebrew rendering in these synthetic PNGs is sufficient for glyph coverage, but not a substitute for real layout testing.
- No real-device RAM measurement is included. This PR records image dimensions, asset sizes, OCR duration, item count, and candidate count only.
- Android native compile and physical-device behavior must be checked before treating this as a production direction.

## Manual Offline Check

After installing a development build on a physical Android device:

1. Open the app once if the development build needs initial setup.
2. Enable airplane mode.
3. Force close and reopen the app.
4. Run `Local OCR Experiment` on each bundled synthetic image.
5. Verify that OCR text, item count, candidate counts, duration, and overlays appear without network access.

Only record this as passed after it has actually been run on a device.
