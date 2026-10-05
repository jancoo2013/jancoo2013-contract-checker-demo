# Expert Memory — Residential Lease Mechanism Map v0.1

Status: experimental teaching/retrieval map for the Expert Memory track.

Purpose: provide the second learning layer after the Foundation Core. The Foundation Core teaches what a lease is and how to read contractual mechanisms. This map teaches the major subsystems that may exist inside a residential lease, what function each subsystem performs, which questions define it, and which neighboring mechanisms must not be confused with it.

This document is not a legal rule source, statutory baseline, checklist of mandatory clauses, risk catalogue, Router schema, Gold annotation set, or production runtime contract.

## 1. Position in the learning hierarchy

The intended teaching sequence is:

```text
Foundation Core
-> Mechanism Map
-> Router / structural discovery
-> targeted mechanism modules
-> cross-clause reconciliation
-> final completeness audit
```

The Mechanism Map is deliberately more abstract than a glossary.

It answers:

> What kinds of systems can a residential lease contain, and what function does each system perform?

It does not yet answer:

> What are all possible subtypes, legal rules, market practices, risk thresholds, or jurisdiction-specific consequences?

Those belong to later targeted modules.

## 2. Mechanisms are not identical to Router labels

A Router family is an indexing label used to retrieve relevant knowledge.

A contract mechanism may require several Router families at once. Conversely, one Router family may participate in several different mechanisms.

Examples:

- `NOTICE` may participate in option exercise, breach cure, security realization, transfer, or termination;
- `RENT_PAYMENT` may participate in ordinary payment, early-exit continuing liability, breach, or option-period economics;
- `PROPERTY_CONDITION`, `REPAIR`, and `DAMAGE` often form one connected property-state mechanism;
- `SECURITY` may need `NOTICE`, `BREACH`, `OPTION`, or payment evidence to become understandable;
- `OTHER` may contain structural material that is essential even though no dedicated Router family exists.

Therefore the mechanism map is a semantic layer above routing, not a replacement for routing.

## 3. M00 — Contract frame: parties, object, document structure

### Function

Establish who is participating, what dwelling or property is being leased, which document components form the agreement, and which defined roles the contract uses.

### Core questions

- Who are the contractual roles?
- Does the contract distinguish several people individually or collectively under one role?
- What dwelling, rooms, fixtures, furniture, parking, storage, or other property is included?
- What definitions are introduced?
- Does the preamble form part of the operative agreement?
- Which appendices, inventories, protocols, guarantees, or special conditions are expressly incorporated?
- Is the supplied package complete enough to support contract-wide conclusions?
- Is there a document-priority rule between main text, appendix, handwritten addition, or later amendment?

### Typical Router support

Usually `OTHER`, plus whatever substantive families are triggered by the incorporated material.

### Boundaries

Do not infer a missing participant, object, appendix, or term merely because such material would be typical.

Do not treat a referenced but unavailable document as though its content were known.

Do not infer individual party numbering when operative text treats multiple people as one contractual role.

## 4. M01 — Term, duration, continuation, and renewal

### Function

Define when the tenancy begins, how long it lasts, when it ends, and whether or how it can continue.

### Core questions

- What is the initial term?
- What are the start and end dates?
- Are stated dates consistent with the stated duration?
- Is there an option, renewal, extension, automatic continuation, or new-agreement mechanism?
- Who controls continuation?
- What notice, timing, form, prerequisites, or consent are required?
- Is future rent fixed, formula-based, externally determined, or unresolved?
- Must security or other obligations continue into the extended period?

### Typical Router support

`TERM`, `OPTION`, `NOTICE`, sometimes `RENT_PAYMENT`, `SECURITY`, and `BREACH`.

### Boundaries

An option is not the same as an ordinary request to negotiate a new contract.

A notice period tied to renewal must not be reused as an early-exit or termination notice period.

Unresolved option economics do not prove that no option exists.

## 5. M02 — Rent payment mechanism

### Function

Define the primary consideration paid for the right to occupy the dwelling.

### Core questions

- What is the rent amount or formula?
- When is rent due?
- By what payment method?
- How many cheques, transfers, deposits, or installments are required?
- Are instruments post-dated?
- Are payment descriptions internally consistent?
- Does another clause change the amount or method during an option period?
- What happens if rent remains payable after early departure?
- Does delayed payment trigger interest, indexation, breach, cure, or termination?

### Typical Router support

`RENT_PAYMENT`, often `TERM`, `OPTION`, `EARLY_EXIT`, `BREACH`, `NOTICE`.

### Boundaries

Rent-payment instruments are not automatically security instruments.

A payment count must not be used to repair an inconsistent contractual term.

A late-payment consequence is not part of the ordinary rent schedule even when it is calculated from rent.

## 6. M03 — Other monetary obligations

### Function

Allocate non-rent financial obligations between the parties.

### Core questions

- Who pays utilities, municipal charges, building charges, taxes, maintenance fees, or other expenses?
- When does each obligation arise?
- Is payment made directly to a third party or reimbursed to the other party?
- Must receipts or proof of payment be retained or shown?
- Is an amount fixed, variable, formula-based, or externally determined?
- Does late payment create interest, reimbursement, set-off, breach, or another consequence?

### Typical Router support

`OTHER_PAYMENT`, sometimes `NOTICE`, `BREACH`, `REPAIR`, `DAMAGE`, or `VACATING`.

### Boundaries

Do not merge rent with other charges merely because both are monetary.

Do not treat a reimbursement mechanism as ordinary rent.

Do not classify a security amount as an ordinary payment merely because it is denominated in money.

## 7. M04 — Property condition, defects, repair, and damage

### Function

Define the factual and contractual state of the dwelling, responsibility for defects and repairs, responsibility for damage, and expected condition during and at the end of the tenancy.

### Core questions

- What condition does the tenant acknowledge at entry?
- Is there an inventory, defect list, inspection protocol, or AS-IS statement?
- Which defects are pre-existing, hidden, known, or excluded?
- Who is responsible for which repairs?
- Are there response periods or notice duties?
- Can one party repair and recover cost from the other?
- Is reimbursement different from set-off against rent?
- What damage is attributed to tenant conduct, third parties, ordinary wear, or another cause?
- What return condition is required?
- Do alterations or improvements affect restoration duties?

### Typical Router support

`PROPERTY_CONDITION`, `REPAIR`, `DAMAGE`, often `VACATING`, `OTHER_PAYMENT`, `NOTICE`, and `OTHER`.

### Boundaries

AS-IS wording does not by itself define the whole repair allocation.

A repair obligation and a damage-compensation obligation are different mechanisms.

Ordinary wear, restoration, repair, and third-party damage must remain separate unless the contract links them.

A right to reimbursement is not automatically a right to deduct money from rent.

## 8. M05 — Use, occupancy, alterations, and access

### Function

Define how the dwelling may be used, who may occupy it, what changes may be made, and under what conditions the landlord or others may enter.

### Core questions

- What uses are permitted or prohibited?
- Who may live in or use the dwelling?
- Are guests, additional occupants, business use, pets, subletting, or other activities regulated?
- Are alterations, installations, drilling, painting, furniture movement, or structural changes restricted?
- Is consent required, and from whom?
- Who may enter the dwelling?
- For what purposes?
- Is prior coordination, notice, consent, emergency access, or a time restriction stated?
- Must alterations be removed or left in place at the end?

### Typical Router support

`ACCESS`, `TRANSFER`, `PROPERTY_CONDITION`, `DAMAGE`, `VACATING`, and often `OTHER`.

### Boundaries

Landlord access is not the same as transfer of possession.

An occupancy restriction is not automatically a transfer/subletting rule.

An alteration restriction is not automatically a repair obligation.

Consent to one act must not be generalized to unrelated acts.

## 9. M06 — Transfer, substitution, and early exit

### Function

Define whether the tenant or landlord may transfer contractual position, possession, or occupancy, and whether a tenant can leave before the ordinary end of the term.

### Core questions

- Is assignment, subletting, transfer, or replacement prohibited, permitted, or conditional?
- Is there a specific replacement-tenant route?
- What requirements apply to a candidate replacement?
- Who approves or refuses?
- Is any approval standard stated?
- Does the original tenant remain liable until a separate release event?
- Does physical departure itself change payment liability?
- Is there a notice requirement?
- Does landlord sale or transfer affect the tenant's rights or duties?
- Are transfer and early-exit mechanisms linked or independent?

### Typical Router support

`TRANSFER`, `EARLY_EXIT`, often `RENT_PAYMENT`, `NOTICE`, `BREACH`, and `OTHER`.

### Boundaries

A general assignment prohibition does not automatically defeat a specific replacement-tenant route.

Leaving the dwelling does not automatically terminate future rent liability.

A sale/transfer notice period must not be imported into early-exit procedure.

Replacement tenant, subtenant, assignee, guest, and permitted occupant are not interchangeable concepts.

## 10. M07 — Security and performance assurance

### Function

Provide additional assurance that contractual obligations will be performed or that an identified remedy can be pursued if specified conditions occur.

### Core questions

- What instrument or undertaking exists?
- Who provides it and for whose benefit?
- What amount, cap, date, payee, guarantor, or other stated attributes exist?
- What obligation does it secure?
- What event authorizes use, realization, completion, demand, or collection?
- Is notice or cure required?
- Is the realizable amount fixed or linked to actual debt/damage?
- What method of realization is described?
- When must the instrument be returned, cancelled, released, or replaced?
- Does renewal require continuation or replacement of security?
- Are several security instruments present, and do they secure the same or different obligations?

### Typical Router support

`SECURITY`, often `NOTICE`, `BREACH`, `OPTION`, `RENT_PAYMENT`, `OTHER_PAYMENT`, `DAMAGE`.

### Boundaries

Different instruments remain distinct unless the contract expressly links them.

A security cheque, promissory note, personal guarantee, institutional guarantee, rent cheque, and utility cheque are not one generic object.

A return rule for one instrument must not migrate to another.

Silence in the contract about a physical field does not prove that the field on the actual instrument is blank.

Detailed instrument subtypes and law-specific limits belong to later modules, not this map.

## 11. M08 — Breach, notice, cure, and termination

### Function

Define what happens when an obligation is not performed and how the contractual relationship may move from non-performance to cure, cancellation, termination, or vacancy.

### Core questions

- Which events are defined as breach?
- Are some breaches classified as material, fundamental, or otherwise special?
- Is notice required?
- What form and delivery rule applies?
- Is there an opportunity to cure?
- What cure period applies to which breach?
- Are there exceptions to cure?
- When does cancellation or termination become effective?
- Does termination create a separate duty to vacate?
- Are monetary consequences separate from termination?
- Does a clause-specific procedure narrow a broad breach definition?

### Typical Router support

`BREACH`, `NOTICE`, often `VACATING`, `RENT_PAYMENT`, `OTHER_PAYMENT`, `SECURITY`, `DAMAGE`.

### Boundaries

Breach classification and remedy procedure are different parts of one mechanism.

A cure period tied to one breach must not be generalized to every breach.

A monetary penalty or interest clause does not automatically terminate the lease.

A broad termination clause must be reconciled with narrower special procedures.

## 12. M09 — End of tenancy, return, and holdover

### Function

Define how possession is returned, what condition is required, what must be completed at handover, and what happens if the tenant remains after the required return point.

### Core questions

- What date or event requires return of possession?
- What physical condition is required?
- Are cleaning, painting, restoration, removal, or repair duties stated?
- Is ordinary wear excluded?
- Is there a pre-return inspection?
- Is there an opportunity to correct defects?
- What keys, property, documents, receipts, or utilities must be settled?
- When are security instruments returned or released?
- What event constitutes holdover?
- What payment or consequence follows holdover, and how is it calculated?

### Typical Router support

`VACATING`, `PROPERTY_CONDITION`, `REPAIR`, `DAMAGE`, `OTHER_PAYMENT`, `SECURITY`, `NOTICE`.

### Boundaries

A defect-correction process is not the same as the holdover trigger.

Return condition and early exit are not the same mechanism.

A security return event may depend on post-vacancy settlement and therefore must not be assumed to occur on the same date as physical handover.

## 13. M10 — Insurance, liability, and third-party loss

### Function

Allocate responsibility for insured or uninsured loss, injury, property damage, and claims involving third parties.

### Core questions

- Is either party required to maintain insurance?
- What risk or property must be insured?
- Is proof of insurance required?
- Is there a waiver, indemnity, reimbursement, or liability allocation?
- Does liability depend on fault, possession, negligence, use, or another trigger?
- Are tenant property, landlord property, visitors, neighbors, or third parties treated separately?
- Does the insurance clause interact with repair or damage duties?

### Typical Router support

`INSURANCE`, `DAMAGE`, sometimes `OTHER_PAYMENT`, `NOTICE`, and `OTHER`.

### Boundaries

Insurance obligation is not the same as liability for damage.

A disclaimer is not automatically an insurance clause.

A duty to compensate a third party must not be assumed to be covered by insurance unless the contract says so or a separate evidence layer establishes it.

## 14. M11 — Notices, evidence, references, and procedural connectors

### Function

Connect other mechanisms by defining how information is communicated, when communication is treated as received, what evidence must be retained, and which other clauses or documents must be consulted.

This is a cross-cutting mechanism rather than an isolated economic subsystem.

### Core questions

- Which events require notice?
- Who must notify whom?
- In what form?
- To which address or channel?
- When is notice deemed delivered or received?
- Is proof of payment, receipt, inspection, consent, or another document required?
- Does a clause incorporate another clause or appendix?
- Does the referenced source exist and actually address the claimed subject?
- Is there a document-priority rule?
- Does missing evidence prevent a later conclusion?

### Typical Router support

`NOTICE`, often `OTHER`, plus the substantive family whose mechanism the notice serves.

### Boundaries

A generic notice rule does not create a notice requirement where the substantive mechanism contains none.

A deemed-receipt rule does not by itself establish that notice was actually sent.

A cross-reference must be checked semantically, not merely by clause number.

A missing referenced document is a first-class unresolved dependency.

## 15. Cross-mechanism connectors

Some facts are not mechanisms by themselves but connect mechanisms and must survive the first pass.

Preserve at least:

- actor / role;
- object / instrument identity;
- amount / formula;
- date / period;
- trigger;
- prerequisite;
- exception;
- consent requirement;
- notice form and timing;
- cure period;
- release / return event;
- cross-reference;
- document dependency;
- contradiction;
- unresolved value.

These are the edges from which the second-pass mechanism graph is built.

## 16. Suggested retrieval clusters

The Router output may be translated into module retrieval approximately as follows:

```text
TERM + OPTION
  -> M01 Term / continuation

RENT_PAYMENT
  -> M02 Rent payment

OTHER_PAYMENT
  -> M03 Other monetary obligations

PROPERTY_CONDITION + REPAIR + DAMAGE
  -> M04 Property condition / repair / damage

ACCESS
  -> M05 Use / occupancy / alterations / access

TRANSFER + EARLY_EXIT
  -> M06 Transfer / substitution / early exit

SECURITY
  -> M07 Security / performance assurance

BREACH
  -> M08 Breach / cure / termination

VACATING
  -> M09 End of tenancy / return / holdover

INSURANCE
  -> M10 Insurance / liability

NOTICE
  -> M11 Notice / procedural connector
  + the substantive module that caused the notice

OTHER
  -> do not discard;
     inspect for M00 contract-frame material,
     M05 use/alteration material,
     M11 document/reference material,
     or a genuinely new mechanism not represented by current Router families
```

This is retrieval guidance, not a deterministic final mapping.

Multiple modules may be loaded when one clause or dependency graph spans several mechanisms.

## 17. First-pass implications

The first structural pass should not attempt full legal or risk analysis.

Its job is to produce enough information to answer:

- Which mechanism modules are needed?
- Which clauses belong together?
- Which facts must remain separate?
- Which references or appendices must be retrieved?
- Which uncertainty blocks a later conclusion?

A strong first pass therefore optimizes recall of relevant mechanism families and links, not elegance of the final explanation.

## 18. Second-pass implications

The second pass should receive:

1. the Foundation Core;
2. the relevant mechanism module(s) from this map or a later detailed module;
3. only the contract blocks required for those mechanisms, including linked clauses and definitions;
4. explicit unresolved dependencies.

It should then reconstruct the mechanism rather than merely summarize the selected clauses.

## 19. What this map deliberately does not decide

This version does not decide:

- whether every mechanism must appear in every lease;
- whether an absent mechanism is a defect;
- whether a clause is fair, standard, unusual, valid, void, enforceable, or unlawful;
- statutory rights or mandatory duties;
- market-standard amounts or notice periods;
- detailed subtypes of every instrument;
- litigation or enforcement procedure;
- production risk scoring;
- final user-facing wording.

Those belong to separate verified layers.

## 20. Expansion rule

When a real or synthetic contract reveals a material mechanism not well represented here:

1. preserve it under `OTHER` or the nearest existing family without forcing a false fit;
2. record the mechanism and its distinguishing attributes;
3. compare it with existing modules;
4. add or split a mechanism only when the distinction changes how the contract must be read;
5. do not create a new category merely because a new term appears.

The ontology should grow by meaningful mechanism boundaries, not vocabulary count.
