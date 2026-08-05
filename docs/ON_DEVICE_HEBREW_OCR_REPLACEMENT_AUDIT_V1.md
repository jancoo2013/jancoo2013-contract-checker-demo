# On-device Hebrew OCR replacement audit v1

Date: 2026-08-05

Status: architectural audit; no runtime integration.

## 1. Decision

The audited market does not contain a ready-made full-page Hebrew OCR engine that simultaneously satisfies all current MVP constraints:

- runs locally on Android;
- is realistic for Samsung A55-class hardware;
- does not upload the input image or OCR output;
- returns reliable text geometry;
- has a usable integration and licensing path;
- demonstrates Hebrew support suitable for real rental-contract photos.

Therefore the project must not replace Tesseract with another heavyweight full-page OCR package by name alone.

The only immediate bounded candidate is **Google ML Kit Text Recognition v2, Latin model**, and only for the four direct-value PII classes that are written primarily with digits and Latin characters:

- email;
- Israeli phone;
- checksum-valid Israeli ID;
- checksum-valid IL IBAN.

This is not a Hebrew OCR replacement. It is a narrow direct-value recognition experiment.

Names, Hebrew addresses, party fields, signatures, stamps and handwriting remain separate visual/privacy problems and are not solved by this candidate.

## 2. Hard admission gates

A candidate may enter an Android spike only when all applicable gates are supported by primary documentation:

| Gate | Requirement |
|---|---|
| Execution | inference on the Android device, not a remote service |
| Target hardware | plausible on Samsung A55 without server-class RAM/GPU |
| Privacy | raw image and recognized output are not uploaded |
| Geometry | word/element boxes or polygons are available |
| Language utility | Hebrew support, or demonstrated utility for direct digit/Latin PII |
| Integration | maintained Android API or a bounded custom-runtime path |
| Licensing | terms compatible with a consumer application and reviewable before release |

A model is not admitted merely because it is multilingual, open source, accurate on desktop benchmarks or theoretically convertible.

## 3. Candidate verdicts

### 3.1 Google ML Kit Text Recognition v2 — Latin model

**Verdict: GO for one direct-value-only Android spike. NO-GO for full Hebrew OCR.**

Primary evidence:

- official Android SDK with bundled and Google Play Services delivery paths;
- bundled Latin model adds about 4 MB per script architecture;
- documented as real-time on most devices for Latin script;
- returns blocks, lines, elements and symbols with bounding boxes/corner points and confidence;
- ML Kit terms state that input images and resultant outputs are processed fully on-device and are not sent to Google servers;
- supported scripts are Latin, Chinese, Devanagari, Japanese and Korean; Hebrew script is absent.

Why it remains useful:

Phone numbers, Israeli IDs, IBANs and most email addresses do not require Hebrew transcription. The existing deterministic class checks can consume recognized digit/Latin elements and preserve the current provenance and fail-closed rules.

Limits:

- no Hebrew marker recognition;
- no evidence yet that the Latin detector reliably extracts digit/Latin tokens from a dense mixed Hebrew page;
- Google may receive SDK performance/utilization metrics and may contact servers for updates; product disclosures must reflect the current ML Kit terms;
- success on the four direct classes would not prove complete PII coverage.

Sources:

- [ML Kit Text Recognition v2 for Android](https://developers.google.com/ml-kit/vision/text-recognition/v2/android)
- [ML Kit supported languages and scripts](https://developers.google.com/ml-kit/vision/text-recognition/v2/languages)
- [ML Kit Terms and Privacy](https://developers.google.com/ml-kit/terms)

### 3.2 Tesseract Hebrew (`fast` and full/best data)

**Verdict: FINAL NO-GO for the active MVP.**

Project evidence:

- both previously tested Hebrew model modes produced unusable real-photo output;
- the integrated target-device run produced mean confidence 38 and semantically meaningless text;
- later geometry and quality gates cannot repair missing recognition.

Do not spend another PR on PSM selection, confidence thresholds, overlay behavior or preprocessing intended to rescue Tesseract unless the product owner explicitly reopens the rejected path.

### 3.3 Surya

**Verdict: NO-GO for Samsung A55 on-device runtime.**

The official project describes the current OCR model as approximately 650M parameters and documents server/desktop-oriented inference through vLLM or llama.cpp. No maintained Android integration is supplied. Its accuracy is irrelevant when the deployment target is not viable.

Source:

- [Surya README](https://github.com/datalab-to/surya/blob/master/README.md)

### 3.4 PaddleOCR / PP-OCRv5 multilingual

**Verdict: NO-GO as an off-the-shelf Hebrew replacement.**

PaddleOCR has small multilingual recognition models and local deployment paths, but Hebrew is absent from the current official PP-OCRv5 multilingual language/model tables. Android feasibility without a Hebrew recognizer does not satisfy the product requirement.

Source:

- [PP-OCRv5 multilingual recognition](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.en.md)

### 3.5 EasyOCR

**Verdict: NO-GO.**

The maintained package is Python/PyTorch-oriented, has no supported Android product path, and Hebrew is still not available as a standard language model in the project. The public Hebrew request contains later confirmations that `he`, `heb` and `iw` do not work.

Sources:

- [EasyOCR repository](https://github.com/JaidedAI/EasyOCR)
- [Hebrew support issue](https://github.com/JaidedAI/EasyOCR/issues/363)

### 3.6 Custom model through ONNX Runtime Mobile or LiteRT

**Verdict: technically viable deployment substrate; HOLD as custom research, not an immediate replacement.**

ONNX Runtime officially supports Android packages, CPU inference, XNNPACK and NNAPI, and custom reduced runtimes. LiteRT also supports bundled custom models on Android. These runtimes solve deployment, not recognition: the project would still need to obtain or train a suitable detector/recognizer, export it, bound memory, validate RTL order and build a held-out privacy evaluation.

This path becomes active only if the ML Kit direct-value spike fails or if the unresolved Hebrew-name/address/signature classes require a project-owned model.

Sources:

- [ONNX Runtime Mobile](https://onnxruntime.ai/docs/tutorials/mobile/)
- [LiteRT Android support](https://ai.google.dev/edge/litert/android/metadata/lite_support)

## 4. Architecture consequence

The local privacy layer is not a full Hebrew transcription engine.

The near-term architecture becomes:

```text
raw phone photo
→ local Latin/digit element recognition with geometry
→ deterministic direct-value PII checks
→ separate visual evidence paths for Hebrew fields, names, addresses, signatures and handwriting
→ conservative irreversible local masks
→ local privacy validation
→ anonymized derivative only
→ approved external full Hebrew OCR
```

This preserves the existing product contract: full Hebrew OCR occurs only after the image is irreversibly anonymized.

## 5. Single next step

`android-mlkit-latin-direct-pii-spike-v1`

Bounded scope:

1. Add the bundled ML Kit Latin recognizer to the development Android path.
2. Run it locally on the same selected photo used for the failed Tesseract test.
3. Convert only digit/Latin elements and their geometry into the existing direct-value candidate contract.
4. Preserve the current checksum, provenance, class-compatibility and fail-closed rules.
5. Show a development overlay for the four direct classes only.
6. Do not add Hebrew marker inference, production masks, external handoff or a Tesseract fallback.

Target-device go criteria:

- no crash or out-of-memory condition on Samsung A55;
- element geometry aligns with the original image;
- clearly visible supported direct values are recognized exactly enough to pass their deterministic validators;
- ordinary amounts, dates and clause numbers do not obtain direct-value mask authorization;
- raw image and recognized values remain local;
- latency, model availability and candidate counts are recorded without exporting PII.

No-go consequence:

If the Latin model cannot reliably recover the four direct-value classes from real mixed Hebrew contract pages, stop searching for interchangeable off-the-shelf OCR engines. The next architectural decision must be a custom, narrow detector/recognizer through ONNX Runtime Mobile or LiteRT, or a product-level change to the privacy workflow.

## 6. Explicit exclusions

This audit does not:

- claim that ML Kit reads Hebrew;
- claim complete PII coverage;
- reactivate full local OCR, CRNN training or CER work;
- authorize production masking;
- connect Gemini, cloud OCR or any external image API;
- add an Android dependency or change runtime behavior;
- send or store real contract images or PII in GitHub.
