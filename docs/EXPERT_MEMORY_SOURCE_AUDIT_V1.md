# Expert Memory — primary-source audit packet v1

Status: **source discovery only, NOT independent legal verification**. Prepared 2026-09-22. Machine-readable registry: `research/question_engine/expert_memory/source_audit_packet_v1.json`. Existing five ExpertCase seeds remain synthetic, `UNVERIFIED`, and disconnected from runtime.

## Boundaries and source inventory

| Source ID | Official source | What was actually checked | Limit |
|---|---|---|---|
| `knesset_2017_amendment` | [Sefer HaHukim 2649, 19 July 2017, Rental and Loan Law amendment](https://fs.knesset.gov.il/20/law/20_lsr_389390.pdf) | Original publication text, §25י(b)–(e), §25טו | **Historical enacted text**, not certified 2026 consolidation |
| `knesset_current_law_index` | [Knesset National Legislation Database, lawitemid 2000596](https://main.knesset.gov.il/Activity/Legislation/Laws/pages/lawprimary.aspx?lawitemid=2000596&st=lawlaws&t=lawlaws) | Official law locator; current full-text endpoint did not yield independently readable text here | Catalogue pointer only; 2026 effective-date wording unresolved |
| `gov_2026_proposal` | [Government economic-programme bill, January 2026, proposed §40](https://www.gov.il/BlobFolder/legalinfo/state-budget-economic-plan-proposal-2026/he/state-budget_2026_Files_state-budget-economic-plan-proposal-2026.pdf) | Official search-index excerpt of proposal to amend §25י | **Proposal, not enacted law**; obtain official 2026 Gazette and verify commencement |
| `raa_2025_check_procedure` | [Enforcement Authority, cheque/note file-opening procedure PDF](https://www.gov.il/BlobFolder/policy/opening-notes-and-checks-file-regulation/he/opening-notes-and-checks-file-29-06-2025.pdf) | Official indexed extract, items 1–4, including conditions for security cheques | PDF body and current procedure version still require direct independent inspection |
| `raa_opening_service` | [Official opening service for unpaid cheques and promissory notes](https://www.gov.il/he/service/opening_promissory_notes_and_checks_file) | Official indexed service description | Procedural availability does not prove merits or banking outcome |
| `raa_objection_service` | [Official objection service for cheque/note execution](https://www.gov.il/he/service/objection_iou_repayment) | Official indexed service description | Does not supply an independently checked filing deadline or predict the ruling |

**Verification categories matter.** `PRIMARY_TEXT_READ` means the cited official publication text was accessible for the stated historical section. `INDEX_EXCERPT_ONLY` means an official indexed snippet was seen, **not** that the entire current source was inspected. `CATALOG_METADATA_ONLY` does not license a quotation or a current statutory conclusion. The government bill documents a proposal, not evidence of enacted wording. URL availability, document identity, interpretation, applicability and effective-date correctness are different checks.

## Narrow propositions, not legal verdicts

The 2017 publication can anchor the *historical wording* concerning permitted realization grounds, advance notice and opportunity to remedy, financial-outlay security caps, return, and scope exclusions. Whether those rules govern any given cheque or promissory note, and which effective-date version applies, remains an explicit legal question. A contractual 7- or 14-day notice period in a **synthetic** fixture is not established as the statutory period by this source.

The Authority's 2025 indexed procedure differentiates a security cheque merely being held from a cheque presented and dishonoured. The official opening and objection service summaries establish that distinct procedural routes exist. None proves that a bank will reject a cheque marked `לביטחון`, that a landlord's presentation is justified, that two instruments represent one debt, or that an objection succeeds.

## ExpertCase alignment and unresolved work

The registry cross-links all **five** existing `em_*` seed IDs to bounded source propositions; source links add **context/questions only** and do not alter the fixture's fact oracle, its `UNVERIFIED` review status, or the train/evaluation split. A different check and note must keep their own amounts, triggers, notice provisions and return clauses. The indexed 2026 bill proposition intentionally cannot be attached as enacted case authority.

Before any claim can be promoted, obtain and read the enacted 2026 publication (Sefer HaHukim 3510, published 31 March 2026) and effective-date terms; inspect the **full** currently applicable Authority procedure; establish instrument-by-instrument statutory scope with dated, applicable published judgments; then submit the disputed inferences and precise source passages for specialist review. The present packet contains **no verified case-law holding** and no legal Gold cohort. Source integrity tests prevent reference/review-state mistakes; they cannot certify the legal propositions.

Run: `python -m unittest tests.test_expert_memory_source_audit` and `python research/question_engine/expert_memory/validate_source_audit_packet.py`. The existing Expert Memory CI workflow now runs both checks offline. No real-contract, provider, OCR, RAG or database operations are introduced.
