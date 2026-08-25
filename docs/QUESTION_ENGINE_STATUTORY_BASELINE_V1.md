# Question Engine — Statutory Baseline v1

Status: maintained legal-reference map for the `question-engine-development` track.

Purpose: give the Question Engine a versioned statutory baseline for comparing residential rental contract terms against current Israeli rental law without pretending that the LLM itself is the source of legal truth.

This file is **not** a substitute for the official statute, legal advice, or a court ruling. It is a maintained engineering reference. Contract facts, statutory text, and legal interpretation must remain separate evidence layers.

## 1. Authoritative source and version

Primary authority:

- Law: `חוק השכירות והשאילה, התשל״א-1971` — Rental and Loan Law, 1971.
- Official source: Knesset National Legislation Database.
- Official law page: `https://main.knesset.gov.il/Activity/Legislation/Laws/pages/lawprimary.aspx?lawitemid=2000596&st=lawlaws&t=lawlaws`
- Official database reports the law as in force and lists the latest amendment as published on `2026-03-31`.

The reform commonly called `חוק שכירות הוגנת` / “Fair Rental Law” is not treated here as a separate evergreen statute. The relevant 2017 reform was `חוק השכירות והשאילה (תיקון), התשע״ז-2017`, Amendment No. 1 to the Rental and Loan Law.

Official amendment source:

- `https://main.knesset.gov.il/Activity/Legislation/Laws/pages/lawbill.aspx?lawitemid=2006776&t=lawsuggestionssearch`
- publication: `2017-07-19`, Sefer HaHukim 2649, p. 1028;
- effective date recorded by the Knesset: `2017-09-17`.

Baseline review date: `2026-08-25`.

### Freshness rule

Before using this baseline for production legal comparison, verify the current consolidated law and effective dates against the official Knesset source.

Do not assume a section is unchanged merely because its number still exists.

Concrete current example: section `25י` (security) is marked as amended in 2026 and includes wording whose effective date is `2026-09-30`. Therefore a legal rule engine must support effective-date versioning, not only section-number lookup.

## 2. Required analysis order

The statutory layer should not start by declaring that a contract term is illegal.

Preferred order:

```text
contract fact
→ identify candidate statutory topic
→ verify statutory regime applies
→ verify effective-date version of the section
→ determine whether the statutory rule is mandatory / non-derogable, derogable only in tenant's favor, or merely a default rule
→ compare contract term with statute
→ classify conflict / no conflict / ambiguity / unresolved applicability
→ generate user-facing explanation with section citation
```

Suggested high-level statuses:

```text
STATUTE_NOT_APPLICABLE
STATUTE_APPLIES_NO_CONFLICT
CONTRACT_MORE_TENANT_FAVORABLE
POTENTIAL_STATUTORY_CONFLICT
STATUTORY_INTERPRETATION_REQUIRED
EFFECTIVE_DATE_DEPENDENCY
```

Do not collapse `POTENTIAL_STATUTORY_CONFLICT` into “illegal”. Enforcement, interpretation, factual applicability, other statutes, and case law can matter.

## 3. Applicability gate — section 25טו

Before relying on the special residential-rental provisions, test the exclusions in `25טו`.

Known exclusion classes include, among others:

- hotel / vacation accommodation;
- certain institutional residences;
- protected tenancy governed by the Tenant Protection Law;
- a residential lease of no more than three months with no extension option;
- a residential lease longer than ten years where the landlord has no earlier cancellation option;
- rent above the statutory threshold, which is indexed and therefore must not be hard-coded permanently;
- additional categories if prescribed by the Minister of Justice;
- special treatment for leases between close relatives;
- sublease-specific allocation rules.

Engineering rule:

> Never cite the residential non-derogation framework before the applicability gate is resolved.

If the threshold amount or another applicability fact is not available from the sanitized contract, return an explicit unresolved dependency rather than assuming coverage.

## 4. Section map for Question Engine v1

The following map is intentionally concise. It captures the engineering significance of the current statute without vendoring the entire statutory text into the repository.

### Section 4 — good faith

Rental obligations and exercise of contractual rights are subject to ordinary good-faith performance.

Use: contextual legal baseline only. Do not turn this general clause into an automatic risk flag.

### Section 6 — conformity / non-conformity

The landlord must deliver the rented property in conformity with what the parties agreed. The section also regulates when a tenant may rely on non-conformity and the effect of knowledge / notice / opportunity to inspect or repair.

Use: `AS-IS`, hidden-defect, known-defect, and pre-handover-condition analysis.

### Section 17 — landlord inspection and repair access

The tenant must allow the landlord to inspect and perform repairs at reasonable times, with reasonable advance notice and with disruption minimized as far as possible.

Use: landlord-entry clauses. A contract that appears to permit unrestricted entry should be compared against this baseline and any applicable non-derogation rule before producing a user-facing conclusion.

### Section 22 — assignment / subletting

The general law regulates assignment and subletting and addresses unreasonable refusal by the landlord.

Use: replacement-tenant, assignment, and sublease analysis.

Important: do not infer non-derogability merely from the existence of this section. The non-derogation list in `25יד` must be checked separately.

### Section 25 — set-off (`קיזוז`)

Mutual debts arising from the lease may be set off.

Question Engine consequence:

- if a contract contains a blanket prohibition on set-off, this is a statutory-comparison trigger;
- do not merely paraphrase “set-off prohibited” as if the contract were the whole legal picture;
- applicability and non-derogation must be checked before producing the final statement.

### Section 25ב — written residential lease

A residential lease should be in writing and signed, but failure to comply with the writing requirement does not by itself invalidate the lease; each party is to receive a signed copy.

Use: document-completeness and missing-copy scenarios.

### Section 25ג + Second Schedule — required residential contract content

The residential lease is to include the items listed in the Second Schedule, including, among other things:

- apartment address;
- party identification details;
- apartment / furniture / accessories description;
- lease term;
- extension option and its terms;
- termination right and its terms;
- rent amount, due date, and payment method;
- additional tenant-borne payments;
- known material defects and material known disturbances affecting use.

Question Engine consequence:

- blank fields and omitted required topics are legal-structure findings, not merely formatting defects;
- do not silently invent missing values;
- keep `CLAUSE_PRESENT_VALUE_BLANK` distinct from `NOT_FOUND`.

### Section 25ו — fit for habitation

The landlord must deliver a dwelling fit for habitation. The First Schedule identifies conditions that make a dwelling unfit, including certain missing basic systems and unreasonable safety/health risk.

Non-derogation significance: section `25יד(1)` says this rule cannot be contracted out of.

Question Engine consequence:

- a waiver / `AS-IS` clause cannot be treated as automatically erasing habitability rights;
- severe safety/health defects require statutory comparison rather than contract-only analysis.

### Section 25ח — repairs and defects

Current core structure:

- the tenant is responsible for a defect caused by unreasonable use and generally repairs that defect at the tenant's expense;
- the landlord repairs other non-trivial defects at the landlord's expense within a reasonable time and no later than 30 days after demand;
- an urgent defect that prevents reasonable habitation must be repaired within a reasonable time and no later than 3 days after demand;
- if the landlord does not repair within the statutory period, the general self-help / reduction remedies referenced by the statute may apply.

Question Engine consequence:

- repair analysis must distinguish damage caused by unreasonable tenant use from ordinary defects / wear;
- compare contract repair allocation against the statute before concluding that the tenant must pay;
- cross-check `AS-IS`, appliance/furniture clauses, set-off clauses, and repair-remedy clauses together.

### Section 25ט — current payments borne by tenant

The statute lists ordinary tenant-borne payments, including:

- rent;
- taxes imposed on the apartment holder, including arnona;
- current consumption services such as water, electricity, gas, and heating;
- current common-property maintenance payments.

The statute also identifies payments that should not be shifted directly to the tenant under this section, including examples such as:

- acquisition / improvement of fixed systems serving the apartment, except tenant-requested special adaptations or improvements;
- building insurance premiums;
- landlord obligations to third parties outside the listed current payments, including broker fees where the broker acted for the landlord.

Question Engine consequence:

- classify each payment by legal type instead of using one generic “utilities/costs” bucket;
- compare unusual landlord-cost shifting against this section.

### Section 25י — security (`ערובה`)

Current engineering-relevant structure:

- the section regulates security securing tenant obligations;
- the statutory amount cap applies to security that involves a financial outlay by the tenant, including examples such as a bank guarantee or cash;
- the combined cap is the lower of one-third of total rent for the lease period or three months' rent;
- realization is limited to enumerated situations and corresponding amounts;
- the landlord must give reasonable advance notice before realization and allow a reasonable opportunity to cure;
- return of the security / balance is subject to the statutory return timing.

Critical Question Engine rule:

> Do not apply the three-month cap mechanically to every instrument called “security”. Distinguish a bank guarantee / cash-type security from a security cheque, promissory note, guarantor obligation, and other instruments, then determine whether the statutory cap applies to that instrument.

Also flag effective-date versioning: the 2026 amendment to `25י` contains wording effective `2026-09-30` concerning additional guarantee providers.

### Section 25יב — extension / option

Key current structure:

- the landlord should notify the tenant within a reasonable time before expiry whether the landlord wants to extend and on what terms;
- if the landlord has an extension option, the landlord must give notice no later than 90 days before expiry and may exercise the option only if the extension terms were set in advance in the contract;
- if the tenant has an extension option, the tenant must notify the landlord no later than 60 days before expiry.

Question Engine consequence:

- `option_exists = true` is not enough;
- ask whose option it is, notice period, whether the economic terms are predetermined where required, and whether the contract's mechanism is actually predictable / exercisable.

### Section 25יג — no-cause termination clause

Current core structure:

- a residential lease clause allowing the landlord to terminate without breach is invalid unless the tenant has a corresponding termination right;
- the landlord must give at least 90 days' notice;
- the tenant must give at least 60 days' notice.

Question Engine consequence:

- early-exit analysis must distinguish termination for breach from a no-cause break clause;
- if the contract grants only the landlord a no-cause break right, create a statutory-comparison finding;
- compare all early-exit clauses together before writing the practical explanation.

### Section 25יד — non-derogation / tenant-favor rule

This is a central meta-rule for the Question Engine.

Current structure includes:

- section `25ו` cannot be contracted out of;
- a defined list of provisions, including sections `23` through `25ה`, parts of `25ח`, and `25ט` through `25יג`, may not be varied except in the tenant's favor.

Question Engine consequence:

- do not treat a conflicting contract clause as necessarily controlling merely because the tenant signed it;
- when a contract term is worse for the tenant than a protected statutory rule, surface the statutory conflict with the exact section number;
- do not over-extend `25יד` to sections that are not listed.

### Section 25טו — exclusions / scope

This section is the mandatory applicability gate described above.

Question Engine consequence:

- no “Fair Rental Law says…” output until `25טו` scope has been checked;
- indexed statutory monetary thresholds must be refreshed from current official sources rather than hard-coded forever.

## 5. User-facing citation policy

When the statutory comparison is sufficiently supported, the report should cite the relevant section explicitly.

Preferred pattern:

```text
Договор говорит: ...

Но для обычной жилой аренды §25ח Закона об аренде и ссуде устанавливает ...
§25יד не позволяет ухудшить эту норму договором в ущерб арендатору.

Практически это означает: ...
```

Requirements:

- identify the statute by its proper name: `חוק השכירות והשאילה, התשל״א-1971`;
- optionally explain that the residential protections were substantially added by the 2017 reform commonly called `שכירות הוגנת`;
- cite exact section IDs rather than vaguely saying “the 2017 law”;
- distinguish contract fact from statutory rule and from product interpretation;
- avoid categorical “illegal / void / unenforceable” wording unless the statutory rule clearly supports that conclusion and applicability is resolved;
- prefer “potential conflict with §X” when interpretation or facts remain unresolved.

## 6. Example: contract prohibition on set-off

Contract finding:

```text
setoff_prohibited_by_contract = true
```

Statutory triggers:

- section `25`: mutual debts arising from the lease may be set off;
- section `25יד`: section `25` is within the protected list for residential leases, subject to the applicability framework.

User-facing direction:

> The contract says you may not set off amounts against rent. However, section 25 of the Rental and Loan Law provides for set-off of mutual lease-related debts, and section 25יד limits contracting out of that rule to the tenant's detriment in applicable residential leases. Therefore the contract wording should not be presented as automatically eliminating every set-off right.

This example is an engineering pattern, not an individualized legal opinion.

## 7. Example: security amount relative to rent

The engine should perform two separate analyses:

1. **Economic significance:** calculate `security_amount / monthly_rent` when both values are verified.
2. **Statutory cap applicability:** determine the security instrument type and whether `25י`'s financially-burdensome-security cap applies.

Do not confuse these questions.

A security cheque equal to 3.6 months of rent may be economically notable even if the statutory three-month cap does not apply to that instrument in the same way as to a bank guarantee or cash deposit.

## 8. Source-of-truth and maintenance policy

Production or release calibration must use the official current law, not this file alone.

Maintenance checklist:

1. Open the official Knesset law page.
2. Record the latest amendment date.
3. Check whether relevant sections changed.
4. Check commencement / future-effective dates.
5. Check indexed monetary thresholds and official notices where relevant.
6. Update this baseline's review date and any changed summaries.
7. Add regression fixtures for any changed statutory rule before shipping updated legal comparisons.

If the statutory baseline is stale or version cannot be verified, the system should degrade to contract-only analysis rather than assert an outdated legal rule.

## 9. What is intentionally not stored here

This repository does not vendor a full static copy of the statute in v1.

Reasons:

- the law is actively amended and a static copy can silently become stale;
- parts of the current law have future-effective wording;
- the Question Engine needs section-level applicability / effective-date metadata, not merely a text dump;
- the official Knesset database remains the authority.

If a future implementation needs local immutable legal text for deterministic testing, add a separately versioned, source-attributed statutory snapshot with explicit `effective_from`, `effective_until` / superseded metadata and a refresh process. Do not replace this maintained baseline with an unversioned copied law file.
