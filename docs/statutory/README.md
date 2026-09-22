# Statutory snapshots

This directory stores versioned, source-attributed statutory snapshots for deterministic Question Engine work.

The files here are **not** substitutes for the official Knesset source and are not user-facing legal advice. They exist so code and tests can work against explicit effective-date metadata and normalized rules instead of relying on an LLM's memory or on third-party summaries.

## Source hierarchy

1. The official Knesset National Legislation Database is the authority for current law and amendment history.
2. Official Knesset publications in `ספר החוקים` are the authority for the text and commencement of a historical amendment.
3. Repository JSON snapshots are normalized engineering representations of rules supported by those official sources.

A repository snapshot must never be treated as current merely because it exists. Before production use, the engine must resolve the contract date, applicable amendment/version, commencement rules, indexed thresholds, and any later amendments.

## 2017 residential-rental reform

`ISRAEL_RENTAL_AND_LOAN_AMENDMENT_2017_V1.json` records a machine-readable historical snapshot of Amendment No. 1 to `חוק השכירות והשאילה, התשל״א-1971`, the reform commonly called `שכירות הוגנת`.

Official source metadata:

- amendment: `חוק השכירות והשאילה (תיקון), התשע״ז-2017`;
- Knesset law item: `2006776`;
- publication: `ספר החוקים 2649`, starting at p. 1028;
- publication date: `2017-07-19`;
- commencement: 60 days after publication, i.e. `2017-09-17`;
- official publication PDF: `https://fs.knesset.gov.il/20/law/20_lsr_389390.pdf`;
- official legislation page: `https://main.knesset.gov.il/Activity/Legislation/Laws/pages/lawbill.aspx?lawitemid=2006776&t=lawsuggestionssearch`.

The JSON intentionally stores normalized rule data rather than a copied full-text statute. That makes the snapshot directly usable by Python and avoids confusing a historical 2017 text with the current consolidated law after later amendments.

## 2026 enacted rental-security amendment — deferred commencement

`ISRAEL_RENTAL_AND_LOAN_AMENDMENT_2026_V1.json` is a **separate versioned overlay**, not a silent replacement of the 2017 historical baseline. It records Amendment No. 3 to the Rental and Loan Law within the enacted 2026 Economic Programme Law (Chapter VI, §24). The change replaces §25י(a) definitions, adds guarantees from defined licensed non-bank providers to the opening of §25י(b), and **does not** directly rewrite §25י(c)–(e) in the amending §24.

- Publication: `ספר החוקים 3510`, 2026-03-31, printed pages 363–364 (§24) and 370 (§37).
- [Official Knesset publication](https://fs.knesset.gov.il/25/law/25_lsr_12846788.pdf); [readable reproduction of the official Gazette](https://www.law.co.il/media/computer-law/economic_plan_law_2026.pdf#page=14).
- Commencement: §37 makes Chapter VI effective **six calendar months after publication**, recorded as `2026-09-30`. On the snapshot's `2026-09-22` review date this enacted text was **not yet operative**.
- Provenance caveat: the official Knesset PDF URL was identified, but direct fetching of those official-domain bytes failed during this review; pp. 363–364 and 370 were read in the publicly available Gazette reproduction and checked against an independently indexed publication transcript. **Byte identity of the reproduction and official-domain PDF is not established.**
- Keep the January 2026 **government bill** as a distinct legislative-history record; do not cite its proposed §40 as the enacted amendment.
- The overlay is **not wired to runtime** and cannot by itself establish a particular guarantee provider's license, lease applicability, judicial interpretation, or that a security cheque automatically falls under the cash/bank-guarantee cap.

The offline Expert Memory audit validator cross-checks the overlay against the separate enacted-source entry and its deferred-effect claims. Future edits require a new review record; do not rewrite the source-anchored 2017 snapshot.

## Maintenance rule

When a later amendment changes a project-relevant section, add a new dated snapshot or overlay. Do not silently edit an older snapshot to make it look current. Historical snapshots should remain stable once merged.
