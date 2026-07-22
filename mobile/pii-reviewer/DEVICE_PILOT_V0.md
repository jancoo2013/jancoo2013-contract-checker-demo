# Android Reviewer Standalone APK Handoff v0

This file defines only the handoff boundary for the release-variant standalone APK produced by the `Mobile reviewer` workflow.

## Artifact

Use the artifact named `pii-reviewer-standalone-<git-sha>` from the workflow run for the exact merged `main` commit under test.

The artifact contains:

```text
pii-reviewer-standalone.apk
build-identity.json
```

Before transfer, verify that:

- the APK SHA-256 equals `apk_sha256` in `build-identity.json`;
- `git_sha` identifies the intended commit;
- `artifact_kind` is `standalone_pilot_apk`;
- `build_variant` is `release`.

A debug artifact that opens the Expo Development Build launcher is not valid for the offline pilot.

## Deferred work

This PR does not install the APK, prepare a real review pack, run the Samsung A55 smoke, perform human review, or produce privacy metrics. Those are separate repository-external steps after merge.

Real pages, PII, review packs, screenshots, and reviewer results must not be committed to GitHub.
