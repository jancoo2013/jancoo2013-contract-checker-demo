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
→ client-side normalization and encryption
→ bounded asynchronous serverless job
→ GPU worker decrypts in volatile memory
→ full-page Hebrew OCR and layout extraction
→ server-side PII detection and irreversible image/text redaction
→ privacy validation
→ anonymized derivative and numbered evidence blocks
→ structured LLM risk extraction
→ Python validation
→ completeness audit
→ three user-facing report cards
→ detailed “Разбор по пунктам”
→ deletion of raw and transient job material
```

The former absolute rule that raw photos must never leave the device is superseded for this consent-based serverless processing mode.

This does not authorize raw contract material to be sent to Gemini, Google Vision, general LLM APIs, analytics, logs, GitHub, CI, Airtable, or unrelated services. The approved serverless worker is the only remote component allowed to process raw page images and raw OCR text.

The paused on-device visual PII detector remains a possible future auxiliary or fallback layer, not the active next step.

The existing project-owned recognizer, CTC, synthetic-data, Gold, and CER work remains paused research. Tesseract must not be restored as an active fallback.

Do not connect runtime Airtable API before the local JSON/YAML risk configuration is stable. Airtable is a project knowledge base and control table, not the runtime MVP backend.

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
→ PII detection and irreversible image/text redaction
→ privacy validation
→ anonymized derivative
→ numbered evidence blocks
→ approved LLM audit
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

Only sanitized image/text derivatives may proceed to Gemini or another legal-analysis model.

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

## 6. Active MVP OCR and PII Sanitization

The active OCR worker must return usable Hebrew text plus line/block geometry. OCR output alone is not a privacy pass.

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

### Evidence rule for automatic sanitization

Page position, page number, alignment, short-line geometry, handwriting appearance, or digit presence are weak context only. None may independently authorize a production mask.

An automatic mask requires direct value evidence, marker-to-value/field relation, validated visual handwriting/signature/stamp evidence, or another approved evidence class under `docs/PII_EVIDENCE_DETECTOR_V1.md`.

Detector evaluation remains grouped by whole contract and template family. Contract-specific coordinates and one-off exceptions are forbidden.

Primary privacy metrics remain:

- PII-region recall;
- complete mask coverage;
- missed-sensitive-area rate;
- page/contract-level privacy pass rate;
- over-redaction of legally relevant content.

## 7. Evidence and Citation Architecture

Do not rely on the LLM to copy exact Hebrew quotes.

Reason: LLMs may paraphrase, normalize spelling, alter spaces, omit particles, or slightly rewrite text. Strict string matching would reject valid answers, while loose quote matching can accept wrong evidence.

Canonical decision:

```text
The model must not generate contract quotes.
```

Instead:

1. The OCR layer splits sanitized contract text into numbered evidence blocks.
2. Each block receives a stable ID, for example:
   - `P1-B03`
   - `P2-B07`
3. Gemini receives numbered sanitized blocks.
4. Gemini returns structured JSON with `evidence_block_ids`.
5. Python validates that the IDs exist.
6. Python retrieves the exact sanitized Hebrew source text if needed.
7. The user sees a Russian explanation by default.
8. The Hebrew original is available only behind an optional expander such as `Показать оригинал на иврите`.

Core rule:

```text
Model does not quote.
Code stores the source.
User sees the explanation.
Original Hebrew is available on demand.
```

Fuzzy matching can be used only as fallback/debugging, not as the main verification method.

Embeddings are not part of MVP evidence validation. Semantic similarity is not legal evidence. Embeddings may be useful later for knowledge-base search, similar-clause retrieval, or risk-matrix enrichment.

## 8. LLM/Python Responsibility Split

The LLM should extract structured findings from sanitized evidence blocks.

Python should validate and decide what is shown.

The LLM should return fields such as:

- risk domain;
- severity;
- practical consequence;
- questions to ask;
- suggested Hebrew message if useful;
- confidence;
- evidence block IDs.

Python should validate:

- JSON schema;
- evidence IDs exist;
- risk has required evidence;
- source blocks are not empty;
- completeness rules;
- marker checks where applicable;
- aggregation into report cards.

The model is not the source of truth. The sanitized uploaded contract text/images and deterministic evidence mapping are the source of truth.

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
- evidence block IDs;
- confidence;
- optional Hebrew original in an expander.

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
OCR/text
→ evidence blocks
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

For the active image track, build in this order:

1. Serverless GPU OCR viability benchmark using only synthetic/redacted pages.
2. Candidate quality, geometry, latency, VRAM, and cost decision.
3. Bounded encrypted job-envelope and cleanup contract.
4. Server-side PII sanitization and privacy evaluation.
5. Sanitized evidence blocks.
6. LLM risk analysis and report integration.
7. Production consent, legal, provider, region, and incident controls.

The first benchmark must not be treated as production deployment.

The source of truth is the sanitized contract evidence produced by the approved processing pipeline, not the LLM.
