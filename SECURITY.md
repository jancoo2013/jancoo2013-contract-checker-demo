# Security Policy and Mandatory Review Gate

Status: binding repository security policy. This file applies to every branch and pull request. It complements `AGENTS.md`, the architecture/privacy documents, and the canonical OCR state. It does not certify the product as production-safe.

## 1. Current security posture

This repository is a pre-production prototype. Security controls described here are requirements, not proof that the deployed system already satisfies them.

Production use with real contracts remains blocked until the relevant controls are implemented and verified in the actual runtime, provider configuration, storage, logs, cleanup paths, and incident procedures.

## 2. Data classes

### 2.1 Restricted raw and transient material

Restricted material includes:

- original contract photos or page images;
- raw OCR text or layout output;
- any payload containing names, Israeli ID numbers, phone numbers, email, addresses, signatures, bank details, account numbers, guarantor data, or other recoverable PII;
- unredacted crops, thumbnails, previews, caches, debug exports, temporary files, and failure artifacts;
- job keys, encryption keys, signed URLs, provider credentials, access tokens, and secrets.

Restricted material may exist only in the approved processing path:

- the user device;
- encrypted transport;
- approved encrypted short-lived job storage when unavoidable;
- volatile memory of an authorized worker;
- bounded transient worker files when unavoidable and automatically cleaned up.

It must not enter GitHub, CI, Airtable, analytics, crash reporting, general logs, support tickets, downstream LLM prompts, or unrelated services.

### 2.2 Persistable sanitized material

The final user report and sanitized evidence may be stored intentionally. They are not zero-retention objects.

Persistent report storage is allowed only when all of the following are true:

- the report was produced from a privacy-validated sanitized derivative;
- it contains no original page image, raw OCR dump, recoverable PII, secret, or hidden reversible layer;
- every read, list, export, update, and delete operation is account-scoped and authorization-checked;
- object identifiers are not the only access-control mechanism and are not guessable authorization substitutes;
- data is encrypted at rest and in transit;
- retention, user deletion, account deletion, backup expiry, and operational recovery behavior are defined and tested;
- logs and analytics contain only non-sensitive metadata.

### 2.3 Security telemetry

Security and reliability telemetry may persist only as structured non-sensitive metadata, such as event type, timing, bounded sizes, status codes, anonymized job identifiers, provider region identifier, and cleanup result. Contract text, OCR text, page pixels, PII, keys, signed URLs, and authorization headers are prohibited.

## 3. Security invariants

The following are blocking invariants.

### 3.1 Israel-only processing gate for restricted material

- Original images, raw OCR text, and PII-bearing payloads may be processed only by explicitly approved infrastructure physically located in Israel.
- Code must use an explicit allowlist of approved Israel endpoints or provider region identifiers. Hostname guesses, default regions, nearest-region routing, or implicit provider behavior are insufficient.
- Any endpoint or region not explicitly approved must fail closed before upload or job creation.
- Automatic fallback, retry, replication, migration, or disaster-recovery routing to another country or region is prohibited for restricted material.
- Unavailability of the approved Israel endpoint must block the job rather than weaken the boundary.
- Provider retention, subprocessors, support access, backups, logs, and deletion behavior must be verified before production use.

### 3.2 Minimum exposure and deletion

- Restricted material must exist for the shortest bounded time required for the active job.
- Cleanup must run after success, terminal failure, timeout, cancellation, and worker interruption where the platform permits.
- Cleanup must be idempotent and observable through non-sensitive status metadata.
- Raw or transient data must not be retained merely for debugging, model improvement, analytics, support, or convenience.
- A deletion request is not proof of deletion; runtime/provider behavior must be verified.

### 3.3 Redaction integrity

- Image redaction must be irreversible in the exported artifact.
- Masked pixels must not remain recoverable through alpha channels, overlays, hidden layers, metadata, alternate frames, caches, undo data, or reversible transforms.
- Sanitized text must not retain PII in hidden fields, structured metadata, source maps, model traces, or debug payloads.
- When privacy validation is uncertain or contradictory, the system must block downstream analysis rather than pass the material through.

### 3.4 Authentication and authorization

- Every persistent report operation must authenticate the caller and authorize access to that exact report.
- Cross-account reads, enumeration, insecure direct object references, predictable public links, and authorization based only on client-provided ownership fields are prohibited.
- Administrative access must be least-privilege, auditable, and separate from normal user access.
- Session, token, password-reset, and account-recovery behavior must fail closed and must not expose report contents.

### 3.5 Secrets and cryptography

- Secrets must not be committed, logged, placed in client bundles, returned in API responses, or embedded in examples.
- Production secrets must come from an approved secret manager with least-privilege access and rotation procedures.
- Do not invent custom cryptography. Use reviewed platform/library primitives with authenticated encryption and explicit key lifecycle.
- Signed URLs and job tokens must be short-lived, narrowly scoped, and protected from logs and referrers.

### 3.6 Input, resource, and network safety

- Treat images, PDFs, OCR output, filenames, metadata, archives, callbacks, and provider responses as hostile input.
- Enforce bounded file size, page count, pixel count, dimensions, decompression ratio, execution time, concurrency, memory, retries, and output size.
- Reject malformed or contradictory contracts instead of guessing.
- Prevent server-side request forgery, path traversal, command injection, unsafe deserialization, arbitrary file access, and untrusted callback destinations.
- New network destinations, dependencies, permissions, or provider capabilities require explicit review.

## 4. Threat model

Security review must consider at least:

- an unauthenticated external attacker;
- an authenticated user attempting cross-account access;
- account takeover or stolen session/token;
- malicious files and resource-exhaustion inputs;
- compromised credentials, dependency, CI job, worker image, provider account, or administrator account;
- accidental disclosure through logs, analytics, crash reports, screenshots, support flows, backups, or debug artifacts;
- provider region drift, retention drift, or fallback outside Israel;
- incomplete cleanup after failure, timeout, cancellation, or worker termination;
- denial of service and cost-amplification attacks against GPU jobs;
- supply-chain changes and unsafe dependency updates.

## 5. Mandatory security review for every PR

Every PR, including documentation-only and test-only PRs, must receive a final-diff security review before it is marked Ready. A generic code review is not a substitute.

The reviewer must inspect the exact final head and cover, as applicable:

1. changed data flows and trust boundaries;
2. raw/transient data, report persistence, retention, deletion, caches, and backups;
3. authentication, authorization, ownership checks, and report enumeration/IDOR risk;
4. secrets, tokens, signed URLs, logs, analytics, crash reporting, and error payloads;
5. Israel-only endpoint allowlisting and absence of cross-region fallback;
6. network destinations, callbacks, SSRF, file/path handling, parsing, and hostile input;
7. input/resource bounds, rate limits, retries, concurrency, GPU cost amplification, and denial of service;
8. redaction irreversibility and downstream privacy validation;
9. dependencies, permissions, CI/workflow changes, generated artifacts, and supply-chain exposure;
10. cryptographic primitives, key lifecycle, and unsupported security claims;
11. cleanup behavior on success, failure, timeout, cancellation, and interruption;
12. consistency with this file and all binding architecture/privacy/state documents.

The PR body must contain exactly one final verdict:

- `Security review: PASS`
- `Security review: BLOCKING FINDINGS`

It must also record `Security impact: NONE`, `LOW`, or `HIGH`, list any findings, and state what remains unverified. Documentation-only changes still require a verdict; `not applicable` is not an accepted substitute.

### 5.1 Blocking findings

The PR must not be marked Ready or recommended for merge when any of the following remains:

- restricted material can reach a prohibited service, repository, log, analytics system, crash report, or downstream LLM;
- an unapproved or non-Israel endpoint can receive restricted material, including through fallback or retry;
- raw/transient deletion is absent, unbounded, fail-open, or falsely claimed as verified;
- persistent reports can be read, listed, exported, changed, or deleted without exact account-scoped authorization;
- redaction is reversible or privacy validation can fail open;
- a secret, credential, key, signed URL, token, or real user document is present in the diff or test artifacts;
- hostile input can trigger unbounded memory, CPU, GPU, storage, retry, concurrency, decompression, or output growth;
- new network access, dependency, permission, workflow, or provider capability lacks explicit justification and review;
- custom or unauthenticated cryptography is introduced for protected data;
- security evidence is stale, refers to a different head SHA, or claims runtime/provider behavior that was not actually tested;
- binding security, privacy, architecture, or state documents conflict.

## 6. Final report persistence contract

The product may retain all final reports for the authenticated user. This convenience must not turn the report store into a hidden archive of original contracts.

A stored report must contain only the Russian analysis, structured findings, and sanitized evidence needed to support those findings. Original images, raw OCR, names, IDs, signatures, bank details, unredacted excerpts, temporary debug material, and processing keys must remain outside the report object.

The production design must define:

- report ownership and account isolation;
- encryption and key access;
- create/read/list/export/delete authorization;
- user-visible deletion and account deletion;
- retention and backup expiry;
- migration and restore behavior;
- audit events without report contents;
- handling of a report when later privacy validation detects a defect.

## 7. Vulnerability handling

Do not publish exploit details, credentials, or real contract data in a public issue. Report sensitive findings through a private channel agreed with the repository owner. Use synthetic proof material only.

For a suspected exposure of restricted material:

1. stop new affected processing where possible;
2. revoke or rotate relevant credentials and signed access;
3. preserve only non-sensitive forensic metadata;
4. identify affected data classes, users, regions, providers, logs, caches, and backups;
5. verify containment and deletion rather than assuming it;
6. record corrective work in a bounded PR and update the canonical state.
