# Architecture Notes

## 1. Product Purpose

This project helps Russian-speaking tenants in Israel understand and check Hebrew rental contracts before signing.

The product is not legal advice and does not replace a lawyer. It is a guided risk-audit and explanation tool.

## 2. Current Working Pipeline

The current prototype supports:

- text-based Gemini contract audit;
- local text redaction before sending text to Gemini;
- TEST-only image upload in Streamlit;
- manual click-to-redact-row masking;
- undo last mask;
- reset all masks on page;
- export of redacted/anonymized PDF if implemented in current main;
- no OCR pipeline in production yet.

Images are not sent to Gemini, Google Vision, OCR services, or external image APIs.

## 3. Privacy Model

Raw photos with personal data must not be sent to external OCR or LLM services.

Production target pipeline:

```text
photo
→ local/browser/mobile PII masking
→ anonymized image/PDF
→ OCR
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
- landlord/tenant/agent identifying details.

Important:
Monetary amounts are not PII by default and should usually be preserved for analysis.

Example:
Security check amount 7,500 ₪ should remain visible.
ID number or bank/check number should be redacted.

## 4. Evidence and Citation Architecture

Do not rely on the LLM to copy exact Hebrew quotes.

Reason:
LLMs may paraphrase, normalize spelling, alter spaces, omit particles, or slightly rewrite text. Strict string matching would reject valid answers, while loose quote matching can accept wrong evidence.

Canonical decision:

The model must not generate contract quotes.

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

Model does not quote.
Code stores the source.
User sees the explanation.
Original Hebrew is available on demand.

## 5. User-Facing Report

Hebrew quotes are mostly noise for users who do not know Hebrew.

Default report card should show:

- risk type;
- risk level;
- plain Russian explanation;
- practical consequence;
- what to ask the landlord/agent;
- suggested Hebrew message if useful;
- confidence level;
- source reference like `page 1, block 7`.

The exact Hebrew source should be hidden by default and shown only on request.

Use `Источник: страница X, блок Y` instead of dumping Hebrew text into the main report.

## 6. Guardrails Against Hallucinations

The LLM must be constrained to structured output.

Every risk finding must include at least one `evidence_block_id` unless it is explicitly marked as a general warning.

Python must validate:

- JSON schema;
- evidence IDs exist;
- risk has required evidence;
- source blocks are not empty;
- optional keyword/marker checks for certain risk classes.

Examples:

`security_check` / deposit risks should usually be supported by blocks containing markers such as:

- שיק ביטחון;
- בטוחה;
- ערבות;
- פיקדון;
- ₪.

`early_exit` / replacement tenant risks should usually be supported by markers such as:

- שוכר חלופי;
- עזיבה מוקדמת;
- הודעה מראש;
- העברת זכויות.

Fuzzy matching can be used only as fallback/debugging, not as the main verification method.

Embeddings are not part of MVP verification. They may be useful later for knowledge-base search, similar clause retrieval, or risk-matrix enrichment, but not as legal evidence validation.

## 7. Conflict-Consultant Mode Is Not MVP

A future mode may help users structure a post-signing conflict, for example:

- landlord threatens to cash a security check;
- damage is claimed after a new tenant moved in;
- dispute about painting/cleaning;
- missing inspection report.

This is not part of MVP because the source of truth is weaker than in contract analysis.

Contract audit has a document as source.
Conflict consulting often has only the user narrative.

If implemented later, it must avoid legal conclusions and focus on:

- facts stated by the user;
- missing evidence;
- weak points in each position;
- documents to request;
- questions to ask;
- when to contact a lawyer.

The assistant must not say who will win a legal dispute.

## 8. Security Checks and Deposits

The product must preserve and analyze monetary amounts connected to:

- security checks;
- deposits;
- guarantees;
- repair/cleaning obligations;
- painting obligations;
- unpaid bills;
- early termination penalties.

These values are legally and practically important.

Do not redact amounts merely because they are near personal-data markers.

Redact identifying numbers and personal values, but preserve risk-relevant financial terms and sums when possible.

## 9. Rejected or Deferred Approaches

Rejected for MVP:

- sending raw contract photos to external OCR/LLM services;
- asking the user to manually redact everything without guidance;
- relying on exact LLM-generated quotes;
- exposing long Hebrew quotes by default in the user report;
- using embeddings as legal evidence validation;
- building conflict-consultant mode before contract-audit pipeline is stable.

Deferred:

- automatic Hebrew marker detection;
- OCR after local image anonymization;
- comparison against a curated legal/risk knowledge base;
- NotebookLM-generated risk matrix integration.

## 10. Development Principle

Keep the architecture conservative.

The safest MVP path:

```text
redacted/anonymized document
→ OCR/text extraction
→ numbered evidence blocks
→ structured LLM risk analysis
→ Python validation
→ Russian user report
→ optional Hebrew source expansion
```

Do not let the LLM become the source of truth.

The source of truth is always the uploaded contract text/images after preprocessing.
