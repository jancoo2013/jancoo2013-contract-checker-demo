# Android Reviewer Device Pilot v0

This runbook covers the repository-owned part of `android-reviewer-device-pilot-v0`: obtaining an installable debug APK, verifying its identity, installing it on Samsung A55, and running the bounded offline device smoke. Real pages, review packs, and review results remain outside GitHub.

## 1. Approved artifact

Use the `Mobile reviewer` GitHub Actions run for the exact merged `main` commit being tested.

Download the artifact named:

```text
pii-reviewer-debug-<git-sha>
```

It contains:

```text
pii-reviewer-debug.apk
build-identity.json
```

`build-identity.json` records the application ID, version, exact Git commit, workflow run identity, and APK SHA-256. Do not use an APK whose recorded commit is not the intended merged `main` commit.

On Windows, verify the downloaded APK before transferring it to the phone:

```powershell
Get-FileHash .\pii-reviewer-debug.apk -Algorithm SHA256
```

The result must equal `apk_sha256` in `build-identity.json`.

## 2. Install on Samsung A55

1. Transfer `pii-reviewer-debug.apk` to the phone without uploading the review pack to any cloud service.
2. Open the APK from Samsung My Files.
3. If Android asks, allow **Install unknown apps** only for the file-opening application used for this installation.
4. Install `PII Reviewer`.
5. If Android reports an incompatible signature from an older debug build, uninstall the older `PII Reviewer` and install this APK again. Debug artifacts are not production-upgrade packages.
6. Do not grant unrelated permissions.

Record outside the repository:

- APK Git SHA and APK SHA-256;
- GitHub Actions run ID and attempt;
- device model;
- Android version;
- installation result and any exact operational error category, without contract text or PII.

## 3. Repository-external review pack

The selected local directory must contain:

```text
predictions.jsonl
renderer/manifest.jsonl
line_segmentation/manifest.jsonl
<source image paths referenced by predictions.jsonl>
<renderer derivative paths referenced by renderer/manifest.jsonl>
```

The app verifies closed schemas, relative paths, SHA-256 bindings, image dimensions, grayscale derivatives, page order, candidate masks, and neutral line regions before displaying a page.

The pack must be generated from the existing Python baseline, renderer, and line-segmentation contracts. Do not place real pages, manifests containing PII values, or reviewer output in GitHub.

Transfer the complete directory to local phone storage before the offline smoke.

## 4. Offline device smoke

After the APK and review pack are already on the phone, enable airplane mode and keep Wi-Fi disabled.

Verify, in order:

1. The application launches without a development server.
2. **Выбрать review pack** opens the Android directory picker.
3. Selecting the prepared directory reports the expected page count.
4. Every page renders without an operational error.
5. **Исходник** and **После масок** show the correct source and derivative for the same page.
6. Page navigation preserves prior page status and findings.
7. `missed_pii` binds a tap to a neutral line region.
8. `incomplete_mask` and `over_redaction` bind a tap to an existing mask candidate.
9. **Отменить отметку** removes only the latest finding on the current page.
10. **Страница чистая** is unavailable after a finding exists on that page.
11. **Сохранить результат** remains unavailable until every page is closed.
12. The completed review creates exactly one file named `review-<prediction-sha>.jsonl` in the selected directory.
13. A second save to the same output path fails instead of overwriting the first result.

Operational failures are recorded by category and step only. Do not copy page text, names, identifiers, addresses, signatures, or screenshots containing PII into GitHub issues or PRs.

## 5. Human pilot boundary

The Hebrew-capable reviewer marks only:

- `missed_pii`;
- `incomplete_mask`;
- `over_redaction`;
- page `pass`.

The reviewer does not transcribe the contract, draw bounding boxes, correct masks, judge legal safety, or preserve PII values in notes.

## 6. Completion boundary

This step is complete only after the exact APK identity, Samsung A55/Android identity, prediction-manifest SHA-256, reviewed page count, save/no-overwrite result, and operational failures are recorded outside GitHub without PII.

Building the APK alone does not prove device behavior, detector recall, mask completeness, acceptable over-redaction, external-transfer safety, or production privacy safety.
