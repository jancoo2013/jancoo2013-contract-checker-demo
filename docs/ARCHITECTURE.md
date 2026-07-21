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
- no OCR pipeline in production yet.

Images are not sent to Gemini, Google Vision, OCR services, or external image APIs.

The current image redaction flow is a closed technical test, not a complete production privacy layer.

## 3. Target MVP Pipeline

The target MVP should move in this order:

```text
raw image/document
→ on-device automatic PII-region detection and irreversible masking
→ local fail-closed privacy validation
→ anonymized image/document
→ approved external full OCR
→ secondary text PII redaction
→ numbered evidence blocks
→ structured LLM risk extraction
→ Python validation
→ completeness audit
→ three user-facing report cards
→ detailed “Разбор по пунктам”
→ optional Hebrew source expansion
```

The local mobile component is a privacy detector/redactor, not a required full Hebrew transcription engine. It may use layout, page zones, Hebrew field markers, digit patterns, signatures, handwriting cues, and conservative mask expansion.

An approved external OCR/LLM service may receive only the anonymized derivative after the local privacy boundary has passed. Raw photos and recoverable PII must not leave the device.

The existing project-owned recognizer, CTC, synthetic-data, Gold, and CER work is paused research rather than an MVP dependency. Do not resume CRNN or training work without an explicit product decision recorded in the binding privacy/OCR documents.

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

Raw photos, documents, or text containing personal data must not be sent to external OCR or LLM services.

Production target pipeline:

```text
raw image/document
→ local/browser/mobile PII-region detection
→ irreversible local masking
→ local privacy validation
→ anonymized image/document
→ approved external OCR
→ secondary text PII redaction
→ LLM audit
→ Russian report
```

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

Do not require a mask on every page. Many middle pages of a lease may contain no personal data. Privacy logic should detect likely personal-data rows by Hebrew field labels, layout context, known PII markers, digits, signatures, and handwriting cues. It should mask only the rows or zones likely to contain personal data while preserving monetary amounts and legal-risk content.

The anonymized derivative must not preserve recoverable pixels in alpha channels, hidden layers, reversible overlays, metadata, or debug artifacts that are sent externally.

## 6. Active MVP PII-Region Detection

Local image privacy logic should search for Hebrew field labels and row patterns such as:

- tenant name field;
- landlord name field;
- Israeli ID field;
- phone field;
- email field;
- address field;
- signature field;
- bank details field;
- guarantor identifying fields.

The detector should classify rows or zones into at least three groups:

1. PII rows/zones that must be masked before external OCR/LLM use.
2. Risk-relevant rows that should be preserved for analysis.
3. Ambiguous rows/zones that require fail-closed masking or local review.

Risk-relevant rows include, for example:

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

Do not blindly redact a full page only because one PII-like label appears on it. Prefer row/zone-level masking with conservative expansion around the sensitive value.

The annotation and verification target is a PII region or mask, not an exact full-line transcript. Primary metrics are PII-region recall, complete mask coverage, missed-sensitive-area rate, page-level privacy pass rate, and over-redaction of legally relevant non-PII content.

A Hebrew-capable reviewer verifies whether sensitive regions were missed or incompletely covered and whether important legal text was unnecessarily removed. The reviewer is not expected to transcribe the contract or correct every OCR character.

## 7. Evidence and Citation Architecture

Do not rely on the LLM to copy exact Hebrew quotes.

Reason: LLMs may paraphrase, normalize spelling, alter spaces, omit particles, or slightly rewrite text. Strict string matching would reject valid answers, while loose quote matching can accept wrong evidence.

Canonical decision:

```text
The model must not generate contract quotes.
```

Instead:

1. Python/OCR layer splits the contract into numbered evidence blocks.
2. Each block receives a stable ID, for example:
   - `P1-B03`
   - `P2-B07`
3. Gemini receives numbered blocks.
4. Gemini returns structured JSON with `evidence_block_ids`.
5. Python validates that the IDs exist.
6. Python retrieves the exact original Hebrew text from the source block if needed.
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

The LLM should extract structured findings.

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

The model is not the source of truth. The uploaded contract text/images after preprocessing are the source of truth.

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

Rejected for MVP:

- sending raw contract photos or recoverable PII to external OCR/LLM services;
- treating full local Hebrew OCR as a prerequisite for privacy-safe image handoff;
- requiring a mask on every page before OCR handoff;
- using the current manual masking test as a complete production privacy layer;
- asking the user to manually redact everything without guidance;
- relying on exact LLM-generated quotes;
- exposing long Hebrew quotes by default in the user report;
- using embeddings as legal evidence validation;
- comparing against many reference contracts in one LLM call;
- building conflict-consultant mode before contract-audit pipeline is stable.

Deferred:

- project-owned full Hebrew OCR, CRNN training, full-line Gold transcription, and Android recognizer export;
- runtime Airtable API integration;
- template/reference comparison;
- curated legal/risk knowledge base RAG;
- NotebookLM-generated risk matrix integration.

## 18. Development Principle

Keep the architecture conservative.

For non-privacy product work, build in this order:

1. Structured text audit.
2. Evidence blocks.
3. Python validation.
4. Completeness audit.
5. Three-card report + `Разбор по пунктам`.
6. Privacy-safe anonymized image/OCR handoff.

The user has explicitly selected automatic local PII detection and irreversible redaction as the current active image-processing track. Follow `docs/CUSTOM_OCR_PIPELINE.md` and `docs/OCR_PROJECT_STATE.md`. Full project-owned OCR research is paused unless explicitly reactivated.

Do not let the LLM become the source of truth.

The source of truth is always the uploaded contract text/images after preprocessing.
