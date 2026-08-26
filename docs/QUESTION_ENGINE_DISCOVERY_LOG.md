# Question Engine — Discovery Log and Current Working Design

Status: consolidated working design for the `question-engine-development` track.

This document records current Question Engine product decisions and the generalized discoveries that led to them. It is intentionally more compact than the earlier chronological notebook. Detailed historical wording remains available in Git history before PR #239.

This file is **not** the canonical operational state. `docs/OCR_PROJECT_STATE.md` and `docs/OCR_PROJECT_STATE.json` remain authoritative for `active_track`, blockers, and `next_step_id`. Binding privacy/security/architecture rules remain in `AGENTS.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, and the privacy/OCR contracts.

## 1. Product objective

The Question Engine should help a Russian-speaking tenant understand what a Hebrew residential rental contract means in practice.

The product is not a clause-by-clause paraphraser and must not begin with an unconstrained `LLM: find risks` prompt. It should behave as a translator of consequences and a preparation tool for discussion before signing.

The product may offer concrete discussion points and optional Hebrew wording, but it does **not** produce a certified final contract, determine the final outcome of a dispute, tell the user whether to sign, or predict who would win in court.

## 2. Current target pipeline

```text
privacy-validated sanitized contract material
→ deterministic core question inventory
→ LLM structured semantic extraction
→ deterministic conditional follow-ups
→ cross-clause interaction checks
→ bounded novel-issue catch-all
→ deterministic/Python schema + evidence + consistency validation
→ statutory applicability/effective-date comparison where relevant
→ confirmed / narrowed / cleared findings
→ Screen 1 orientation
→ Screen 2 Russian essay analysis
→ Screen 3 Russian discussion/action plan
→ optional Hebrew discussion text on demand
```

The LLM reads natural language and extracts relationships. Code controls what must be investigated, validates evidence and structure, performs deterministic comparisons/calculations, gates statutory claims, and decides which results may reach the user.

The deterministic layer does not need to perform free-form semantic interpretation of Hebrew legislation. It uses maintained, versioned statutory rules and metadata for bounded checks after the relevant contract facts have been extracted.

## 3. Source of truth and evidence layers

The LLM is not the source of truth.

Keep these layers separate:

```text
CONTRACT_FACT
STATUTORY_RULE
PRODUCT_EXPLANATION
```

Contract evidence establishes what the document says. The statutory layer supplies verified rule context. Product explanation translates practical consequence.

Do not create an unconstrained model-owned `LEGAL_CONCLUSION` layer.

Exact Hebrew evidence shown to the user must come from sanitized source material or a deterministic sanitized evidence reference, not from an LLM-generated quote.

## 4. Core answer states

At minimum the engine must distinguish:

```text
FOUND
NOT_FOUND
AMBIGUOUS
HANDWRITING_DEPENDENCY
CLAUSE_PRESENT_VALUE_BLANK
```

`NOT_FOUND` is valid and must not be treated as model failure.

`CLAUSE_PRESENT_VALUE_BLANK` means the mechanism exists in printed text but a required value is blank. It is not the same as absence.

Handwriting must never be semantically reconstructed, guessed, or inferred from surrounding text. If meaning depends on handwriting, return an explicit unresolved dependency.

## 5. Party-role granularity

De-identification must preserve the role granularity actually used by the contract.

If several named people are collectively defined and later operative text uses only one collective role, keep the collective role. Do not invent numbered tenants merely because several names appear in the header.

Introduce individual placeholders only where operative text materially distinguishes individuals in rights, obligations, guarantees, payments, or remedies.

A contract may therefore be collective for most obligations while still distinguishing one participant for a specific remedy or payment path.

## 6. Core recurring domains

The first deterministic inventory should cover recurring domains such as:

- lease term and dates;
- rent amount and payment mechanics;
- indexation / currency linkage / external reference rates;
- renewal / option and economic predictability;
- early exit / replacement tenant / assignment / subletting;
- late payment, breach definitions, cure periods, and sanctions;
- security instruments, amounts, enforcement, and return;
- utilities, arnona, `ועד בית`, and other running costs;
- repairs, defects, ordinary wear, furniture/appliances;
- `AS-IS`, known defects, condition protocols;
- use restrictions, guests, additional occupants;
- alterations and restoration duties;
- landlord access;
- liability and third-party claims;
- handover / return condition / holdover;
- sale or transfer of landlord rights;
- set-off restrictions;
- missing appendices or referenced documents;
- blank fields, broken references, and internal inconsistencies;
- bespoke/special conditions.

Topic presence alone is not useful. The engine must ask how the topic is regulated, what safeguards or exceptions exist, who carries practical risk, and how related clauses interact.

## 7. Cross-clause analysis is mandatory

A candidate finding is not final until relevant definitions and related clauses have been checked.

Required patterns include:

### Early exit

Compose continuing rent liability, replacement-tenant path, assignment/subletting limits, and any separate termination mechanism into one practical exit model.

### Security

Resolve the actual instrument type, amount, enforcement grounds, notice/cure rule, return trigger, and return deadline. If the contract says `any fundamental breach`, first determine exactly which breaches the contract defines as fundamental.

### Repairs

Read repair allocation together with `AS-IS`, furniture/appliance provisions, self-help/reimbursement rules, and set-off provisions.

### Internal references

Verify that referenced clauses exist and are relevant. Broken references are first-class findings.

### Standard text versus special conditions

Check whether bespoke additions supplement, narrow, override, or contradict generic template language.

The second pass must be able to remove or narrow an initial concern:

```text
candidate finding
→ cross-clause/statutory review
→ CONFIRMED / NARROWED / CLEARED
```

A trustworthy engine reduces false alarms rather than accumulating red flags.

## 8. Novel-issue catch-all

After the deterministic inventory and cross-clause passes, run one bounded catch-all for material mechanisms not already covered.

Repeated discoveries across independent contracts should be promoted into the permanent inventory or a conditional branch.

Current candidates already mature enough for deterministic promotion include:

- blanket set-off prohibition;
- broken internal references;
- security-enforcement scope;
- replacement-tenant veto mechanics;
- external economic dependencies;
- open-ended reasonableness standards;
- subjective counterparty-satisfaction standards;
- holdover/penalty formula calculations.

## 9. Practical significance and deterministic calculations

Do not dominate the report with banal facts such as “rent must be paid”. Translate verified source values into useful consequences.

Examples:

```text
security_amount / monthly_rent
```

```text
holdover_penalty
→ ₪/day
→ ₪/week
→ ₪/30 days
→ multiple_of_monthly_rent
```

External dependencies such as CPI, USD/ILS exchange rate, or a bank reference rate should be represented explicitly, for example:

```text
EXTERNAL_VALUE_DEPENDENCY
```

Do not invent user-facing severity thresholds until calibrated from more evidence.

## 10. Security instruments remain distinct

Do not collapse these into one generic “deposit”:

- `שיק ביטחון` / security cheque;
- `ערבות בנקאית` / bank guarantee;
- `שטר חוב` / promissory note;
- cash deposit;
- guarantor obligations;
- post-dated rent cheques;
- utility/open cheques where relevant.

This distinction matters both economically and for statutory comparison. In particular, do not apply a financial-outlay cap mechanically to every instrument called security.

## 11. Internal inconsistencies are findings, not cleanup tasks

Actively compare:

- stated duration versus start/end dates;
- payment count versus stated term;
- option duration versus notice rule;
- repeated amounts/dates across sections;
- security instrument name at creation versus return;
- references to missing or wrong subclauses;
- standard text versus later special conditions.

Preserve the inconsistency. Do not silently correct source text.

External context may explain an inconsistency, but external context must remain separate from what the contract itself proves.

## 12. Mandatory explanation of `שכירות בלתי מוגנת`

Never leave this as the bare Russian phrase “незащищённая аренда”.

Immediately explain in plain Russian that this means the agreement is outside the special historical `דייר מוגן` regime. It does not mean that the tenant has no ordinary rights under the contract or applicable law.

## 13. Balanced analysis

Do not encode a presumption of bad faith by landlords or agents.

The engine may explain that a contract is strongly landlord-favoring, restrictive, or gives one side substantial leverage, but it must describe the mechanism and evidence rather than accuse anyone of deception.

Tenant-friendly safeguards must also survive into the final result. A topic may legitimately end as:

```text
NO_CHANGE_NEEDED
```

Examples include a shorter security-return period, a better tenant option notice period, clear running-cost allocation, or a useful repair safeguard.

## 14. Statutory layer

The maintained source is the current `חוק השכירות והשאילה, התשל״א-1971` (Rental and Loan Law, 1971). The reform commonly called `שכירות הוגנת` is treated correctly as Amendment No. 1 from 2017, effective `2017-09-17`, not as a separate timeless statute.

Required analysis order:

```text
contract fact
→ candidate statutory topic
→ applicability gate
→ effective-date-correct rule version
→ non-derogation / tenant-favor rule where relevant
→ compare contract with rule
→ certainty class
→ confirmed statutory outcome
→ user-facing explanation
```

Section `25טו` is the applicability gate for the special residential regime. Section `25יד` is a central non-derogation meta-rule, but it must not be extended to sections it does not name.

Current law, not memory of 2017, is authoritative. Later amendments must be overlaid by effective date.

If freshness or effective date cannot be verified, degrade to contract-only analysis rather than assert a stale rule.

## 15. Statutory outcome types

Useful internal outcome types include:

```text
STATUTE_NOT_APPLICABLE
STATUTE_APPLIES_NO_CONFLICT
CONTRACT_MORE_TENANT_FAVORABLE
STATUTE_SUPPLEMENTS_CONTRACT
CONTRACT_NARROWER_THAN_STATUTE
POTENTIAL_STATUTORY_CONFLICT
EFFECTIVE_DATE_DEPENDENCY
```

Do not automatically translate `POTENTIAL_STATUTORY_CONFLICT` into a categorical statement that a clause is invalid or can be ignored.

## 16. Statutory certainty classes

Keep certainty separate from outcome:

```text
DETERMINATE_STATUTORY_COMPARISON
OPEN_STATUTORY_STANDARD
LEGAL_INTERPRETATION_REQUIRED
```

These identifiers are internal engineering labels, not Russian UI copy.

- `DETERMINATE_STATUTORY_COMPARISON`: applicability/effective-date checks pass and the rule is concrete enough for bounded comparison.
- `OPEN_STATUTORY_STANDARD`: the rule itself uses an open concept such as reasonable time or reasonable grounds.
- `LEGAL_INTERPRETATION_REQUIRED`: the engine cannot safely reduce the issue to a deterministic rule without broader sources, disputed facts, or case-specific judgment.

## 17. Open standards versus subjective counterparty standards

Do not treat these as the same thing.

`reasonable time`, `reasonable grounds`, `reasonable notice`, and similar wording do not supply one universal number or list. User-facing copy should explain the practical point directly: the boundary depends on the circumstances; if the parties disagree, the matter may ultimately be decided in court.

Language equivalent to `to the landlord's satisfaction` is different because the counterparty's satisfaction is built directly into the contractual mechanism. Represent it separately, for example:

```text
SUBJECTIVE_COUNTERPARTY_SATISFACTION_STANDARD
```

Where the statute supplies a hard outside limit, surface that concrete number instead of leaving the user only with vague wording.

## 18. Template and source trust rules

Template recognition is orientation metadata, never semantic proof.

```text
TEMPLATE_FAMILY_MATCH != CLAUSE_EQUIVALENCE
SOURCE_RECENCY != STATUTORY_ALIGNMENT
```

Every concrete contract must be read end-to-end. Small edits, blanks, added clauses, or special conditions can materially change practical outcome.

Public templates are useful for discovering recurring topics and market drafting patterns. They are **not** sources of statutory truth.

Balanced public templates are comparative reference material, not presumed realistic rewrite targets for the user's landlord or agent.

Track source/version freshness. A live public URL can continue serving an old document after a newer version exists.

## 19. Legacy templates

An old template is useful evidence of drafting patterns that may continue circulating, but age itself is not a verdict.

Represent literal contract effect separately from current statutory effect:

```text
CLAUSE_LITERAL_EFFECT
STATUTORY_EFFECT
```

Legacy clauses especially reinforce checks for:

- overly broad repair allocation;
- broad `AS-IS`/waivers;
- broad tenant-payment catch-alls;
- `ANY BREACH → security enforcement`;
- external currency/rate dependencies;
- missing return deadlines;
- excessive or unclear sanction formulas;
- broken references.

Do not invent a statutory cap where the maintained statutory baseline does not identify one.

## 20. Remediation is a separate layer

The product must not stop at `finding → explanation`.

Preferred path:

```text
finding
→ practical consequence
→ statutory comparison when relevant
→ certainty class
→ actionable discussion point
→ optional proposed wording for discussion
```

Internal provenance classes:

```text
STATUTE_GROUNDED_DISCUSSION_TEXT
NEGOTIATION_DISCUSSION_TEXT
LEGAL_REVIEW_RECOMMENDED
```

These are engineering identifiers only.

- `STATUTE_GROUNDED_DISCUSSION_TEXT`: wording grounded in a concrete, applicability-checked, effective-date-correct statutory rule. It is still discussion text, not a certified final clause.
- `NEGOTIATION_DISCUSSION_TEXT`: a practical safeguard that the statute does not require in those exact words.
- `LEGAL_REVIEW_RECOMMENDED`: the issue is not safe to reduce to a deterministic replacement clause; prefer a question or negotiation direction instead.

A statute-grounded discussion text is blocked unless the statutory gate passes.

Remediation outcomes need at least:

```text
CHANGE_OR_CLARIFY
ACTION_WITHOUT_REWRITE
NO_CHANGE_NEEDED
```

`ACTION_WITHOUT_REWRITE` covers practical safeguards such as fully documenting an existing defect protocol rather than unnecessarily rewriting a clause.

## 21. User-facing UX hierarchy

The current screen order supersedes the earlier generic “essay → attention list → details” ordering:

### Screen 1 — orientation / overall result

A compact overall picture and completeness state.

### Screen 2 — Russian essay analysis

Explain how the contract works, the important problems, statutory context where supported, important uncertainties, and meaningful tenant-friendly safeguards.

Do not place long Hebrew proposal text on this screen.

### Screen 3 — Russian discussion/action plan

For each important item explain:

- what should be discussed or clarified;
- why it matters;
- whether it is grounded in a concrete rule, an ordinary negotiation safeguard, or something that cannot be reduced safely to one answer;
- whether the best action is wording change, practical action without rewrite, or no change.

Detailed per-clause/source material should be available as drill-down from the analysis/action flow rather than occupying a competing top-level screen.

## 22. Plain-language Russian rule

User-facing Russian is for a person who may be seeing Hebrew contract terminology for the first time.

Do not use abstract professional jargon when a normal sentence works.

In particular, production Russian copy should avoid words built from `юрист-` / `юрид-`.

Do **not** use labels such as:

```text
Требует юридической оценки
Юридически корректная формулировка
Отдельная юридическая категория
```

Use plain alternatives such as:

```text
Основано на законе
Можно предложить хозяину
Нужно проверить отдельно
Точного ответа в законе здесь нет
Если возникнет спор, ответ зависит от обстоятельств и может дойти до суда
```

Internal English identifiers such as `LEGAL_INTERPRETATION_REQUIRED` may remain in engineering data and must not leak into Russian UI copy.

## 23. Hebrew discussion text

Hebrew is optional communication payload, not the primary explanation.

Preferred UI:

```text
Russian discussion card
→ [Показать текст на иврите]
→ side sheet / drawer / bottom sheet with RTL Hebrew text
→ [Копировать] [Поделиться]
```

The Hebrew text should not remain permanently visible on the main page.

Provide a copy action directly beside the Hebrew phrase. On Android, use the generic system share sheet rather than hard-coding WhatsApp-only behavior; WhatsApp can then appear naturally if installed.

## 24. Boundary against advice-like outputs

The main protection is architecture/schema gating, not a footer disclaimer.

Allowed shape:

```text
what the contract says
→ what a verified rule may add or limit
→ practical consequence
→ what can be clarified or discussed
```

Do not generate outputs that say or imply:

- this is the user's final position in a dispute;
- the user may safely ignore a contractual obligation;
- the user will win or lose in court;
- the user should sue, refuse to pay, sign, or not sign;
- a model-generated clause is the one correct final wording.

Do not personalize transaction/dispute strategy from unrelated user profile data.

A concise product notice may say in plain language that the app explains the contract and relevant rules, does not determine the outcome of a dispute, and does not tell the user what they must do. The notice is secondary to deterministic output controls.

## 25. High-value recurring statutory triggers discovered so far

The permanent inventory should include or prepare conditional checks for at least:

- applicability / §25טו;
- `AS-IS`, hidden/known defects / §§6, 8 and related rules;
- inability to use the apartment versus voluntary non-use / §15;
- landlord access / §17;
- assignment/subletting/replacement tenant / §22, with caution about derogability;
- set-off prohibition / §25 + applicable §25יד protection;
- fit-for-habitation / §25ו;
- repairs / §25ח;
- tenant-payable charges / §25ט;
- security type/cap/enforcement/return / §25י;
- landlord transfer notice / §25יא;
- option/renewal / §25יב;
- no-cause termination / §25יג;
- non-derogation / §25יד.

## 26. Findings from reviewed template families that must survive implementation

Generalized lessons from the municipal, legacy, current commercial, and public generator/template reviews:

- current professional-looking templates can still contain provisions that deserve statutory comparison;
- second-pass analysis can clear an initially suspicious security clause after definitions are resolved;
- landlord repair wording tied only to “ordinary wear” may be narrower than the statutory trigger;
- broad tenant-payment catch-alls require scoping against permitted categories;
- blanket set-off prohibition is a recurring deterministic trigger;
- replacement-tenant rights are only as useful as their approval/veto mechanism;
- an option is incomplete without notice rules and economic terms;
- an `AS-IS` clause may make a condition protocol practically important, but should not be presented as erasing every protection;
- security analysis requires type, amount, enforcement grounds, notice/cure, return trigger, and return deadline separately;
- open reasonableness wording and subjective `landlord satisfaction` wording are different mechanisms;
- a fixed daily or percentage penalty should be translated into concrete money before it is explained;
- the engine must surface good provisions as well as problems;
- one PDF may contain separate documents such as the lease, guarantee, appendix, or marketing consent and should be segmented accordingly;
- a third-party template/blog may be useful for topic discovery while being unreliable as a source of statutory rules.

## 27. Current implementation direction

Discussion/research has now produced enough stable material to move from discovery into the canonical next bounded implementation step:

```text
question-engine-question-inventory-v1
```

The first implementation should not attempt the whole product. It should define a bounded v1 inventory, conditional questions, topic-specific structured fields, and evidence targets against the existing sanitized golden contract, while keeping runtime LLM/provider integration outside that PR unless explicitly authorized by a later state change.

The inventory should reserve fields/branches for statutory comparison and remediation discovered above without prematurely implementing the entire statutory engine or UI.

## 28. Remaining design questions

Still not frozen:

- exact v1 question IDs and field names;
- exact JSON schema boundaries between topic facts and findings;
- exact evidence-reference representation;
- how many model passes are optimal;
- exact trigger representation for cross-clause checks;
- severity/ranking calibration;
- exact wording-generation contract for Hebrew discussion text;
- how to represent later statutory overlays in runtime code;
- release cadence for refreshing statutory sources;
- exact mobile visual design for Screens 1–3.

These open questions should now be resolved incrementally through bounded implementation PRs rather than by extending this discovery discussion indefinitely.
