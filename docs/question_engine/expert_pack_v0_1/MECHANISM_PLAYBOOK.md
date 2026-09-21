# Expert Pack v0.1 — Mechanism Playbook

Status: experimental expert-pattern map. Use together with `CORE_PROTOCOL.md`.

The playbook describes what must be connected before a mechanism is understood. It is not a list of automatic risks.

## 1. Security instruments

Analyze each instrument separately.

Follow the chain:

```text
instrument identity
-> amount
-> date
-> payee / other stated fields
-> blank fields
-> authority to complete blanks
-> secured obligation
-> realization trigger
-> amount basis
-> notice
-> cure opportunity
-> realization method
-> return trigger
-> return deadline
```

Also check:
- whether several instruments secure the same obligation;
- whether guarantor coverage is separate;
- whether option/renewal requires extension or replacement of security;
- whether a separate security document is referenced and present.

Common traps:
- treating "security cheque exists" as complete analysis;
- moving a return deadline from utility cheques to a security cheque;
- converting "payee not stated in contract" into "physical cheque has blank payee";
- collapsing security cheque, promissory note, bank guarantee, rent cheques, and utility cheques into one generic deposit.

## 2. Early exit / replacement tenant

Build one practical exit model from:
- continuing rent liability;
- replacement-tenant route;
- candidate requirements;
- landlord approval requirement;
- approval/refusal standard;
- assignment/subletting restrictions;
- release trigger;
- any additional payment consequence.

Common traps:
- reading a general assignment/subletting prohibition as automatically defeating a specific replacement-tenant clause;
- borrowing a notice period from a sale, renewal, or unrelated clause;
- assuming departure itself ends future rent liability when the contract states another release trigger.

## 3. Payment mechanics

Preserve all payment facts before reconciling them:
- rent amount;
- number of payments;
- cheque count;
- bank-transfer/deposit instructions;
- due dates;
- post-dated instruments;
- separate utility or security instruments.

If the text gives multiple incompatible payment descriptions, do not normalize them. Record the inconsistency and identify which facts belong to which stated mechanism.

Common trap: selecting the most plausible payment scheme and discarding the rest.

## 4. Breach / notice / cure / termination

Read together:
- stated breach events;
- definition of material/fundamental breach;
- clause-specific breach classifications;
- notice requirement and form;
- cure availability and cure period;
- exceptions to cure;
- cancellation right;
- cancellation effective point;
- vacancy demand and deadline;
- any immediate-vacancy or self-help wording.

Common traps:
- turning a cure period for rent arrears into a universal cure period;
- treating broad "fundamental breach" language as the full termination mechanism without checking special procedures;
- reporting immediate termination while ignoring a specific notice/cure rule that narrows it.

## 5. AS-IS / defects / repairs

Read together:
- entry-condition statement;
- inspection acknowledgment;
- AS-IS or waiver wording;
- known-defect list or condition protocol;
- hidden/pre-existing defect treatment;
- landlord repair responsibility;
- tenant repair responsibility;
- ordinary wear;
- self-help/reimbursement/set-off wording;
- return-condition obligations.

Common trap: treating AS-IS as a standalone conclusion when repair or hidden-defect clauses materially qualify it.

## 6. Return / inspection / holdover

Build the full end-of-tenancy chain:
- required return condition;
- cleaning/painting/restoration;
- ordinary-wear exception;
- pre-return inspection;
- defect protocol;
- correction opportunity and period;
- contractual return/handover date;
- holdover trigger;
- holdover amount/formula and accrual period.

Common trap: surfacing only the holdover sanction while omitting a contractually supplied inspection/correction process that affects how the end-state is reached.

## 7. Option / renewal

Check:
- whether a renewal mechanism actually exists;
- right holder;
- whether further consent is required;
- renewal duration;
- rent amount/formula/external dependency;
- activation actor;
- notice form/deadline/period;
- performance prerequisites;
- security continuation;
- referenced addendum or external writing.

Common traps:
- treating an option mention as proof that no option exists because some details are unresolved;
- treating an option heading as proof that every activation/economic detail is known;
- ignoring security-continuity requirements.

## 8. Internal references and document dependencies

For every material reference:
- verify the referenced clause exists;
- verify it actually addresses the claimed subject;
- distinguish a wrong/broken reference from an unresolved interpretation;
- identify referenced appendices, guarantee documents, inventories, or protocols and whether they are present.

Common traps:
- using the nearest clause number as the source;
- calling an optional clause "missing" merely because an ideal contract might contain it;
- ignoring a genuinely referenced missing document.

## 9. General cross-clause test

When two clauses appear to conflict, test these possibilities before concluding contradiction:

1. one is general and the other specific;
2. one creates an explicit exception;
3. they apply to different actors;
4. they apply to different instruments;
5. they apply to different periods;
6. one depends on an external document;
7. they are genuinely inconsistent.

Do not choose one interpretation merely because it is cleaner.

## 10. Bounded catch-all

After the known mechanisms are reviewed, perform one final pass for a material mechanism not covered by the playbook.

Promote nothing into a "standard rule" from one contract. Preserve the new mechanism as a candidate pattern until repeated evidence justifies adding it to the playbook.
