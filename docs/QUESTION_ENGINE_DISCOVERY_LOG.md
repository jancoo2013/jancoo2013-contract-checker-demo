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

### 2026-08-25 — Reasonableness standards and practical-positioning discovery

The Tel Aviv municipal template exposed a recurring legal-language problem: terms such as `reasonable time`, `reasonable grounds`, `reasonable notice`, and `reasonable conditions` are intentionally open-textured rather than numerically fixed.

Engineering conclusions:

- **Do not present “reasonable” as a concrete promise.** If the contract or statute uses an open standard, the user-facing report must say that the boundary is context-dependent.
- **Explain who ultimately resolves a dispute.** If the parties disagree about whether conduct was “reasonable”, the question may ultimately require legal interpretation and, if the dispute escalates, a court or other competent tribunal can decide it from the circumstances. A court decision applying “reasonable time” under the Rental and Loan Law confirms that the inquiry turns on case-specific factors rather than a universal number.
- **Prefer exact numbers when the statute supplies them.** For example, where the 2017 residential-rental amendment replaced a general “reasonable time” idea with a hard outside limit such as 30 days or 3 days for certain repairs, the report should surface the numeric statutory protection rather than leave the user with the vaguer contract wording.
- **Create an explicit open-standard marker.** A likely future finding type is `OPEN_ENDED_REASONABLENESS_STANDARD`, carrying the source clause, affected right/obligation, whether the statute narrows it with a numeric limit, and whether legal interpretation may be required.
- **Do not imply that “reasonable” means whatever the landlord, agent, tenant, or model personally thinks is reasonable.** It is a legal standard applied to circumstances, not a subjective preference.

The same municipal-template review also clarified product positioning:

- **Balanced public templates are reference material, not realistic rewrite targets.** The product should not assume an agent or landlord will replace their contract with the Tel Aviv municipal form merely because it is more balanced.
- **The practical job is to improve the tenant's negotiating and decision position inside the actual contract they received.** The report should identify which clauses matter, what the current law adds or limits, and which specific points are worth questioning or negotiating.
- **Do not encode a presumption of bad faith by landlords or agents.** Real contracts can be strongly landlord-favoring, but the engine must describe the mechanism and evidence rather than assume a universal intent to exploit the tenant.
- **Use public balanced templates as comparative context only.** They can help calibrate what a more balanced arrangement looks like, but statutory analysis must come from current law, and the user's actual contract remains the primary source.
- **Source-version freshness applies to public templates too.** A municipal URL can continue exposing an older template after a newer version exists; template age/version must be tracked before using it as current-market context.

This update records generalized Question Engine design conclusions only; it does not store the municipal contract text or any user contract data.

### 2026-08-26 — Legacy-template and statutory-comparison discovery

A public residential lease template published in 2010, before the 2017 residential-rental reform, is useful not as a current legal benchmark but as evidence of how older landlord-oriented drafting patterns can continue to circulate in copied Word/PDF forms long after the statutory framework changes.

New engineering conclusions:

- **Template age is context, not a legality verdict.** A clause is not invalid merely because it came from an old form. Every concrete clause still requires current-law comparison, applicability analysis, and effective-date handling.
- **Literal contract effect and current statutory effect must be represented separately.** A useful internal distinction is `CLAUSE_LITERAL_EFFECT` versus `STATUTORY_EFFECT`. A clause can read as a complete waiver or broad landlord right while current law narrows, supplements, or overrides its practical operation.
- **Legacy clauses strengthen the need for effective-date-aware statutory comparison.** The engine should be able to explain that wording may have been drafted under an earlier legal environment and can remain in circulation even when later law changes the tenant's current rights.
- **Repairs are a strong example of contract-vs-statute narrowing.** A legacy clause that assigns nearly every defect to the tenant except a narrow infrastructure carve-out must be compared against current §25ח, which generally distinguishes defects caused by unreasonable tenant use from other non-minor defects. If the protected residential regime applies and the clause worsens a non-derogable tenant protection, return a strong `POTENTIAL_STATUTORY_CONFLICT` candidate rather than merely paraphrasing the contract.
- **Broad `AS-IS`/waiver language must never be reported as total loss of rights without the statutory layer.** The engine should check the current rules on conformity, known/unknown defects, landlord knowledge, notice/cure, and remedies before explaining what the waiver can actually do.
- **Assignment/subletting requires precision rather than automatic invalidity.** Section §22 contains its own reasonableness/court mechanism, but it is not automatically covered by the same non-derogation logic as every protected residential section. An absolute contractual ban can therefore require `STATUTORY_INTERPRETATION_REQUIRED` rather than a simplistic “illegal clause” finding.
- **Broad payment catch-alls need statutory scoping.** Phrases equivalent to “all other charges connected with the apartment” should be compared against the more specific tenant-charge categories in §25ט. The user-facing report should explain that broad drafting does not automatically make every owner/building cost payable by the tenant.
- **Security enforcement needs multiple separate questions.** The engine must separately extract security type, amount, enforcement grounds, notice/cure procedure, return trigger, and return deadline. A legacy `ANY BREACH → security enforcement` rule should be compared against the enumerated current statutory grounds rather than treated as unrestricted merely because the contract says so.
- **Objective open standards and subjective counterparty standards are different risk classes.** `reasonable grounds`, `reasonable time`, or `reasonable conditions` refer to an external legal standard. Language equivalent to `to the landlord's satisfaction` makes the counterparty's satisfaction part of the mechanism and should receive a distinct marker such as `SUBJECTIVE_COUNTERPARTY_SATISFACTION_STANDARD`.
- **Statutory open standards remain open even when they protect the tenant.** If current law itself uses `reasonable notice` or `reasonable time`, the app must disclose that there is no universal numeric boundary unless another provision supplies one.
- **A missing contract deadline can be supplemented by statute.** Where the contract says only that security will be returned after obligations are fulfilled but current applicable law supplies an outside return deadline, use `STATUTE_SUPPLEMENTS_CONTRACT`. The statutory value must come from the effective-date-correct baseline rather than a hard-coded evergreen number.
- **External economic references are first-class dependencies.** Rent, interest, sanctions, or other obligations can depend on a foreign-currency exchange rate, CPI, bank overdraft rate, or another external variable. A likely future field/class is `EXTERNAL_VALUE_DEPENDENCY`, with source variable, fixing date, direction of exposure, and whether the resulting amount is deterministically computable.
- **Translate penalty formulas into money.** When verified source values allow it, Python should convert abstract sanctions such as a percentage of monthly rent per day into useful quantities such as `₪/day`, `₪/week`, `₪/30 days`, and `multiple_of_monthly_rent`. This is practical consequence translation, not legal interpretation.
- **Do not invent a statutory cap where none is identified.** A severe holdover penalty may be economically alarming without having a simple cap in the special residential-rental provisions. In that case report the contract fact and deterministic financial consequence, then use `LEGAL_INTERPRETATION_REQUIRED` if broader remedies/penalty law must be considered.
- **Ambiguous remedy interaction is not automatically contradiction.** If one section gives 15 days before a breach becomes fundamental while another provides a 7-day cure route for cancellation, first classify the relationship as an `AMBIGUOUS_REMEDY_INTERACTION` unless the text clearly makes both rules impossible to reconcile. The engine should not overstate ambiguity as contradiction.

The legacy-template comparison also sharpened the confidence model for statutory analysis. At minimum, the future engine should distinguish:

```text
DETERMINATE_STATUTORY_COMPARISON
OPEN_STATUTORY_STANDARD
LEGAL_INTERPRETATION_REQUIRED
```

These are not user-facing severity levels. They describe how mechanically certain the legal comparison is:

- `DETERMINATE_STATUTORY_COMPARISON` — applicability and effective-date checks pass and the relevant statutory rule is concrete enough for a bounded comparison;
- `OPEN_STATUTORY_STANDARD` — the governing rule itself depends on concepts such as reasonableness and the app must expose that uncertainty;
- `LEGAL_INTERPRETATION_REQUIRED` — the relationship between contract and law cannot safely be reduced to a deterministic rule without broader legal analysis, case law, or fact-specific judgment.

This confidence tier sits alongside, not instead of, outcome types such as `STATUTE_APPLIES_NO_CONFLICT`, `CONTRACT_MORE_TENANT_FAVORABLE`, `STATUTE_SUPPLEMENTS_CONTRACT`, `CONTRACT_NARROWER_THAN_STATUTE`, and `POTENTIAL_STATUTORY_CONFLICT`.

This update stores only generalized engineering conclusions from a public historical template and current statutory comparison. It does not copy the template text, store user contract material, PII, handwriting, or raw OCR.

### 2026-08-26 — Actionable-remediation UX and legal-advice boundary discovery

The Flamingo-template review and follow-up product discussion established that merely identifying a problem is not enough. The user must also understand what can realistically be discussed with the landlord or agent before signing, while the product must avoid presenting itself as individualized legal counsel.

#### Actionable remediation is a separate product layer

The preferred analysis path is now:

```text
finding
→ contract consequence
→ statutory comparison
→ legal-certainty / interpretation class
→ actionable discussion point
→ optional proposed wording for discussion
```

The system should not stop at `finding → explanation`. A strong user-facing result should answer both “what does this mean?” and “what can I raise with the landlord?”.

However, proposed wording must carry provenance and confidence. Do not use an internal label such as `STATUTE_ALIGNED_REWRITE`, which can imply that the system has produced a legally certified clause. Preferred internal categories are:

```text
STATUTE_GROUNDED_DISCUSSION_TEXT
NEGOTIATION_DISCUSSION_TEXT
LEGAL_REVIEW_RECOMMENDED
```

- `STATUTE_GROUNDED_DISCUSSION_TEXT` — a discussion text grounded in a concrete, applicability-checked, effective-date-correct statutory rule. It is still a proposal for discussion, not a guaranteed legally sufficient contract clause.
- `NEGOTIATION_DISCUSSION_TEXT` — a practical tenant-protective proposal where the law does not require that exact wording.
- `LEGAL_REVIEW_RECOMMENDED` — the issue depends on broader legal interpretation, case law, disputed facts, or an open standard; the product should not pretend to draft the legally correct clause.

If statutory applicability, effective date, non-derogation, or section freshness cannot be verified, the engine must not generate statute-grounded wording. It may still offer a clearly labeled negotiation proposal if doing so does not misrepresent the law.

#### Screen-level UX separation

The current preferred mobile flow separates understanding from negotiation:

```text
Screen 1 — overall result / orientation
Screen 2 — Russian essay analysis: what the contract means and what deserves attention
Screen 3 — Russian action plan: what specifically can be discussed with the landlord
```

Screen 2 should contain the explanatory essay and statutory context, not long negotiation templates.

Screen 3 should contain concrete Russian-language discussion cards. Each card should explain:

- what the practical problem is;
- why it matters;
- whether the point is grounded in a concrete statutory rule, is merely a negotiation safeguard, or requires legal review;
- what the user can ask to clarify or change.

User-facing provenance labels should be simple and explicit, for example:

```text
Основано на законе
Переговорное предложение
Требует юридической оценки
```

The product should use wording such as “Что стоит обсудить” / “Вариант формулировки для обсуждения”, not “Как исправить договор” / “Правильная редакция”, because the latter suggests a legal-certification role the product does not have.

#### Hebrew discussion text must be optional and secondary

The primary interface for the target user is Russian. Hebrew negotiation text should not remain permanently visible on the main screen, especially for a user who may be seeing Hebrew for the first time.

Preferred pattern:

```text
Russian discussion card
→ [Показать текст на иврите]
→ side sheet / drawer / bottom sheet with RTL Hebrew text
→ [Копировать] [Поделиться]
```

The Hebrew text is an optional payload for communication, not the primary explanation.

A copy action should be available directly next to the Hebrew phrase. On Android, a generic system share action is preferable to a hard-coded WhatsApp-only integration: the Android share sheet can surface WhatsApp, Telegram, SMS, email, and other installed apps without coupling the product to one provider.

#### Non-legal-advice product invariant

The product boundary should be enforced by architecture and output schema, not primarily by a footer disclaimer.

The system may say:

```text
Here is what the contract says.
Here is what the verified statute says.
Here is where the two appear to differ or leave uncertainty.
Here is a point you can discuss before signing.
```

The system must not claim:

```text
These are your final legal rights in a dispute.
This clause is definitely illegal/void unless a deterministic, applicability-resolved rule actually supports that exact conclusion.
You may safely ignore this obligation.
You will win/lose in court.
You should sue / refuse to pay / sign / not sign.
This is the legally correct final wording of the clause.
```

The Question Engine should keep three evidence/meaning layers separate:

```text
CONTRACT_FACT
STATUTORY_RULE
PRODUCT_EXPLANATION
```

Do not silently create a fourth LLM-owned `LEGAL_CONCLUSION` layer.

Contract evidence proves what the document says. The statutory layer provides verified legal context. The product explanation translates the practical consequence. None of those by itself authorizes the model to predict litigation outcomes or determine the user's complete legal position.

#### Deterministic gate before statute-grounded remediation

The LLM must not invent a legal rule and then write a Hebrew clause around it.

A statute-grounded discussion text should only become eligible after a deterministic/legal-reference gate has resolved, at minimum:

```text
candidate statutory topic
→ applicability gate
→ effective-date-correct section version
→ non-derogation / tenant-favor rule where relevant
→ legal-certainty class
→ allowed remediation type
```

If this gate fails, `STATUTE_GROUNDED_DISCUSSION_TEXT` is blocked.

If the result is `LEGAL_INTERPRETATION_REQUIRED`, the product should generally offer a question or negotiation direction rather than a purported “correct” replacement clause. Example direction: “Можно ли ограничить ответственность арендатора ущербом, возникшим по его вине?” rather than a claim that the application has rewritten the clause into its legally definitive form.

#### Do not personalize legal strategy

The product can personalize factual explanation to the contract, but should not turn user profile information into litigation or transaction strategy.

Avoid outputs such as:

- “С вашей зарплатой этот риск можно принять.”
- “В вашей ситуации лучше отказаться от сделки.”
- “Если хозяин уже подписал, можете просто не платить.”
- “Суд, скорее всего, будет на вашей стороне.”

The bounded product scope remains:

```text
what the contract says
→ what verified law may add / limit
→ practical consequence
→ what can be clarified or discussed
```

#### Disclaimer is secondary, not the safety mechanism

A concise product notice can state that the app helps explain the contract and potentially relevant statutory rules, does not determine the user's final rights in a concrete dispute, and does not replace a lawyer. That notice is useful, but it is not enough on its own.

The primary protection must be deterministic eligibility rules, schema validation, allowed output classes, provenance labels, and blocking of unsupported legal verdicts or overly strong remediation language before the final report is rendered.

This update records generalized product/Question Engine design conclusions only. It stores no contract text, user PII, handwriting, raw OCR, or individualized legal advice.

### 2026-08-26 — Current-template second-pass and plain-language discovery

Review of a current 2026 commercial residential-rental template confirmed that source recency and professional presentation do **not** imply that every clause is aligned with the current statute.

New engineering conclusions:

- **Source recency is not proof of statutory alignment.** A 2026 template can still contain wording that deserves comparison against current protected residential rules. Therefore `SOURCE_RECENCY != STATUTORY_ALIGNMENT` should be treated as a product invariant.
- **Do not flag a defined term before resolving its definition and related clauses.** A phrase such as `any fundamental breach` can look much broader than it really is. The engine must first identify every clause that defines `fundamental breach`, then compare the resulting concrete set of triggers against the statutory rule. In the reviewed template, this cross-clause pass removed an initial false alarm about security enforcement.
- **A second pass must be able to remove findings, not only add them.** The analysis pipeline should explicitly support `candidate finding → cross-clause/statutory review → confirmed / narrowed / cleared`. A trustworthy product should reduce false alarms instead of accumulating red flags.
- **Non-use and inability to use are different mechanisms.** A clause requiring rent even when the tenant does not use the apartment should distinguish voluntary non-use from situations where use is impossible because of the apartment or access to it. This creates a dedicated comparison trigger for section `15` and suggests that §15 should be added to the maintained statutory map before implementation of this question.
- **Repair wording based only on “ordinary wear” may be narrower than §25ח.** The engine should compare the contract's trigger for landlord-paid repairs against the statutory structure: tenant-caused unreasonable-use defects versus other non-trivial defects. A contract can use the correct 30-day / 3-day limits while still narrowing the landlord's repair responsibility through the trigger wording.
- **`AS-IS` plus a condition protocol changes the practical action.** When the contract already contains an inspection/defect appendix, the best remediation may be procedural rather than textual: fill the protocol completely, photograph existing defects, and avoid leaving known problems undocumented. The remediation layer therefore needs a class for `ACTION_WITHOUT_REWRITE` / practical pre-signing action, not only replacement clause text.
- **Repeated set-off prohibition is ready for deterministic promotion.** A blanket no-setoff clause has now appeared in more than one independent template family. It should move from catch-all discovery toward a permanent statutory-comparison question against §25 and the applicable §25יד protection.
- **Tenant-favorable terms must survive into the final report and action screen.** A shorter security-return period, a more favorable tenant option notice period, properly allocated running costs, or another better-than-baseline safeguard should be explicitly marked as `NO_CHANGE_NEEDED` / “оставить как есть”. The remediation engine must not imply that every reviewed topic needs negotiation.
- **Remediation outcomes need at least three directions:** `CHANGE_OR_CLARIFY`, `ACTION_WITHOUT_REWRITE`, and `NO_CHANGE_NEEDED`. These sit alongside provenance classes such as statute-grounded discussion text versus ordinary negotiation proposal.
- **Party-role analysis may be collective for obligations but individual for remedies.** Where co-tenants are jointly liable but a guarantee is first applied to the tenant who caused the breach, de-identification and structured extraction must preserve enough role granularity to represent that remedy path.
- **Penalty formulas remain deterministic consequence work.** Fixed daily or rent-relative holdover penalties should be converted to concrete money and monthly-rent multiples when verified rent is available, without turning that calculation into a claim about enforceability.

#### Plain-language rule for Russian UX

User-facing Russian must be written for a person who may be reading a Hebrew contract and Israeli rental rules for the first time.

Do not use abstract phrases such as:

```text
“отдельная юридическая категория”
“требует юридической оценки”
“юридически корректная формулировка”
```

More broadly, **avoid Russian user-facing words built from `юрист-` / `юрид-`**. These terms are unnecessary, make the interface sound like professional counsel, and reduce readability. Internal engineering identifiers may remain in English where needed, but rendered Russian copy should use plain alternatives.

Preferred user-facing language:

```text
Основано на законе
Можно предложить хозяину
Нужно проверить отдельно
Точного ответа в законе здесь нет
Если возникнет спор, это может решаться по обстоятельствам, вплоть до суда
```

The previously proposed Russian label `Требует юридической оценки` is deprecated and must not be used in production copy. Prefer `Нужно проверить отдельно` or a more specific plain-language explanation.

The same rule applies to explanations of open standards such as `reasonable grounds` or `reasonable time`. Do not explain them through abstract terminology. Explain the practical point directly: there is no fixed list or number; if the parties disagree, the answer depends on the circumstances and may ultimately be decided in court.

This update records generalized Question Engine and UX conclusions only. It stores no source contract text, PII, handwriting, raw OCR, or user-specific contract material.
