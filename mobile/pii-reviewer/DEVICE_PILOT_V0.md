# Android Reviewer APK Handoff v0

This file defines only the handoff boundary for the debug APK produced by the `Mobile reviewer` workflow.

## Artifact

Use the artifact named `pii-reviewer-debug-<git-sha>` from the workflow run for the exact merged `main` commit under test.

The artifact contains:

```text
pii-reviewer-debug.apk
build-identity.json
```

Before transfer, verify that the APK SHA-256 equals `apk_sha256` in `build-identity.json` and that `git_sha` identifies the intended commit.

## Deferred work

This PR does not install the APK, prepare a real review pack, run the Samsung A55 smoke, perform human review, or produce privacy metrics. Those are separate repository-external steps after merge.

Real pages, PII, review packs, screenshots, and reviewer results must not be committed to GitHub.
