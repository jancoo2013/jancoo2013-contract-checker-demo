# Evidence-based local PII detector v1

Status: binding design contract for the next local privacy detector. Read together with `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md`, and `docs/OCR_PROJECT_STATE.md`.

## 1. Purpose

The detector must find and mask likely personal-data regions across different Israeli residential lease layouts without being tuned to one contract template.

The detector is local and may use bounded marker recognition, value-shape checks, handwriting/signature cues, and spatial relations. It is not required to transcribe the full Hebrew page.

`marker_layout_baseline_v0` remains a diagnostic baseline only. Its fixed page-zone rules are not a production decision policy.

## 2. Core invariant

Page position alone is never sufficient evidence for an automatic mask.

These facts by themselves must not create a mask:

- a line is in the top part of a page;
- a line is between fixed vertical percentages;
- a line is near the bottom of a page;
- a line is on the first or last page;
- a line is short, right-aligned, or contains digits.

Page position and page role may be recorded only as weak context. A zone-only finding may be sent to local review, but it must not become an automatic mask.

## 3. Evidence families

### 3.1 Direct value evidence

A bounded local detector may produce direct evidence for:

- Israeli ID-like numeric structure;
- phone-like numeric structure;
- email-like structure;
- bank-account or IBAN-like structure;
- cheque or other financial identifier structure;
- other explicitly approved identifier formats.

Digits alone are not direct evidence. Monetary amounts, dates, clause numbers, notice periods, and rent/deposit amounts must not be classified as personal data solely because they contain digits.

### 3.2 Marker evidence

A bounded marker detector may identify labels such as:

- name / party labels;
- `ת.ז.` and equivalent ID labels;
- phone and email labels;
- address labels;
- bank or account labels;
- guarantor labels;
- signature labels.

A marker alone identifies a local search area. It does not justify masking an entire line, page band, or page.

### 3.3 Visual sensitive-region evidence

Local image analysis may identify:

- handwriting adjacent to a form field;
- signatures or initials;
- stamps or seals;
- filled blank lines associated with an identifying field;
- dense handwritten additions that cannot be separated safely from PII.

A generic table border, underline, strikethrough, or printed paragraph is not handwriting/signature evidence.

### 3.4 Relational evidence

The detector must preserve how signals are connected. Relevant relations include:

- marker and value in the same line;
- value immediately adjacent to the marker;
- handwritten entry inside the marker's bounded field;
- signature-like region adjacent to a signature label;
- direct value pattern within the smallest enclosing field or row.

Large page zones are not relational evidence.

## 4. Candidate decisions

Every candidate must have one of three dispositions:

1. `auto_mask` — sufficient local evidence exists and the smallest safe sensitive region can be isolated.
2. `local_review` — PII is plausible but evidence or geometry is incomplete; nothing may be exported until review resolves it.
3. `preserve` — evidence is insufficient or the region is risk-relevant non-PII content.

An `auto_mask` candidate requires at least one of:

- a validated direct value pattern;
- marker evidence linked to a plausible value or filled field;
- validated signature/handwriting/stamp evidence linked to a sensitive field;
- another explicitly approved strong evidence combination.

Two weak layout facts do not become strong evidence merely because they agree.

## 5. Candidate evidence record

The next implementation must make evidence explicit rather than encoding it only in a reason string. A candidate record must be able to represent:

- candidate geometry;
- proposed PII class;
- disposition;
- evidence family and detector identifier;
- local evidence geometry where applicable;
- marker-to-value or field relation where applicable;
- ambiguity/fail-closed reason;
- detector version.

The evidence record must not store real PII text in GitHub fixtures. Synthetic values and non-identifying placeholders are allowed.

## 6. Mask geometry

The mask must cover the smallest safe sensitive region.

- Do not mask a full page because one marker appears.
- Do not mask a fixed page band.
- Do not expand a value mask across unrelated legal text.
- If a sensitive value cannot be separated, use `local_review` or the smallest safe enclosing field/row.
- Irreversible rendering and local privacy validation remain downstream requirements.

## 7. Generalization protocol

Evaluation is grouped by whole contract, not by individual page or line.

- All pages from one contract stay in one split.
- Contracts from the same known template family should stay in one split where feasible.
- A held-out contract must not influence thresholds, marker lists, geometry rules, or exception logic before its evaluation.
- A failure on a new contract must be classified by a reusable error category. Do not add contract-specific coordinates, page numbers, filenames, or one-off exceptions.
- Every newly available real contract becomes a new generalization test, not a new template to memorize.

For engineering validation, a diverse set of 5–10 contracts may expose overfitting, but it is not sufficient for a production-quality claim.

Required metrics remain:

- PII-region recall;
- complete mask coverage;
- missed-sensitive-area rate;
- over-redaction of legally relevant content;
- page-level privacy pass rate.

Report metrics both per contract and across contracts. A good average must not hide one failed contract.

## 8. Migration from the current baseline

1. Freeze `marker_layout_baseline_v0` as a diagnostic comparator.
2. Define the candidate evidence schema and validation rules.
3. Add deterministic direct-pattern evidence using synthetic and non-identifying fixtures.
4. Add marker-to-value relational evidence.
5. Add handwriting/signature/stamp evidence.
6. Combine evidence into `auto_mask`, `local_review`, and `preserve` decisions.
7. Evaluate on whole-contract held-out splits before Android production integration.

The controlled Android reviewer remains useful for local verification, but the current three-page contract must not be used as the sole tuning target.

## 9. Immediate implementation step

The single next implementation step is `pii-candidate-evidence-schema-v0`:

- define a strict evidence-bearing candidate schema;
- validate allowed evidence families and dispositions;
- prove that page-zone context alone cannot validate an `auto_mask` candidate;
- use only synthetic/non-identifying fixtures;
- do not change the current renderer, Android reviewer, external APIs, or production runtime in that PR.
