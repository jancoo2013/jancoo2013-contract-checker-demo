# Serverless GPU OCR Pipeline v1

Status: frozen/deferred OCR infrastructure reference while the canonical state is on `question-engine-development`. Read together with `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md`, and `docs/OCR_PROJECT_STATE.md`.

Merged PR #234 froze Surya/cloud OCR infrastructure as a prioritization decision and moved the active implementation track to the Question Engine. Statements below that describe serverless GPU OCR as the active MVP direction are preserved as the deferred production candidate architecture and privacy boundary for any future reopen; they do not select the current next PR. The canonical `active_track` and `next_step_id` come only from the state files. Existing privacy, Israel-only, deletion, no-raw-Gemini, and restricted-data constraints remain binding.

## 1. Product decision

A future production MVP may send an encrypted raw contract image to an approved serverless GPU worker after explicit user consent if the frozen OCR infrastructure track is explicitly reopened.

This replaces the former absolute rule that raw images must never leave the device. It does not permit uncontrolled storage, logging, model-provider reuse, or forwarding raw inputs to unrelated OCR/LLM APIs.

The serverless worker is a confidential document-processing boundary, not a public OCR endpoint.

## 2. Target pipeline

```text
raw phone photos
→ client-side normalization and transport encryption
→ bounded asynchronous job submission
→ serverless GPU worker starts on demand
→ decrypt only inside worker memory
→ full-page Hebrew OCR/layout as transient localization evidence
→ server-side PII detection + party/field role association
→ irreversible pixel removal + stable semantic placeholder rendering
→ privacy validation
→ sanitized full-page image derivative
→ approved multimodal LLM legal-risk analysis
→ Python validation / completeness checks / report generation
→ Russian report
→ deletion of raw job material and transient plaintext
```

The PII block is not required to produce a perfect transcript of every contract word or punctuation mark. Its primary job is to find every sensitive region needed for privacy, determine the role/field where safely possible, remove the original sensitive pixels irreversibly, and preserve document meaning with stable safe role markers. Preserve the role granularity actually defined by the contract: if several named people are collectively defined and used later only as `השוכר`, sanitization should preserve the single contract role `השוכר` rather than inventing `TENANT_1`, `TENANT_2`, etc. Individual numbering is needed only when the contract itself distinguishes those individuals in later obligations or rights.

The privacy-validated sanitized page images are the primary downstream document representation for the multimodal legal-analysis model. Raw OCR JSON/text remains restricted transient worker state and must not become the canonical downstream LLM payload. Sanitized text/evidence may still be derived after privacy validation when needed for deterministic checks or citations.

A separate always-on GPU server is not required for the MVP. The worker may scale to zero when idle.

## 3. Privacy boundary

Raw images and raw OCR text may exist only in these bounded locations:

- the user's device;
- encrypted transport and encrypted temporary job storage;
- volatile worker memory while the authorized job is executing.

Raw material must not appear in:

- application logs;
- exception messages;
- analytics;
- GitHub, CI, Airtable, or developer fixtures;
- persistent worker disks unless explicitly encrypted and covered by automatic deletion;
- downstream LLM prompts;
- debug exports or retained workflow results.

The worker must delete encrypted input objects, transient files, raw OCR output, and job keys after completion or terminal failure. Exact deletion guarantees and provider retention behavior must be verified before production.

The exported sanitized image must contain no recoverable original PII through alpha channels, hidden layers, metadata, alternate frames, caches, or reversible overlays. Semantic placeholder text may be rendered only after the underlying sensitive pixels have been irreversibly replaced.

## 4. Consent and product disclosure

Before upload, the user must be told in plain language that:

- the original contract will be processed on a remote GPU server;
- it contains personal information;
- it will be encrypted in transit and temporary storage;
- the worker must decrypt it during processing;
- raw data is intended to be deleted after the job;
- only the sanitized result proceeds to legal analysis.

Consent, privacy policy, processor terms, data-region selection, incident handling, and applicable Israeli privacy obligations require separate legal review before public release.

## 5. Serverless design

For the first MVP experiment after an explicit future reopen:

- use a queue-based serverless endpoint with minimum workers `0`;
- cap maximum workers and execution time to bound spend;
- use short result retention and job TTL;
- avoid a separate VPS, Redis, RabbitMQ, MinIO, and permanent database until measurements prove they are needed;
- keep the model loaded once per worker lifecycle, not once per page;
- batch all pages from one contract where memory permits;
- return only value-free metrics and sanitized artifacts.

The serverless platform's own queue is sufficient for the first benchmark. A separate orchestration service may be introduced later for authentication, billing, key mediation, retries, or provider abstraction.

## 6. Cost and latency model

Compute billing includes:

1. container and model cold start;
2. execution;
3. configured idle timeout before scale-down.

Therefore, advertised model throughput does not equal end-to-end contract latency or cost.

The benchmark must report separately:

- cold-start delay;
- warm execution time;
- pages per second and total contract time;
- queue delay;
- GPU type and VRAM;
- billed worker seconds;
- storage and transfer costs;
- failures, retries, and out-of-memory events.

## 7. OCR candidate policy

Surya was the first benchmark candidate because it supports Hebrew, returns geometry, and exposes a GPU inference path. It is not selected for production until held-out tests verify:

- printed Hebrew/layout usability on real contract photographs to the extent needed for robust PII localization and document structure;
- RTL ordering and bounding-box correctness;
- names, addresses, numbers, phones, emails and mixed printed/handwritten field behavior;
- signature/stamp/handwriting localization even when exact handwriting transcription is unreliable;
- stable enough geometry for complete irreversible PII-region coverage;
- single-contract latency rather than high-concurrency throughput only;
- GPU-memory requirements on the selected serverless class;
- current code and model-weight licensing for the intended commercial use.

Perfect full-contract transcription is not by itself a production acceptance criterion for the PII block. Missing a sensitive region is substantially more important than a non-PII OCR spelling or punctuation error.

The architecture must remain replaceable: the worker interface is model-neutral.

## 8. Required serverless benchmark step

The canonical current privacy/OCR step is defined by `docs/OCR_PROJECT_STATE.md` and its JSON mirror. This serverless architecture document does not independently select the next PR.

If the canonical state later reopens a serverless OCR viability benchmark, that benchmark must:

1. build one local/serverless-compatible benchmark worker around one OCR candidate;
2. use only synthetic, public, or owner-controlled redacted test pages in repository automation;
3. process a fixed multi-page Hebrew contract-like packet;
4. emit transient text/layout evidence sufficient to evaluate candidate quality and geometry, while persistent output remains non-sensitive;
5. compare cold and warm execution;
6. verify that raw page content and OCR text are absent from logs and retained result metadata;
7. evaluate whether the candidate exposes enough geometry/anchors for later PII localization and semantic replacement;
8. make no Android integration, production upload path, Gemini call, production mask, or real-user-data claim.

## 9. Provisional go/no-go gate

The candidate proceeds only if all are demonstrated on the same final benchmark revision:

- printed Hebrew/layout is materially usable on held-out contract-like pages for PII localization and document structure;
- stable line/block geometry is returned;
- candidate behavior around names/IDs/phones/emails/addresses/signatures/handwriting is characterized enough to design the PII detector and coverage rules;
- one ten-page job completes without OOM on an economically acceptable GPU class;
- warm compute cost is below `$0.10` per ten-page contract;
- cold and warm latency are measured rather than inferred;
- no raw content is logged or committed;
- licensing and provider retention remain explicitly unresolved or verified, never assumed.

These are research gates, not production privacy or accuracy guarantees.

## 10. Deferred infrastructure

Do not build yet:

- permanent GPU instances;
- a custom VPS queue;
- Redis or RabbitMQ;
- MinIO or a long-lived document store;
- multi-provider failover;
- production key management;
- production user consent UI;
- automated billing;
- legal-analysis integration.

Each becomes a separate decision only after a reopened benchmark establishes quality, resource use, latency, and cost.
