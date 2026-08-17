# Architecture Notes

## 1. Product Purpose

This project helps Russian-speaking tenants in Israel understand and check Hebrew residential rental contracts before signing.

The product is a preliminary AI-assisted contract risk audit and explanation tool.

It is not:

- legal advice;
- an AI lawyer;
- a legality verdict;
- a guarantee that the contract is safe;
- a tool that tells the user whether to sign.

The product should answer questions such as:

- what requires attention before signing;
- where the uploaded materials show visible risks;
- which questions should be asked to the landlord, agent, or lawyer;
- which referenced documents are missing.

The product must not answer:

- whether the user can safely sign;
- whether a clause is definitely illegal, void, enforceable, or unenforceable;
- who would win a dispute.

## 2. Current Working Pipeline

The current prototype supports:

- text-based Gemini contract audit;
- local text redaction before sending text to Gemini;
- TEST-only image upload in Streamlit;
- manual click-to-redact-row masking;
- undo last mask;
- reset all masks on page;
- in-memory handoff of masked pages via `Продолжить к распознаванию текста` for a future OCR stage;
- optional/debug/supportive PDF download or export if implemented in current main;
- no production serverless OCR pipeline yet.

The current image redaction flow is a closed technical test, not a complete production privacy layer.

Tesseract full-page Hebrew OCR on the target Samsung A55 has been tested and rejected for the active MVP path.

## 3. Target MVP Pipeline

The product owner explicitly selected encrypted on-demand serverless GPU OCR as the active architecture to benchmark.

```text
raw phone photos
→ minimal client-side normalization and encryption
→ bounded asynchronous serverless job
→ GPU worker decrypts in volatile memory
→ full-page Hebrew OCR/layout as transient localization evidence
→ server-side PII detection + party/field role association
→ irreversible pixel removal + stable semantic placeholder rendering
→ privacy validation
→ sanitized full-page image derivative
→ approved multimodal LLM risk extraction from the sanitized images
→ Python validation / completeness audit
→ three user-facing report cards
→ detailed “Разбор по пунктам”
→ deletion of raw and transient job material
```

The PII/OCR block is not a product goal of its own and is not required to produce a perfect full-contract transcript. Its primary purpose is to identify every sensitive region needed for privacy, determine a stable party/field role where safely possible, irreversibly remove the original sensitive pixels, and preserve enough semantic structure for downstream analysis.

The privacy-validated sanitized page images are the primary downstream representation of the contract. Raw OCR JSON/text remains restricted transient worker state and is not the canonical payload for the legal-analysis model. Sanitized structured text or evidence blocks may still be derived after the privacy pass for deterministic checks, citations, or report support.

The former absolute rule that raw photos must never leave the device is superseded for this consent-based serverless processing mode.

This does not authorize raw contract material to be sent to Gemini, Google Vision, general LLM APIs, analytics, logs, GitHub, CI, Airtable, or unrelated services. The approved serverless worker is the only remote component allowed to process raw page images and raw OCR text.

The paused on-device visual PII detector remains a possible future auxiliary or fallback layer, not the active next step. Surya remains on the serverless-GPU track; this architecture does not move Surya onto the phone.

The existing project-owned recognizer, CTC, synthetic-data, Gold, and CER work remains paused research. Tesseract must not be restored as an active fallback.

Do not connect runtime Airtable API before the local JSON/YAML risk configuration is stable. Airtable is a project knowledge base and control table, not the runtime MVP backend.

### Serverless GPU platform decision

**Status:** Active for the current Surya/serverless OCR benchmark.

**Target:** AWS Israel (Tel Aviv), `il-central-1`.

Google Cloud `me-west1` with an NVIDIA T4 was evaluated and rejected as the preferred target for the intended Surya workload because the T4's 16 GB VRAM and performance margin are too tight for the target server-side OCR path.

The preferred AWS GPU class is G5 / NVIDIA A10G 24 GB, subject to actual `il-central-1` availability, account quota, and measured benchmark cost.

Reopen the Google option only if:

- a larger economical GPU becomes available for the required workload in Google Cloud `me-west1`;
- measured Surya resource usage shows that a T4 is comfortably sufficient with acceptable latency and safety margin;
- AWS `il-central-1` becomes unavailable for the required GPU class or quota cannot reasonably be obtained;
- AWS becomes materially more expensive for the measured production workload.

Until one of those conditions is met, infrastructure work should proceed from the assumption:

```text
Serverless GPU OCR benchmark target = AWS il-central-1.
Preferred GPU class = G5 / NVIDIA A10G 24 GB, subject to availability/quota.
Google T4 is not the default candidate.
```

Do not restart the Google-vs-AWS comparison from zero without new measurements or provider changes that satisfy a reopen condition. The detailed closed-decision record is maintained in `docs/INFRASTRUCTURE_DECISIONS.md`.

## 4. Airtable Role

Airtable is used as a project knowledge base and admin/control table for:

- product decisions;
- Hebrew markers;
- missing document rules;
- report card aggregation rules;
- risk types;
- prompt versions;
- synthetic/anonymized test cases.

Airtable must not store:

- raw user contracts;
- raw user photos;
- OCR text containing PII;
- names;
- Israeli ID numbers;
- full addresses;
- phone numbers;
- emails;
- signatures;
- bank details;
- check numbers or account identifiers;
- landlord, tenant, agent, or guarantor identifying details.

For MVP code, prefer repo-local JSON/YAML configuration exported or copied from Airtable later.

## 5. Privacy Model

The serverless GPU worker is part of the trusted processing boundary.

Raw material may exist only in:

- the user's device;
- encrypted transport;
- encrypted short-lived job storage when needed;
- volatile worker memory while the authorized job is executing;
- tightly controlled transient worker files only when unavoidable and automatically deleted.

The worker necessarily decrypts the contract during processing. Encryption therefore protects transport and storage, not computation. The product must not describe this as local processing, zero-access processing, or a guarantee that the provider can never access plaintext.

Production target pipeline:

```text
raw image/document
→ client-side encryption
→ serverless GPU OCR/layout
→ PII detection + role association
→ irreversible sensitive-pixel replacement + semantic placeholders
→ privacy validation
→ sanitized full-page image derivative
→ approved multimodal LLM audit
→ optional sanitized structured evidence for deterministic validation/citations
→ Russian report
→ cleanup of raw job material
```

Before public release, the product must define and verify:

- explicit user consent;
- plain-language disclosure of remote processing;
- per-job key lifecycle;
- authentication and authorization;
- provider and data-region policy;
- processor terms and legal review;
- retention and deletion behavior;
- log scrubbing;
- cleanup after success, failure, timeout, and cancellation;
- incident response.

Only sanitized image/text derivatives may proceed to Gemini or another legal-analysis model. The sanitized image pages are the primary downstream artifact; raw OCR text/layout never leaves the trusted processing boundary.

PII includes at least:

- names;
- Israeli ID / ת.ז.;
- phone numbers;
- email addresses;
- full addresses;
- signatures;
- bank account details;
- check numbers if present;
- landlord/tenant/agent/guarantor identifying details.

Monetary amounts are not PII by default and should usually be preserved for analysis.

Example:

```text
Security check amount 7,500 ₪ should remain visible.
ID number or bank/check number should be redacted.
```

Do not require a mask on every page. The privacy layer should preserve legally relevant wording whenever it can safely separate it from identifiers.

The anonymized derivative must not preserve recoverable pixels in alpha channels, hidden layers, reversible overlays, metadata, caches, or debug artifacts.

### Semantic PII replacement

The exported sanitized page should preserve known participant/field roles instead of replacing every sensitive value with an unlabeled blank rectangle.

Examples:

```text
real landlord name  → [АРЕНДОДАТЕЛЬ]
first tenant name   → [АРЕНДАТОР 1]
second tenant name  → [АРЕНДАТОР 2]
guarantor name      → [ПОРУЧИТЕЛЬ 1]
tenant ID value     → [ID АРЕНДАТОРА 1]
tenant phone        → [ТЕЛЕФОН АРЕНДАТОРА 1]
```

The original pixels must be removed irreversibly before placeholder text is rendered. The same person must keep the same semantic marker across all pages of one contract. A marker must never encode a recoverable part of the original value. If the region is clearly sensitive but the role cannot be established safely, use a generic safe placeholder or block downstream handoff when complete coverage itself is uncertain.

Development inspection may use semi-transparent overlays to check coverage. Any image that can leave the trusted worker must contain opaque irreversible replacement underneath the semantic marker.

## 6. Active MVP OCR and PII Sanitization

The active OCR worker must return usable Hebrew/layout evidence sufficient for PII localization and document structure. OCR output alone is not a privacy pass, and exact transcription of every legal word or punctuation mark is not the primary objective of this block.

The server-side sanitization layer should identify at least:

- tenant and landlord names;
- Israeli ID fields and values;
- phone and email fields;
- property and party addresses;
- signatures and initials;
- handwriting containing identifying data;
- bank and cheque identifiers;
- guarantor identifying fields;
- ambiguous sensitive regions.

The sanitizer should classify image/text regions into at least three groups:

1. PII that must be irreversibly removed before downstream analysis.
2. Risk-relevant content that should be preserved.
3. Ambiguous content that blocks downstream handoff or requires controlled review.

Risk-relevant content includes, for example:

- שכר דירה;
- דמי שכירות;
- פיקדון;
- שיק ביטחון;
- בטוחה;
- ערבות;
- שטר חוב;
- נספח;
- כתב ערבות;
- רשימת ציוד;
- פרוטוקול מסירה;
- שוכר חלופי;
- עזיבה מוקדמת;
- הודעה מראש;
- בלאי סביר;
- צביעה;
- תיקונים;
- חשבונות;
- ועד בית;
- ארנונה.

Do not blindly redact a full page because one PII-like label appears. Prefer row/field/region-level masking with conservative expansion around sensitive values.

Exact handwriting recognition is not required when the system can safely identify the sensitive handwritten/signature region and remove it completely. For privacy, complete PII-region coverage has higher priority than perfect transcription of the sensitive value.

### Evidence rule for automatic sanitization

Page position, page number, alignment, short-line geometry, handwriting appearance, or digit presence are weak context only. None may independently authorize a production mask.

An automatic mask requires direct value evidence, marker-to-value/field relation, validated visual handwriting/signature/stamp evidence, or another approved evidence class under `docs/PII_EVIDENCE_DETECTOR_V1.md`.

Detector evaluation remains grouped by whole contract and template family. Contract-specific coordinates and one-off exceptions are forbidden.

Primary privacy metrics remain:

- PII-region recall;
- complete mask coverage;
- missed-sensitive-area rate;
- correct/stable semantic role replacement where the role is known;
- page/contract-level privacy pass rate;
- over-redaction of legally relevant content.

A spelling or punctuation error in non-PII OCR is not a privacy failure by itself. A missed sensitive region is.

## 7. Evidence and Citation Architecture

The downstream multimodal model reads the privacy-validated sanitized page images directly. It must never receive the raw pages or raw OCR output.

Do not rely on the LLM to copy exact Hebrew quotes.

Reason: LLMs may paraphrase, normalize spelling, alter spaces, omit particles, or slightly rewrite text. Strict string matching would reject valid answers, while loose quote matching can accept wrong evidence.

Canonical decisions:

```text
The model must not generate contract quotes as evidence.
The primary LLM input is the privacy-validated sanitized page image set.
Raw OCR JSON/text is not an external handoff artifact.
```

When deterministic source citation is required, a post-privacy evidence layer may create stable numbered references tied to sanitized page/image regions and/or sanitized text derived from those regions. Example IDs may remain:

- `P1-B03`
- `P2-B07`

The exact evidence representation is a later bounded contract. It must preserve the ability for Python to validate that cited evidence exists and for the UI to show the corresponding sanitized source without reconstructing raw PII.

Core rule:

```text
Model analyzes sanitized images.
Code validates structured findings and evidence references.
User sees the explanation.
Any Hebrew source shown to the user comes from the sanitized source artifact, not a model-generated quote.
```

Fuzzy matching can be used only as fallback/debugging, not as the main verification method.

Embeddings are not part of MVP evidence validation. Semantic similarity is not legal evidence. Embeddings may be useful later for knowledge-base search, similar-clause retrieval, or risk-matrix enrichment.

## 8. LLM/Python Responsibility Split

The multimodal LLM should extract structured findings from privacy-validated sanitized page images and, when available, sanitized deterministic evidence references.

Python should validate and decide what is shown.

The LLM should return fields such as:

- risk domain;
- severity;
- practical consequence;
- questions to ask;
- suggested Hebrew message if useful;
- confidence;
- evidence references when the bounded evidence layer is available.

Python should validate:

- JSON schema;
- evidence references exist when required;
- risk has required evidence;
- completeness rules;
- marker checks where applicable;
- aggregation into report cards.

The model is not the source of truth. The privacy-validated sanitized contract images and deterministic evidence mapping are the source of truth.

## 9. Completeness Audit

The contract must be treated as a document package, not just one text blob.

The package may include:

- main lease agreement;
- נספחים / appendices;
- שטר חוב;
- כתב ערבות / guarantee document;
- inventory / רשימת ציוד;
- handover protocol / פרוטוקול מסירה;
- signature pages;
- checks or payment/security appendices;
- additional pages with special conditions.

The product should detect references to missing documents using markers such as:

- נספח;
- נספחים;
- שטר חוב;
- כתב ערבות;
- ערבות;
- רשימת ציוד;
- פרוטוקול מסירה;
- צ'קים;
- שיקים;
- שיק ביטחון;
- בטחונות;
- חתימה;
- חתימות.

If referenced documents are missing, the report must show a completeness status before risk cards:

- Full analysis;
- Partial analysis;
- Missing documents.

For high-impact missing documents such as שטר חוב or כתב ערבות, the affected report card may become `Incomplete` even if no explicit high-risk clause was extracted.

## 10. User-Facing Report Model

The default user report should not be a long legal memo.

The default UI should show:

1. A global completeness status.
2. Three traffic-light risk cards.
3. A detailed mode called `Разбор по пунктам`.

The three cards are:

- Money;
- Terms and eviction;
- Obligations.

Each card can have one of these states:

- Red;
- Yellow;
- Green;
- Incomplete.

Green must never mean:

- the contract is safe;
- the user may sign;
- there are no legal risks.

Green means only:

```text
No obvious critical risk was found in this domain in the uploaded/analyzed materials.
```

Preferred Russian wording:

```text
В загруженных страницах явных критических рисков в этой зоне не найдено. Это не означает, что договор безопасен или что его можно подписывать без консультации.
```

## 11. Report Domains

### Money

Includes:

- rent;
- deposit;
- שטר חוב;
- security checks;
- guarantees;
- penalties;
- commissions;
- indexation;
- repair/cleaning/painting payments charged to tenant.

### Terms and eviction

Includes:

- lease period;
- renewal;
- early exit;
- replacement tenant;
- notice period;
- landlord termination rights;
- eviction or handover timing.

### Obligations

Includes:

- repairs;
- fair wear and tear;
- painting;
- cleaning;
- utilities;
- building committee;
- municipal taxes;
- furniture/equipment responsibility;
- appliances;
- handover state.

## 12. Detailed Mode: Разбор по пунктам

`Разбор по пунктам` is the optional detailed layer over the same backend analysis.

It should show:

- validated finding title;
- domain;
- severity;
- Russian explanation;
- practical consequence;
- questions to ask;
- suggested Hebrew message if useful;
- evidence references when available;
- confidence;
- optional sanitized Hebrew original/source region in an expander.

There must not be two separate analyses. The system should run one backend analysis and present it in two ways:

```text
one validated structured analysis
→ default three-card summary
→ detailed point-by-point view
```

## 13. שטר חוב UX

Do not force the user to read or rewrite Hebrew handwriting.

For שטר חוב, the product should ask only minimal critical questions that the machine cannot reliably answer:

- Is a numeric amount visible?
- What numeric amount is visible, if any?
- Are there suspicious blank fields near amount/date/signature?
- Is the user unsure?

The product should not require the user to enter:

- amount in words;
- debtor name;
- full date;
- all handwritten fields;
- full Hebrew transcription.

Python should compare the numeric amount with rent/deposit/security context and raise risk if the amount is missing, unusually high, blank, or unclear.

## 14. Guardrails Against Legal Overclaiming

Avoid language such as:

- this clause is illegal;
- demand deletion;
- do not sign;
- the landlord is violating the law;
- you will win in court;
- this is enforceable/unforceable with certainty.

Use language such as:

- this clause may create increased risk;
- this wording appears to place broad responsibility on the tenant;
- it is worth clarifying this before signing;
- consider discussing this with the landlord, agent, or a licensed lawyer;
- this report is incomplete because referenced documents are missing.

The product may recommend consulting a licensed lawyer when high financial, termination, guarantee, or unclear legal-risk conditions appear.

## 15. Template/RAG Comparison

Template/reference comparison is not MVP.

Do not send many reference contracts plus the user contract into one LLM call and ask the model to find deviations.

If template comparison is added later, use this safer flow:

```text
privacy-validated sanitized images/text
→ deterministic evidence extraction
→ classify template candidate
→ confidence threshold
→ load exactly one matching baseline
→ compare normalized extracted JSON to normalized baseline JSON
→ Python performs final diff and report aggregation
```

If template confidence is low, skip template comparison and fall back to generic risk audit.

## 16. Conflict-Consultant Mode Is Not MVP

A future mode may help users structure a post-signing conflict, for example:

- landlord threatens to cash a security check;
- damage is claimed after a new tenant moved in;
- dispute about painting/cleaning;
- missing inspection report.

This is not part of MVP because the source of truth is weaker than in contract analysis.

Contract audit has a document as source. Conflict consulting often has only the user narrative.

If implemented later, it must avoid legal conclusions and focus on:

- facts stated by the user;
- missing evidence;
- weak points in each position;
- documents to request;
- questions to ask;
- when to contact a lawyer.

The assistant must not say who will win a legal dispute.

## 17. Rejected or Deferred Approaches

Rejected for the active MVP:

- Tesseract full-page Hebrew OCR on the target phone;
- treating Surya as an on-device production dependency;
- treating perfect full-contract OCR transcription as the primary purpose of the PII block;
- making raw OCR JSON/text the canonical LLM handoff instead of privacy-validated sanitized page images;
- pretending that encrypted server processing is local or zero-access;
- sending raw images or raw OCR text from the trusted worker to Gemini or unrelated OCR/LLM APIs;
- permanent unencrypted storage of user contracts;
- building an always-on GPU server for sporadic MVP traffic;
- adding a VPS, Redis, RabbitMQ, MinIO, or PostgreSQL before the platform-queue benchmark proves a need;
- relying on high-concurrency throughput numbers as proof of single-contract latency;
- relying on exact LLM-generated quotes;
- exposing long Hebrew quotes by default in the user report;
- using embeddings as legal evidence validation;
- comparing against many reference contracts in one LLM call;
- building conflict-consultant mode before contract-audit pipeline is stable.

Deferred:

- on-device visual PII localization as a primary path;
- project-owned full Hebrew OCR, CRNN training, full-line Gold transcription, and Android recognizer export;
- production encryption and key management;
- custom VPS orchestration and persistent queue/storage;
- runtime Airtable API integration;
- template/reference comparison;
- curated legal/risk knowledge base RAG;
- NotebookLM-generated risk matrix integration.

## 18. Development Principle

Keep the architecture measurable and replaceable.

The canonical current privacy/OCR step is selected only by `docs/OCR_PROJECT_STATE.md` and its JSON mirror. Architecture documents define ordering constraints and gates, but they do not independently choose the next PR.

For the active image track, the current planned order is:

1. Complete bounded client-side document geometry normalization (orientation, text-geometry analysis, conservative deskew with full-frame preservation; no destructive runtime crop) and audit that block as a unit.
2. Run the serverless GPU OCR viability benchmark using only synthetic/redacted pages.
3. Make the candidate quality, PII-localization geometry, latency, VRAM, and cost decision.
4. Define the bounded encrypted job-envelope and cleanup contract.
5. Implement server-side PII detection, stable role association, irreversible semantic image sanitization, and privacy evaluation.
6. Produce privacy-validated sanitized full-page images as the primary multimodal LLM input; add sanitized structured evidence only where deterministic validation/citation needs it.
7. Integrate multimodal LLM risk analysis and report generation.
8. Add production consent, legal, provider, Israel-region, authorization, retention, and incident controls.

Document-boundary and crop estimators may remain as advisory capture-quality evidence, but production preprocessing must not physically remove source pixels before OCR unless a later explicitly approved architecture change reintroduces destructive crop.

The serverless benchmark must not be treated as production deployment, and completing the client-side geometry block does not authorize upload, OCR, PII processing, or provider integration.

The source of truth is the privacy-validated sanitized contract image set plus any deterministic sanitized evidence derived from it, not the LLM and not raw OCR JSON.