# Question Engine — Discovery Log and Working Design

Status: active working design notebook for the `question-engine-development` track.

This document records important product discoveries, working hypotheses, current Question Engine design conclusions, and how those conclusions change as more real rental contracts are studied.

It is **not** the canonical operational state. `docs/OCR_PROJECT_STATE.md` and `docs/OCR_PROJECT_STATE.json` remain authoritative for `active_track`, `next_step_id`, blockers, and the single permitted next implementation step. Binding privacy/security/architecture rules remain in `AGENTS.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, and the privacy/OCR contracts.

The purpose of this file is narrower: prevent Question Engine product knowledge from being scattered across chats, PR descriptions, and the much larger OCR continuity document.

## 1. Product objective

The Question Engine should help a Russian-speaking tenant understand what a Hebrew rental contract **actually means in practice**.

The target is not a clause-by-clause paraphrase and not an unconstrained `LLM: find risks` prompt.

A useful result should answer two successive questions:

1. **What kind of agreement is this and how does it work overall?**
2. **What specifically deserves the tenant's attention, and why does it matter in real life?**

The system should behave as a translator of consequences rather than as a contract editor, judge, or AI lawyer.

## 2. Current architecture hypothesis

The current preferred architecture is a deterministic Question Engine layered around an LLM semantic reader:

```text
privacy-validated sanitized contract material
→ deterministic core question inventory
→ LLM extracts structured facts and relationships
→ deterministic conditional follow-up questions
→ cross-clause interaction checks
→ catch-all search for material issues not yet covered by the inventory
→ deterministic/Python schema + evidence + consistency validation
→ concise human-readable overview essay
→ focused "what to pay attention to" explanations
→ Russian user-facing report
```

Key principle:

> The deterministic engine does not need to understand Hebrew law or natural language by itself. Its job is to organize the investigation. The LLM reads and interprets the contract; code controls what must be investigated, validates structure/evidence, and prevents unsupported output from silently becoming the final answer.

This keeps the semantic flexibility of an LLM without allowing the model to decide from scratch what a complete contract analysis should contain.

## 3. Responsibility split

### Deterministic Question Engine / Python

Should eventually own:

- the recurring question inventory;
- conditional branches;
- required completeness checks;
- cross-clause follow-up selection;
- arithmetic and ratio calculations when source values are verified;
- status/schema validation;
- evidence-reference validation;
- detection of missing required answer fields;
- deterministic comparisons and consistency checks where possible;
- deciding which verified findings are eligible for the final report.

### LLM

Should eventually own:

- reading sanitized Hebrew contract language;
- mapping clauses to semantic topics;
- extracting structured facts;
- explaining practical consequences;
- identifying relationships, exceptions, and tensions between clauses;
- answering targeted follow-up questions;
- proposing novel material issues in the catch-all pass;
- composing the final human-readable explanation only from allowed/verified findings.

The LLM is not the source of truth. Sanitized contract evidence is the source of truth.

## 4. Do not start with "find risks"

The first model pass should establish a structured map of what the agreement says.

The system should not pressure the model to find a problem in every category. A legitimate result can be that a topic is absent, neutral, balanced, or unresolved.

Provisional answer states:

```text
FOUND
NOT_FOUND
AMBIGUOUS
HANDWRITING_DEPENDENCY
CLAUSE_PRESENT_VALUE_BLANK
```

`NOT_FOUND` is a valid result, not a model failure.

`CLAUSE_PRESENT_VALUE_BLANK` is distinct from `NOT_FOUND`: a contract may clearly provide a mechanism such as an option, security instrument, rent amount field, or notice period while leaving the actual value blank.

## 5. Handwriting rule

Handwriting must not be semantically reconstructed, guessed, or inferred from context.

If an answer depends on handwritten content, the Question Engine should surface an explicit unresolved dependency rather than asking the LLM to decipher or invent the value.

Example semantic outcome:

```text
security_structure = FOUND
security_type = FOUND
security_amount = HANDWRITING_DEPENDENCY
```

A large part of a contract may still be meaningfully analyzed even when some handwritten dates, names, amounts, or special terms are unavailable.

## 6. Blank-field rule

Unfilled templates are valid Question Engine inputs.

The engine must distinguish:

- a topic that does not exist in the contract;
- a printed clause whose value is blank;
- a value that exists but is hidden/redacted as PII;
- a value that exists only in handwriting and is intentionally unresolved;
- an ambiguous or internally inconsistent value.

Never infer a missing number merely because the surrounding clause makes one likely.

## 7. Party-role granularity

De-identification should preserve the role granularity actually used by the contract.

If several named people are defined collectively and the operative text later refers only to `המשכיר` or `השוכר`, keep the collective role. Do not create `TENANT_1`, `TENANT_2`, etc. solely because several names appear in the header.

Introduce individual placeholders only where operative contract language materially distinguishes those people in rights, obligations, guarantees, payment behavior, or another legally relevant way.

This rule was confirmed by the first golden fixture: the contract was collective almost everywhere but contained one later clause that materially distinguished individual tenant members.

## 8. Core domains are recurring; treatment is what matters

Across contracts, a relatively stable set of domains repeats:

- lease term and dates;
- rent and payment mechanics;
- rent increases/indexation;
- renewal/option;
- early exit and replacement tenant mechanisms;
- late payment and sanctions;
- security/deposit/guarantee instruments;
- utilities, municipal charges, and running costs;
- repairs and ordinary wear;
- use of the property, guests, assignment, and subletting;
- alterations and restoration duties;
- landlord access;
- liability and third-party claims;
- handover/return condition and holdover;
- missing appendices or referenced documents;
- internal inconsistencies, blank fields, and broken references.

However, the product value is **not** in asking banal questions such as "Who pays utilities?" and repeating the answer.

The important question is:

> How is this topic regulated in this contract, what mechanisms or safeguards exist, who carries the practical risk, and how do related clauses modify one another?

Two contracts can cover exactly the same topic but produce opposite practical outcomes.

## 9. Cross-clause interaction is a first-class analysis step

A single clause often cannot be interpreted usefully in isolation.

The Question Engine therefore needs explicit interaction checks.

Examples of the pattern:

### Early exit

If one clause says the tenant remains liable for rent after leaving, while another allows a replacement tenant under conditions, the system should ask how those clauses work together rather than reporting them separately.

### Repairs

If one clause says the landlord repairs ordinary defects, another contains an `AS-IS` declaration, and another separately regulates furniture/appliances, the system should determine what each rule applies to and whether one limits or qualifies another.

### Security

If the contract uses more than one security-instrument term, the engine should determine whether they are clearly separate instruments, synonyms used consistently, or an internal ambiguity.

### Internal references

If a clause points to another clause for an interest rate, notice rule, remedy, or definition, the engine should verify that the reference actually exists and means what the referring clause claims.

## 10. Novel-issue catch-all

A fixed taxonomy must not become a prison for the model.

After the recurring inventory and interaction passes, the engine should include one bounded catch-all question roughly equivalent to:

> Identify any material contractual mechanism, unusual condition, internal relationship, or practical consequence that a reasonable tenant should understand before signing and that was not already covered by the requested topics. Do not repeat already reported findings.

If the same novel issue appears repeatedly across independent contracts, it should be promoted from catch-all output into the permanent deterministic inventory or a conditional branch.

This is the current preferred way for the Question Engine to improve from accumulated real-contract experience without training a separate neural network.

## 11. Practical significance beats paraphrase

A user does not need a report dominated by statements such as:

- the landlord is the owner;
- the tenant rents the apartment;
- rent must be paid;
- the apartment must eventually be returned.

Those facts can appear when necessary for orientation, but they are not the analytical value of the product.

A useful explanation should surface consequences such as:

- a tenant may continue owing rent after moving out unless a replacement mechanism succeeds;
- an `AS-IS` declaration may make documentation of pre-existing defects especially important;
- a repair rule may treat the apartment itself differently from furniture or appliances;
- a security package may be large relative to monthly rent;
- several sanctions can stack for one payment default;
- a clause may forbid unilateral set-off even when the tenant believes money is owed back;
- a contract may grant a right but make it dependent on landlord consent in a way that materially weakens the apparent right.

## 12. Ratios and scale matter

The engine should not merely extract monetary values. It should use verified values to calculate useful context when that context changes practical understanding.

Example discovered from the first sample:

```text
security_amount / monthly_rent
```

A security amount can be formally stated correctly yet still be notable because it equals several months of rent.

The exact thresholds for user-facing severity are not yet fixed and should not be invented from a single contract. The deterministic layer may calculate the ratio first; interpretation rules can be calibrated from more examples and legal/product review.

## 13. Security instruments must be distinguished

Different security mechanisms must not be casually collapsed into one generic "deposit" concept.

Examples that may require separate treatment include:

- security cheque / `שיק ביטחון`;
- bank guarantee / `ערבות בנקאית`;
- promissory note / `שטר חוב`;
- cash deposit;
- guarantor obligations;
- post-dated or utility-specific cheques where relevant.

If a contract switches terminology inside what appears to be the same mechanism, the engine should flag the ambiguity instead of silently choosing one interpretation.

## 14. Internal inconsistencies are material findings

The engine should actively compare related values and definitions rather than assuming the contract is internally coherent.

Examples of useful deterministic/model-assisted checks:

- stated lease duration versus start/end dates;
- number of payment instruments versus stated term;
- option duration versus notice rule;
- security instrument named at creation versus instrument named at return;
- clause reference target exists and is semantically relevant;
- repeated values agree across sections;
- special conditions do not contradict standard-form text.

Do not silently "correct" the source. Preserve the inconsistency and explain its practical effect.

Context from outside the document may explain why an apparent inconsistency exists (for example, a contract that has already been renewed), but external context must remain distinguishable from what the contract itself proves.

## 15. User-facing essay comes before the attention list

The current preferred report order is:

1. a concise human-readable overview of how the agreement works overall;
2. a focused explanation of the most important points to pay attention to;
3. detailed per-topic/per-clause material when the user wants to go deeper.

The overview should not be a clause-by-clause summary. It should characterize the agreement's practical structure, for example:

- payment model;
- exit model;
- repair/responsibility allocation;
- security architecture;
- degree of landlord discretion;
- unusually restrictive or unusually tenant-friendly mechanisms;
- important internal inconsistencies.

We expect the exact essay algorithm to stabilize only after reviewing several materially different real contracts.

## 16. Mandatory explanation of "unprotected rental"

The product must never present `שכירות בלתי מוגנת` merely as "незащищённая аренда" without immediate plain-language context.

The phrase can alarm a Russian-speaking user and falsely suggest that the tenant has no legal protection.

Whenever this concept appears in user-facing output, explain immediately that it refers to the lease **not being under the special protected-tenant (`דייר מוגן`) regime**. It does not by itself mean that the tenant has no ordinary contractual or statutory rights.

This explanation should be attached to the term, not hidden later in a glossary.

## 17. Balanced analysis, not automatic hostility to the landlord

The engine should describe how rights and burdens are distributed rather than assume every landlord-favoring clause is improper.

A useful analysis can say that one contract is more restrictive than another, or that a mechanism gives the landlord substantial leverage, without accusing the landlord or agent of deception or illegality.

Likewise, tenant-friendly safeguards should be surfaced when present, such as:

- explicit ordinary-wear protection;
- landlord repair duties;
- self-help repair/reimbursement mechanisms;
- reasonable-notice access restrictions;
- permitted assignment or subletting;
- notice/cure requirements before enforcement of security.

The goal is to explain consequences and balance, not maximize the count of red flags.

## 18. Provisional structured-answer pattern

The exact schema is not frozen, but a likely direction is a small status envelope plus topic-specific structured fields and evidence references.

Illustrative shape only:

```json
{
  "question_id": "EARLY_EXIT",
  "status": "FOUND",
  "answer": {
    "tenant_may_leave_early": false,
    "continuing_payment_required": true,
    "replacement_tenant_path_exists": true
  },
  "evidence": ["clause_8", "clause_9"],
  "ambiguities": []
}
```

The final schema must avoid asking the LLM to generate exact Hebrew quotations as evidence. Evidence should eventually resolve to deterministic sanitized source references.

## 19. Current development method

Do not try to freeze the complete Question Engine taxonomy from one contract.

Current preferred development loop:

```text
real contract under owner control
→ sanitized/controlled semantic reading
→ human-quality analysis
→ record what the analysis needed to notice
→ compare against previous contracts
→ separate recurring domains from one-off mechanisms
→ promote stable discoveries into deterministic questions/branches
→ retain catch-all for genuinely new mechanisms
```

Several varied contracts are more valuable at this stage than a prematurely large universal question list.

## 20. Statutory baseline is a separate evidence layer

Contract analysis should not stop at “the contract says X” when current Israeli rental law materially limits, supplements, or contradicts the contractual wording.

The preferred architecture now has a distinct statutory comparison layer:

```text
contract facts
→ Question Engine semantic map
→ statutory applicability gate
→ effective-date-aware statutory baseline
→ contract-vs-statute comparison
→ cross-clause + legal interaction analysis
→ user-facing explanation with section citation
```

The statute used for this baseline is `חוק השכירות והשאילה, התשל״א-1971` (Rental and Loan Law, 1971). The reform commonly called `שכירות הוגנת` / “Fair Rental Law” should be described accurately as the 2017 amendment to that law, not as a separate timeless statute. The Knesset records Amendment No. 1 as effective from `2017-09-17`.

Important design rules:

- **Contract fact and statutory rule are different evidence types.** The model must not blend them into one unsupported narrative.
- **Applicability comes first.** Before invoking the special residential-rental protections, check the exclusions and scope rules in section `25טו`.
- **Non-derogation must be explicit.** Section `25יד` is a central meta-rule: some statutory protections cannot be contracted away, while others may only be varied in the tenant's favor. Do not assume every statutory section is mandatory.
- **Use exact section citations.** When supported, user-facing analysis should say, for example, “§25ח” or “§25י”, not vaguely “the 2017 fair-rental law”.
- **Prefer statutory conflict language over accusations.** A finding should normally say “potential conflict with §X” or explain that the contract may not override the statutory rule, rather than automatically declare the landlord or agent unlawful.
- **Current law, not 2017 memory, is authoritative.** The official Knesset database currently records later amendments, including a 2026 amendment. Therefore the system needs effective-date versioning.
- **If freshness cannot be verified, degrade safely.** It is better to provide contract-only analysis than to assert an outdated statutory rule.

A dedicated maintained reference now lives in `docs/QUESTION_ENGINE_STATUTORY_BASELINE_V1.md`.

It intentionally does **not** vendor an unversioned full copy of the law. A static text dump is dangerous because the law changes and some wording can have future commencement dates. The baseline instead stores official source metadata, relevant section IDs, operative engineering summaries, applicability/non-derogation rules, and a refresh procedure.

A future deterministic implementation may add immutable statutory snapshots, but only with explicit `effective_from` / superseded metadata and a source-refresh process.

## 21. Open design questions

Not yet frozen:

- exact core question inventory;
- exact conditional-branch representation;
- exact structured answer JSON schema;
- exact evidence-reference format;
- how many model passes are optimal;
- when a cross-clause check should be triggered automatically;
- how to rank findings without turning the product into a legality verdict;
- how to calibrate "unusual", "strict", or "material" against Israeli rental practice;
- which comparisons should be deterministic ratios/rules versus LLM interpretation;
- exact final essay construction algorithm;
- exact statutory-applicability schema and effective-date representation;
- how to separate simple statutory comparison from questions that require case law / legal interpretation;
- how often the statutory baseline must be refreshed in production;
- how many diverse golden/sample contracts are enough before freezing v1 taxonomy.

## 22. Change history

### 2026-08-24 — Question Engine track pivot (PR #234)

- Surya/cloud OCR infrastructure frozen as a prioritization decision rather than a proven OCR failure.
- Question Engine becomes active development track.
- Engine must remain OCR-provider-independent.
- Development begins from sanitized owner-controlled contract material.
- Handwriting inference prohibited.
- Party roles must remain directionally meaningful after de-identification.

### 2026-08-25 — Binding-doc synchronization (PR #235)

- Binding architecture/privacy docs synchronized to the Question Engine pivot.
- Collective role granularity rule clarified: do not invent numbered tenants unless operative language distinguishes them.

### 2026-08-25 — First golden fixture (PR #236)

- First sanitized printed-text golden contract committed.
- Real example confirmed that collective party roles can later contain a narrow individual exception.
- Source blanks and internal inconsistencies are preserved rather than normalized.
- Next canonical implementation step remains the initial question inventory.

### 2026-08-25 — Multi-contract analysis discoveries (working conclusions before this log)

The next contracts reviewed in product discussion produced the following design conclusions:

- unfilled templates require a distinct `clause present / value blank` state;
- the same recurring topic can be regulated in radically different ways, so analysis must focus on mechanism and consequence rather than topic presence;
- user-facing output should begin with a useful overall essay before listing attention points;
- cross-clause interaction checks are central, not optional;
- ratios such as security-to-rent can be more informative than raw amounts;
- different security instruments must remain semantically distinct;
- `שכירות בלתי מוגנת` must always receive an immediate non-alarming explanation;
- the deterministic Question Engine should organize the investigation while the LLM remains the semantic reader;
- a bounded novel-issue catch-all should prevent the fixed taxonomy from missing genuinely new mechanisms.

This section records design conclusions only. It intentionally contains no source photographs, recoverable PII, raw OCR, handwritten values, or other restricted material from the reviewed contracts.

### 2026-08-25 — Same-template-family variation and special-condition discovery

A further public blank rental template showed that visually and structurally similar contracts can belong to the same template family while producing materially different practical outcomes after relatively small edits, inserted subclauses, blank fields, or special conditions.

New working conclusions:

- **Never analyze by template recognition alone.** Recognizing a familiar form may help orient the model, but every concrete version must still be read end-to-end. Small edits can change renewal price, early-exit rights, notice periods, security enforcement, repair duties, or other material terms.
- **Template similarity is not semantic equivalence.** The engine should treat template-family identity as optional metadata, never as evidence that a clause has the same meaning as in another specimen.
- **Early-exit mechanisms must be composed.** A contract can simultaneously say that rent remains due after early departure, permit a replacement tenant under conditions, and contain a separate mutual termination mechanism with its own notice period. These are one decision structure, not three unrelated findings.
- **Rights with an unfixed economic term need a dedicated warning.** For example, a renewal option may exist while the renewal rent is not fixed and is instead left for later determination subject only to a floor. `option_exists = true` is insufficient; the engine must ask how the renewal price is determined and whether the right is economically predictable.
- **Broken internal references deserve a deterministic check.** If a clause refers to a missing subclause or nonexistent target, return an explicit `BROKEN_INTERNAL_REFERENCE`-type finding rather than ignoring the reference or inventing the missing rule.
- **Blank sanctions remain meaningful structures.** A holdover penalty clause with an unfilled amount is not absent: the obligation structure is present while the monetary value is unresolved.
- **Special/additional conditions are first-class evidence.** Individually inserted obligations such as pre-handover cleaning, repair, appliance checks, keys/remotes, painting, or other apartment-specific work may materially affect the tenant even though they fall outside the core taxonomy. The catch-all pass must explicitly search for such bespoke obligations.
- **Standard text and bespoke additions must be compared.** The engine should ask whether later special conditions narrow, override, supplement, or contradict generic template language.
- **User-facing analysis should explain the combined practical path.** For example, instead of separately stating "rent remains due", "replacement tenant is allowed", and "mutual termination exists", explain what practical routes the tenant actually has to leave early and what conditions attach to each route.

This update records only generalized Question Engine design conclusions from a public blank template. No source images, personal data, filled contract values, or copyrighted template text are stored in the repository.

### 2026-08-25 — Statutory-baseline architecture discovery

Product direction now explicitly requires frequent section-level statutory grounding where it materially strengthens the user's understanding or exposes a contract-vs-law tension.

New conclusions:

- the system should cite the current Rental and Loan Law by exact section when possible;
- “Fair Rental Law 2017” is user-friendly context, but the legal source of truth is the current consolidated `חוק השכירות והשאילה, התשל״א-1971`;
- statutory applicability, effective date, and non-derogation must be resolved before stating that a contract term is overridden;
- section `25יד` is a central meta-rule for determining when protected residential provisions cannot be worsened against the tenant;
- section `25טו` is a mandatory applicability gate;
- contract-only findings such as security size and statutory-cap findings are separate analyses and must not be conflated;
- legal references should provide a practical argument the tenant can understand and discuss with an agent/landlord, without turning the product into an unsupported legality verdict;
- the maintained statutory map is stored separately in `docs/QUESTION_ENGINE_STATUTORY_BASELINE_V1.md` and must be refreshed against the official Knesset source.
