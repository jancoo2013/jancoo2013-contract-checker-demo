# Question Engine — Cross-contract dispute/practice classification v1

Status: current Question Engine research/design context. This document records what survived comparison of two independent sanitized residential-lease analyses. It does **not** promote case-law propositions into runtime legal rules and does not change the canonical implementation step.

## 1. What changed after the second contract

PR #243 reserved a four-layer boundary:

```text
Contract Facts
→ Dispute / Practice Engine
→ Question Engine
→ Safe Output
```

The second, substantially larger lease confirmed that this boundary is useful and that the product should organize practical knowledge around recurring **dispute mechanisms**, not around a flat catalogue of scary clauses.

Two-contract recurrence is only a signal that a mechanism family deserves maintained product attention. It is **not** evidence that every associated legal proposition, case summary, severity label, or user-facing sentence is production-ready.

## 2. Classification vocabulary

Use three product-research classes:

- `CORE` — mechanism family recurred independently and materially changes pre-signing analysis; reserve a stable place for it in maintained product knowledge.
- `CONDITIONAL` — important when triggered by contract facts, but not yet sufficiently recurring/generalized to occupy the universal core.
- `RESEARCH_ONLY` — useful provenance, case/evidence lead, or dispute-state detail that must not drive ordinary pre-signing runtime yet.

Additional qualifier:

- `CORE_FACTS_CONDITIONAL_PRACTICE` — extracting the contract facts is core, but deeper practice analysis is only triggered when the contract actually uses the relevant mechanism.

These labels classify **product mechanisms**, not legality, enforceability, likely court outcome, or advice.

## 3. CORE mechanism families after two contracts

### 3.1 Security and enforcement — CORE

Do not model `security` as one generic deposit field.

The maintained family must preserve distinct instruments and mechanics, including where present:

- ordinary rent cheques;
- security cheque / `צ'ק ביטחון`;
- promissory note / `שטר חוב`;
- guarantors;
- open utility cheques;
- cash/bank guarantee/deposit if a future contract uses them.

For each instrument, the contract-fact layer should be capable of resolving or explicitly leaving unknown:

```text
instrument type
amount
payee
blank date
blank amount/payee
transfer restriction
completion authority
contractual realization grounds
notice wording
cure wording
return trigger/deadline
linked separate document
```

The practice layer must keep separate:

```text
bank/instrument mechanics
!= contractual/statutory authority to realize
!= existence and amount of underlying debt
!= execution/opposition procedure
```

A recurring pre-signing question is justified only when the answer changes one of these branches. The actual instrument image may therefore be a necessary evidence dependency even when the lease text is readable.

### 3.2 Early exit + replacement tenant — CORE

Analyze as one mechanism system, not independent clauses:

```text
full-term payment wording
+ replacement-tenant route
+ landlord approval standard
+ assignment/sublet language
+ mitigation/re-letting facts
+ termination consequences
```

The product must not reduce this to `early exit allowed: yes/no`.

Pre-signing output should describe the contract's practical structure. Questions about a replacement candidate already proposed, keys already returned, actual re-letting date, or reasons already given for refusal belong to future dispute-support mode, not the ordinary Question Engine.

### 3.3 Financial sanctions and overlap — CORE

Recurring analysis must keep separate:

- ordinary rent/principal;
- late interest/indexation;
- daily holdover compensation;
- fixed agreed damages after breach/cancellation;
- actual repair/utility losses;
- security realization.

The internal engine must map each claimed mechanism by:

```text
trigger
amount/formula
start date
end date
harm/head of loss
possible overlap with another mechanism
```

Never convert this family into the user-facing rule `large penalty => court will reduce it`. Case-law review showed that both enforcement and reduction occur depending on the mechanism and facts.

### 3.4 Condition / AS-IS / defects / damage evidence — CORE

Treat these as one chronology/evidence system:

```text
entry baseline
→ known/pre-existing defect
→ event or deterioration
→ notice
→ repair responsibility
→ exit condition
→ contemporaneous proof
```

The contract parser should detect AS-IS language, condition acknowledgments, normal-wear exceptions, repair allocation, painting/restoration duties, referenced condition appendices, and signed inventory.

The ordinary Question Engine should prefer concrete missing dependencies such as a referenced condition appendix over generic advice questions.

### 3.5 Termination + cure + notice + physical eviction distinction — CORE

Cross-clause analysis is required where one clause grants broad cancellation rights and another sets a cure period or notice mechanism.

The internal system must keep distinct:

```text
contractual breach trigger
cure/notice mechanics
contract cancellation
right to demand vacancy
physical eviction procedure
```

Safe Output must never translate a contractual phrase such as `immediately vacate` into a claim that the landlord may physically remove the tenant without the required process.

### 3.6 Option / renewal mechanics — CORE, interpretation remains conditional

The recurring product task is to identify whether renewal has a complete mechanism:

- duration;
- price/formula;
- activation notice;
- deadline;
- whether new landlord consent is required;
- any addendum/external writing dependency.

The family is `CORE` because both contracts produced material renewal ambiguity. A specific conclusion that a clause creates a unilateral legal option remains conditional on exact wording and verified law/practice.

### 3.7 Utilities and occupancy charges — CORE_FACTS_CONDITIONAL_PRACTICE

Always extract who bears rent-adjacent current charges and any advances/reconciliation formula.

Deeper practice analysis is triggered only when the contract introduces a special mechanism such as:

- shared/central meter;
- landlord-calculated allocation;
- monthly advances plus later reconciliation;
- open utility security cheques;
- unusual building/common charges.

A generic utility clause alone should not consume major report space.

## 4. High-value CONDITIONAL mechanisms

### 4.1 Broad no-setoff clause — HIGH CONDITIONAL

Trigger on wording equivalent to `אין לקזז` / `לא יהיה רשאי לקזז`.

This can interact with separate statutory repair/setoff rules, but production output must remain gated by applicability/effective-date/non-derogation verification. Do not render a categorical invalidity conclusion from wording alone.

### 4.2 Shared-meter accounting — CONDITIONAL

The useful product model is evidentiary/accounting first:

```text
supplier bill
+ start/end readings
+ allocation formula
+ occupied-unit data where relevant
+ advances already paid
+ upward/downward reconciliation rule
```

The current research base is not dense enough to create a general court-outcome rule for this mechanism.

### 4.3 Landlord access — CONDITIONAL

Detect access purpose, advance notice/coordination, reasonable-time language, frequency, and any entry-without-tenant wording. Do not promote ordinary access boilerplate into a major warning unless the contract materially broadens it.

### 4.4 Alterations/restoration — CONDITIONAL

Detect prior-written-consent requirements, landlord ownership of improvements, and restoration-at-tenant-cost language. Promote only when the mechanism materially increases exit exposure or conflicts with other clauses.

### 4.5 Third-party indemnity — CONDITIONAL

Broad indemnity is not enough for a universal warning. If triggered, preserve causation, scope, proof of payment/loss, and landlord-controlled/structural causes as separate questions.

### 4.6 Inventory / handwriting dependency — CONDITIONAL evidence mechanism

A signed inventory can materially define the exit baseline. Handwritten quantities or values must remain `HANDWRITING_DEPENDENCY` until manually confirmed; OCR/LLM reconstruction is prohibited.

## 5. What should usually stay out of the main report

Unless contract-specific wording changes the practical mechanism, suppress or heavily compress:

- generic neighbor/noise obligations;
- generic integration/precedence boilerplate;
- routine addresses for notices as a standalone risk;
- `שכירות בלתי מוגנת` after one short orientation explaining that it is not synonymous with no rights;
- case names, court citations and procedural detail;
- questions that only make sense after a dispute has already occurred.

The product should rank mechanisms, not reward every clause for existing.

## 6. Question Engine consequence

The second contract produced many analyzable mechanisms but still only a small number of legitimate pre-signing user questions.

Strong candidate question classes now include:

1. missing security-instrument fields that change instrument mechanics;
2. existence/scope of a separately referenced `שטר חוב` or guarantor document;
3. named payee/restrictions on open utility cheques;
4. existence of a referenced condition/defect appendix;
5. missing renewal activation rule or external addendum;
6. direct/sub-meter versus landlord-controlled utility allocation;
7. manual confirmation of a legally relevant handwritten value.

Do **not** move the following into ordinary pre-signing Question Engine merely because they matter in litigation:

- whether an execution warning was received;
- when keys were later returned;
- whether the apartment was later re-let;
- which replacement tenant was already proposed;
- whether a lawsuit was filed;
- what damage was discovered after move-out.

Those belong to a separate future dispute-support mode.

## 7. Promotion and verification rules

After two contracts, mechanism-family promotion and legal-rule promotion must remain separate.

A mechanism may be classified `CORE` because it recurred and materially changes product analysis. Before any associated legal/case proposition becomes production knowledge:

1. verify the actual source and exact proposition;
2. resolve statutory applicability and effective date for the contract date;
3. distinguish residential decisions from commercial analogies;
4. preserve materially landlord-favorable and tenant-favorable outcomes;
5. separate holding from secondary-database summary;
6. retain confidence/source-quality metadata;
7. keep safe user wording materially narrower than internal legal research.

A future third/fourth contract should be used primarily as a **coverage test**: does the existing classification explain the new mechanisms, and which genuinely new family appears? It should not restart the taxonomy from zero.

## 8. Effect on implementation order

This classification does not authorize a dispute-practice runtime, scraper, vector database, external research service, live legal search, UI redesign, or provider integration.

The canonical next bounded implementation remains:

`question-engine-core-inventory-economic-v1`

That implementation may use this document only to keep the first economic inventory aligned with the now-confirmed product mechanism families. It must remain small and deterministic.