# Local PII redaction and OCR handoff pipeline

Status: active product contract. Read together with `docs/ARCHITECTURE.md`. The current implementation status, blockers, continuity rules, and single next step are recorded in `docs/OCR_PROJECT_STATE.md`.

This file records the image-processing direction chosen for the MVP so that later work does not silently turn the local privacy component into a general-purpose Hebrew OCR project.

## Non-negotiable decisions

1. The local mobile component exists to detect and irreversibly mask likely PII regions before any image or document leaves the device.
2. Raw contract photos, recoverable PII, and unredacted OCR text never go to an external OCR or LLM service.
3. After the local privacy boundary is passed, an approved external OCR/LLM service may receive only the anonymized image/document.
4. The MVP does not require exact local transcription of every Hebrew line, clause number, punctuation mark, or mixed-script token.
5. Hebrew labels such as `ת.ז.` and other markers are detection signals, not a requirement to produce a complete local transcript.
6. The primary quality goals are PII-region recall, complete mask coverage, and bounded over-redaction of legally relevant content. Full-line CER is not the MVP privacy metric.
7. Human verification, when used, checks whether PII was missed or incompletely covered and whether important legal text was unnecessarily destroyed. It does not require full Hebrew transcription.
8. Page geometry, bounded decoding, provenance, fail-closed validation, and atomic publication remain required where they support the privacy pipeline.
9. The existing project-owned recognizer, CTC, synthetic-data, Gold, and CER work is preserved as paused research. It is not deleted, but it is not the active MVP path.
10. Reactivating full local OCR requires an explicit product-owner decision and updates to this file, `docs/ARCHITECTURE.md`, and `docs/OCR_PROJECT_STATE.md` in the same PR.

## Product runtime pipeline

```text
raw phone photo
→ on-device geometric and image preprocessing
→ on-device PII-region detection
→ irreversible local masks with explicit reasons/statuses
→ local fail-closed privacy validation
→ anonymized image/document
→ approved external full OCR
→ secondary text redaction
→ evidence blocks
→ legal-risk analysis
→ Russian report
```

The local privacy layer may use layout, known page zones, Hebrew field markers, digit patterns, signatures, handwriting cues, and conservative region expansion. It must not depend on exact full-page transcription to decide whether a region is sensitive.

An external service is downstream of the privacy boundary only. The original photo remains local and unchanged; the exported derivative must not permit recovery of masked pixels.

Production integration with raw user photos remains blocked until the PII classes, mask semantics, fail-closed behavior, and evaluation contract are approved and tested. Offline work may use synthetic, redacted, or locally controlled data.

## PII classes and preservation rules

The MVP privacy layer must cover at least:

- person names and identifying party fields;
- Israeli ID / `ת.ז.` values;
- phone numbers and email addresses;
- personal residential addresses when they identify a party rather than the rented property;
- signatures, initials, stamps, and handwritten identifying entries;
- bank-account, IBAN, cheque, and other financial identifiers;
- landlord, tenant, agent, and guarantor identifying details;
- any additional region that cannot be classified safely but is likely to contain PII.

Monetary amounts, dates, clause numbers, risk wording, deposit amounts, rent amounts, notice periods, repair obligations, and other legally relevant content are not PII by default. The detector should preserve them unless they are inseparable from a sensitive identifier.

Do not require a mask on every page. Prefer row/zone-level masking and conservative expansion around a detected PII value. If a sensitive field cannot be isolated safely, fail closed or mask the smallest safe enclosing region rather than guessing.

## Evaluation model

The annotation target is a PII region or mask, not an exact line transcription.

A controlled evaluation set should record:

- page/image identifier and immutable source hash;
- PII class;
- bounding box or polygon covering the full sensitive region;
- whether the region is readable, ambiguous, handwritten, truncated, or inseparable from nearby legal text;
- optional marker/reason metadata without storing real PII in GitHub.

Primary metrics:

- PII-region recall: proportion of annotated sensitive regions detected;
- complete-coverage rate: proportion of detected regions whose full sensitive pixels are covered;
- missed-sensitive-area rate: uncovered sensitive pixels or regions;
- over-redaction rate: legally relevant non-PII content removed by masks;
- page-level privacy pass rate: pages with no missed or partially exposed PII.

A visually plausible mask or a correct detection of the label `ת.ז.` is not enough if the associated value remains partly visible. Precision alone is not enough because a single missed identifier can violate the privacy boundary.

## Human review role

A Hebrew-capable reviewer may be needed to identify context-dependent names, addresses, guarantor details, or free-text PII that cannot be recognized from fixed labels alone. The reviewer verifies region classification and mask completeness.

The reviewer is not expected to:

- transcribe nine pages;
- correct every OCR character;
- create a full Hebrew Gold transcript;
- judge whether the contract is legally safe.

A reviewer may confirm that a region contains PII without preserving the PII value in the exported annotation.

## Paused project-owned OCR research

The repository already contains useful research assets:

- deterministic synthetic Hebrew line generation;
- dataset and evaluation contracts;
- page normalization, boundary detection, and line segmentation references;
- candidate freezing and review workflow documents;
- recognizer input, CTC text-order/decoder contracts, memory bounds, and isolated CPU runtime.

These assets are retained because parts of them may support marker recognition, digit detection, future offline OCR, or controlled research. They do not justify continuing to a CRNN, training loop, weights, predictions, full-line Gold Set, reviewer transcription APK, or CER claim on the active MVP path.

If the full local OCR track is reactivated later, its existing Gold/leakage/provenance defects must be corrected before training or quality claims. Until then, those findings are recorded technical debt, not the next MVP step.

## Detours to avoid

- Do not implement a compact CRNN merely because recognizer-boundary code already exists.
- Do not treat full-line CER as proof that PII redaction is safe.
- Do not send raw images to Gemini, Google Vision, cloud OCR, or any external image API.
- Do not preserve masked pixels in alpha channels, hidden layers, reversible overlays, debug exports, or cached derivatives sent externally.
- Do not mask whole pages by default when row/zone-level privacy can preserve legal content.
- Do not classify monetary amounts as PII solely because they contain digits.
- Do not ask the user or reviewer to rewrite the contract manually.
- Do not combine privacy detection, full OCR, legal analysis, and Android product integration into one unmeasurable PR.

## Repository workflow

Use one small branch and one ready-for-review PR per measurable step; do not auto-merge it. Each privacy/OCR PR states:

- which single state step it implements;
- whether it reads or writes any real, synthetic, redacted, or annotated data;
- which privacy or quality metric changed;
- which external engines, APIs, or dependencies were used;
- whether any runtime application behavior changed.

Each privacy/OCR PR also updates `docs/OCR_PROJECT_STATE.md` when implementation status, evidence, blockers, or the single next step changes. A working session is not allowed to derive current project state from chat history when the repository can carry it.

When the next action is ambiguous, return to this file and `docs/OCR_PROJECT_STATE.md`. Do not resume full local OCR without an explicit product decision.
