# Expert Memory — private real-contract inventory v1

Status: **metadata-only inventory**, 2026-09-23. The originals remain in the user's personal Library. Public repository artifact: `research/question_engine/expert_memory/real_contract_inventory_v1.json`. No PDF, filename, exact property, party identity, Library ID, raw SHA-256, scan or contract transcription is committed.

## Step 1: discovered PDF groups

A targeted search of the project Library folder and Library root found **14 contract-PDF records** that cluster by title and size into **seven candidate document groups**. Eight copies from these groups could be read as local bytes: seven distinct SHA-256 groups and one independently confirmed identical duplicate. Other equal-name/equal-size copies could not be byte-compared; they are *duplicate candidates*, not proven identical versions. The Library search is not certified exhaustive over all historical uploads.

| Anonymous ID | Sampled pages | Searchable PDF text | Discovered Library records | Duplicate evidence |
|---|---:|---|---:|---|
| RC01 | 6 | No; scan | 1 | Single |
| RC02 | 6 | Yes; printed PDF layer | 4 | Other copies match filename and byte length only |
| RC03 | 6 | No; scan | 3 | Other copies match filename and byte length only |
| RC04 | 6 | No; scan | 3 | One other copy is byte-identical; third copy unverified |
| RC05 | 5 | No; scan | 1 | Single |
| RC06 | 4 | No; scan | 1 | Single |
| RC07 | 3 | No; scan | 1 | Single |

These IDs identify discovered *document groups*, **not independently verified different property templates**. A later content-level comparison may merge related editions or distinguish visually similar files; neither action is inferred from filename alone.

## Step 2: coverage map (next small PR)

First use the **already sanitized** `golden_contracts/contract_001_he.txt` and the existing research matrix of two sanitized contracts. Their original-PDF identities **have not been matched** to RC01–RC07; do not infer a match merely because both have three pages. Define the mechanism-coverage columns and mark unknowns. Where original content is later needed, process it privately and commit only a PII-reviewed derivative; no full-contract external-model calls while frozen.

## Step 3: select a development / independent test split

Privately compare common clause wording to identify actual template families and amendments. Only then reserve one or more **different** families as held-out evaluation, with all duplicated copies and amendments in the same cohort. Select a remaining sanitized contract for a first manual mechanism map and independent review. Do not relabel the existing synthetic five ExpertCase seeds as verified Gold.

The parallel gaps remain open: obtain original court decisions for five case-law leads and the full current Enforcement Authority cheque procedure. Neither should block this inventory or be treated as verified merely because metadata exists.

Offline validator: `python research/question_engine/expert_memory/validate_real_contract_inventory.py`; regression tests are included in the existing Expert Memory CI.
