# Serverless GPU OCR Pipeline v1

Status: approved MVP architecture direction. Read together with `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md`, and `docs/OCR_PROJECT_STATE.md`.

## 1. Product decision

The active MVP may send an encrypted raw contract image to an approved serverless GPU worker after explicit user consent.

This replaces the former absolute rule that raw images must never leave the device. It does not permit uncontrolled storage, logging, model-provider reuse, or forwarding raw inputs to unrelated OCR/LLM APIs.

The serverless worker is a confidential document-processing boundary, not a public OCR endpoint.

## 2. Target pipeline

```text
raw phone photos
→ client-side normalization and transport encryption
→ bounded asynchronous job submission
→ serverless GPU worker starts on demand
→ decrypt only inside worker memory
→ full-page Hebrew OCR and layout extraction
→ server-side PII detection and irreversible image/text redaction
→ privacy validation
→ anonymized image/text derivative
→ numbered evidence blocks
→ approved LLM legal-risk analysis
→ Russian report
→ deletion of raw job material and transient plaintext
```

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

For the first MVP experiment:

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

Surya is the first benchmark candidate because it supports Hebrew, returns geometry, and exposes a GPU inference path. It is not selected for production until local held-out tests verify:

- printed Hebrew quality on real contract photographs;
- RTL ordering and bounding-box correctness;
- names, addresses, numbers, signatures, and mixed handwriting behavior;
- single-contract latency rather than high-concurrency throughput only;
- GPU-memory requirements on the selected serverless class;
- current code and model-weight licensing for the intended commercial use.

The architecture must remain replaceable: the worker interface is model-neutral.

## 8. First implementation step

The next bounded step is `serverless-gpu-ocr-viability-benchmark-v1`.

It must:

1. build one local/serverless-compatible benchmark worker around one OCR candidate;
2. use only synthetic, public, or owner-controlled redacted test pages in repository automation;
3. process a fixed multi-page Hebrew contract-like packet;
4. emit text, reading order, line/block geometry, latency, VRAM, and estimated billed cost;
5. compare cold and warm execution;
6. verify that raw page content and OCR text are absent from logs and retained result metadata;
7. make no Android integration, production upload path, Gemini call, production mask, or real-user-data claim.

## 9. Provisional go/no-go gate

The candidate proceeds only if all are demonstrated on the same final benchmark revision:

- Hebrew output is materially usable on held-out contract-like pages;
- stable line/block geometry is returned;
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

Each becomes a separate decision only after the benchmark establishes quality, resource use, latency, and cost.
