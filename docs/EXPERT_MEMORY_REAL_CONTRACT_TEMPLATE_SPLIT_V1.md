# Expert Memory - real-contract template split v1

Status: **private local comparison, anonymized result, not legal Gold**. The
machine-readable map is
`research/question_engine/expert_memory/real_contract_template_split_v1.json`.

## Evidence boundary

The supplied private archive was treated as the primary source. Eight PDFs were
compared locally: they form seven distinct byte groups and include one additional
byte-identical copy. Comparison used PDF structure, corresponding-page layout and
printed clause organization. No OCR, external model, provider, source filename,
document identifier, hash value, page image or contract text is published. A
sidecar report found with the PDFs was explicitly excluded from evidence.

The anonymous RC01-RC07 inventory can be reconciled by page count, text-layer
presence, the exact duplicate count and the private multipage comparison. These
signals are used only to publish the following abstract family links.

## Confirmed families

| Family | Anonymous groups | Confirmed relation | Cohort |
|---|---|---|---|
| TF_A | RC01, RC04 | The same executed agreement in different captures; RC04 also contains the exact duplicate copy | Development, one content instance |
| TF_B | RC02, RC03, RC05 | One printed template across distinct agreement editions | Development |
| TF_C | RC06 | Structurally distinct singleton template | Independent test, reserved |
| TF_D | RC07 | Structurally distinct singleton template | Independent test, reserved |

All captures and editions of one template stay in one cohort. TF_A must contribute
at most one semantic content instance; its extra captures are not independent
contracts. TF_B is useful for development because it exposes within-template
variation. TF_C and TF_D remain outside semantic development and are reserved for
independent evaluation.

## Sanitized-source matching

No supplied original is positively established as the source of the existing
`contract_001` Golden Fixture. RC07 is inconsistent with that fixture's printed
term and section structure; the other RC links remain `UNKNOWN`. The fixture is
selected for the next deep expert-style review because it is already sanitized,
but it is not eligible for training or cohort scoring until its private family
link is resolved.

The prior two-contract mechanism matrix is aggregate sanitized research. It does
not contain trustworthy per-contract source identity, so its original RC groups
and template families remain `UNKNOWN`. Similar dates, topics, page counts or
filenames are not sufficient evidence.

## Remaining uncertainties

- Equal-title/equal-size Library records outside the eight supplied PDFs are not
  byte-verified and cannot extend the family findings.
- The Golden Fixture's positive private-family identity is unresolved and owner
  text review is still pending.
- The two originals behind the aggregate research cannot be reconstructed from
  trustworthy repository evidence.
- Template grouping does not establish legal correctness, mechanism coverage,
  specialist review or Gold labels.

Offline checks:

```bash
python research/question_engine/expert_memory/validate_real_contract_template_split.py
python -m unittest tests.test_expert_memory_source_audit
```
