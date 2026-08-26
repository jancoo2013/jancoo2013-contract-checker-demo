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

## Maintenance rule

When a later amendment changes a project-relevant section, add a new dated snapshot or overlay. Do not silently edit an older snapshot to make it look current. Historical snapshots should remain stable once merged.
