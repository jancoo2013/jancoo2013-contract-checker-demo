# Question Engine — Dispute / Practice Layer v0

Status: provisional Question Engine design note based on the first dispute-practice research pass over one sanitized three-page residential lease. This note records a product/architecture discovery; it does not replace canonical state, implement runtime behavior, or promote the attached research artifact into production knowledge.

## 1. Why this layer exists

A strong contract parser can already summarize clauses, dates, amounts, and obvious inconsistencies. The product needs a deeper internal layer that answers a different question:

> If this mechanism later becomes disputed, what facts, evidence, procedure, and verified rules usually determine the practical outcome?

That depth should influence what the product notices and asks, but it should usually remain internal. User-facing output should stay short, neutral, and practical.

## 2. Provisional responsibility split

Keep four responsibilities separate:

```text
privacy-validated sanitized contract material
→ Contract Parser / Contract Facts
→ Dispute / Practice Engine
→ Question Engine
→ Safe Output
```

### Contract Parser / Contract Facts

Owns only what the contract itself supports:

- clause/mechanism presence;
- amounts, dates, notice periods, blanks, contradictions, and references;
- security-instrument type and printed mechanics;
- contract-defined party roles;
- missing appendices or unresolved handwriting dependencies.

It must not silently repair contradictions or infer disputed external facts.

### Dispute / Practice Engine

Provides internal research context for a verified contract mechanism. It may contain:

- applicability-checked statutory rules from the maintained statutory layer;
- verified case-law patterns;
- landlord-favorable and tenant-favorable factual patterns;
- procedural routes such as ordinary civil claims, tenant-eviction proceedings, or cheque execution/opposition;
- evidence patterns that repeatedly matter in disputes;
- explicit confidence/source-quality metadata.

It does **not** produce a free-form legal conclusion and must not be treated as the source of truth merely because a model generated a structured research result.

### Question Engine

Uses contract facts plus validated practice context to ask the minimum number of questions whose answers materially change:

- the contract interpretation branch;
- the applicable mechanism;
- a practical-risk assessment;
- a deterministic calculation;
- a relevant evidence/document dependency.

The normal product mode is pre-signing contract review. Questions that only make sense after a dispute already exists — for example, whether an execution warning was received, whether keys were later returned, or whether a lawsuit was filed — belong to a separate future dispute-support mode and must not leak into the ordinary pre-signing inventory.

Universal reminders remain separate from Question Engine questions.

### Safe Output

Translates the validated result into short plain Russian.

Default output should explain:

1. what the contract provides;
2. the practical consequence or uncertainty;
3. at most one useful clarification question when needed.

Case names, court citations, procedural detail, and statutory analysis are internal provenance by default. They may support an optional source/drill-down view later, but should not dominate the main report.

## 3. Practice depth should not become user-facing legal advice

The internal engine may know that similar disputes have turned on notice, proof of debt, dated photographs, mitigation, or the exact instrument presented for collection. The main screen usually does not need to say which court decided which case.

Preferred transformation:

```text
verified law + verified case patterns + procedure + evidence patterns
→ internal practical-risk model
→ short contract explanation / clarification question
```

Not:

```text
case-law research
→ mini legal opinion shown directly to the tenant
```

Existing user-facing boundaries remain binding: no safe-to-sign verdict, no prediction of who wins, no instruction to sue/refuse payment/sign/not-sign, and no categorical enforceability/invalidity conclusion unless a separately approved deterministic rule supports that exact bounded statement.

## 4. Security-cheque example

A security cheque illustrates why this layer is useful.

Contract-fact extraction should resolve, where visible:

- instrument type;
- amount;
- date or blank date;
- payee or blank payee;
- printed authority to complete missing particulars;
- contractual realization grounds;
- notice/cure wording;
- return trigger/deadline;
- conflicting references to another security instrument.

The practice layer may then keep separate questions such as:

```text
bank/instrument mechanics
!= contractual authority to realize
!= existence and amount of underlying debt
!= execution/opposition procedure
```

The ordinary pre-signing Question Engine should only surface unknowns that the user can resolve now and that change the analysis, for example whether date/payee fields are blank or whether a separate security document exists.

A later dispute-support mode could ask different questions, such as whether an execution warning was served. Those are not the same product question inventory.

## 5. Research-source and promotion rules

Model-assisted research output is evidence-discovery material, not authority.

Before a case/rule becomes production knowledge:

1. verify the cited source actually exists and matches the claimed proposition;
2. prefer official law/government/court material where available;
3. record whether a case is residential or only a commercial analogy;
4. distinguish verified holdings from database summaries or research leads;
5. preserve material outcomes that favor either side;
6. keep applicability, effective date, and non-derogation checks separate from contract facts;
7. downgrade or exclude claims that cannot be verified with sufficient confidence.

A mechanism discovered in one contract is not automatically promoted into the permanent deterministic inventory. Repeated occurrence across independent contracts plus product review is the preferred promotion signal.

## 6. Ranking is required before user output

A dispute/practice map can contain many technically valid mechanisms. The product must not give every mechanism equal visual weight.

Ranking should eventually consider at least:

- financial exposure;
- ability to trigger collection/possession consequences;
- ambiguity or missing required values;
- interaction with other clauses;
- probability that the issue matters before signing;
- confidence in the source evidence.

Exact severity thresholds remain unfrozen and require calibration across more contracts.

## 7. First research artifact

The repository research artifact:

`research/question_engine/dispute_practice/rental_dispute_map_il_v1_unverified.json`

is intentionally classified as:

```text
UNVERIFIED_RESEARCH_ONLY_DO_NOT_USE_FOR_PRODUCTION_RULES
```

It is a sanitized model-assisted first pass from one contract. It may be used to discover candidate mechanisms, evidence patterns, procedure branches, and source leads. It must not be imported into runtime code, cited as authority, or used to create deterministic product rules until its source claims are independently audited.

The repository copy removes/generalizes contract-specific identifying data and contains no raw page images or raw OCR.

## 8. Effect on current implementation order

This note does not change the canonical active track or replace the current Question Engine inventory sequence.

The immediate implementation should remain small. The practice layer is a clean boundary to reserve while the deterministic inventory is built; it is not authorization to implement a full case-law engine, scraper, external research service, vector database, or runtime legal-research integration in the current PR sequence.

The next research step is to repeat the same dispute-practice analysis on a substantially larger sanitized contract, compare the two mechanism maps, and only then decide which recurring practice patterns deserve promotion into maintained Question Engine knowledge.
