# Expert Memory — real-contract mechanism coverage v1

Status: **source-scoped sanitized research, not legal Gold, not a production oracle**. Data: `research/question_engine/expert_memory/real_contract_coverage_v1.json`; offline checker: `validate_real_contract_coverage.py`.

## Three evidence scopes, deliberately not merged

| Source | Actual evidence | What is still unknown |
|---|---|---|
| `golden_contracts/contract_001_he.txt` + metadata | Three-page sanitized **printed** text, assistant visual two-pass review; printed clause locators available | Owner text-level signoff, any unseen annexes or handwritten content, relation to private RC01–RC07 |
| `dispute_practice/cross_contract_mechanism_matrix_v1.json` | Aggregate mechanism classification from **two previously sanitized** real-contract research passes (13 families, source frequency 1 or 2) | Which particular private RC group supplied each passage; whether the Golden Fixture overlaps either contract |
| `expert_memory/real_contract_inventory_v1.json` | Seven anonymized private PDF byte groups, technical page/duplicate metadata | **All content coverage UNKNOWN**, all template families UNVERIFIED, all development/holdout cohorts UNASSIGNED |

An aggregate `seen_in_contracts=2` is inherited research metadata, **not** two newly inspected PDFs, two owner-reviewed records or proof that the Golden Fixture is a third independent template. `NOT_ESTABLISHED_IN_SANITIZED_FIXTURE` means **unknown**, not absent from the original.

## Mechanism coverage (first approved sanitized fixture)

The existing two-contract matrix covers 13 families. Ten have traceable printed clause evidence in the already committed Golden Fixture: security/enforcement (§§4, 11), exit/assignment (§§7–8), sanctions/overlap (§§4, 9, 17), condition/defects (§§9, 12), cancellation/notice (§§4, 19, 21), option/renewal (§§3–4, 11), utilities (§§5–6), access (§15), alterations/restoration (§§9, 14, 16), and third-party indemnity (§9). Broad **no-setoff**, **shared-meter accounting** and **handwriting-dependent inventory** are *not established* in this sanitized printed fixture, even though the prior two-contract matrix identified them elsewhere. Section 9's limited repair-setoff route must not be mistaken for a broad no-setoff prohibition. Handwriting is explicitly excluded from the Golden Fixture.

## Seven cross-clause challenges for an expert-style reading

The dataset records source clauses, one specific expert question and a forbidden shortcut for each challenge. These cover: inconsistent nominal term/calendar dates versus payment/option terms; rent cheques versus security and ambiguous bank-guarantee return wording; early exit versus transfer consent; condition waiver versus repair allocation and the **unseen** Appendix B; cancellation versus notice/cure versus physical eviction; separately triggered money heads and security; and third-party reimbursement versus ordinary repair obligations.

These are **checks that a future Question Engine should perform**, not claims that a court would enforce/reduce any clause or that an external annex exists. A suspected issue may be `CONFIRMED`, `NARROWED` or `CLEARED` only after it rereads the relevant clauses and verifies missing evidence. Do not turn generic cross-clause checks into user questions unless a specific missing answer changes analysis.

## Next small PR

`expert-memory-real-contract-template-split-v1`: privately match already authorized originals to sanitized source identities (without committing identities), determine duplicated editions and true template-family overlap, then reserve *family-disjoint* development and holdout cohorts. If family matching cannot be verified without exposing restricted material, leave groups UNASSIGNED and record precisely which missing evidence blocks the split. Only then start a deep, manually reviewed mechanism map of one chosen sanitized real contract. The five court originals and the full current 2025 cheque procedure remain parallel research gaps.

No raw contract PDF, file name, contact details, source hash, OCR, new provider call, embedding/RAG, database or runtime integration is introduced.
