# Blind Synthetic Lease Evaluation v1

Status: research-only evaluation packet for the current Expert Memory synthetic Router/cross-model step.

## Goal

Measure whether the current teaching architecture improves a fresh model's reading of a previously unseen synthetic residential lease.

The fixture is deliberately synthetic. It contains no real contract text, real parties, real address, signatures, account details, or recoverable PII.

The evaluation compares:

1. a stock-model baseline;
2. the same model with the current Expert Memory teaching/retrieval flow.

Do not tune the fixture after seeing a model's answer. If the fixture itself is later found defective, version it and record the reason instead of silently editing the expected answer.

## Files

Share with the tested model:
- `synthetic_blind_lease_v1_he.txt`

Do not share with the tested model:
- `synthetic_blind_lease_v1_gold.json`

The gold file is the sealed reference used after the run to score omissions, unsupported routing, cross-clause failures, and invented facts.

## Run record and source boundary

Before either run, record the exact model name/version as shown to the operator (mark it owner-reported if not independently verified), settings when available, input modality, date, complete prompts, source-file version and conversation boundaries. Use the same synthetic text fixture for both arms. This plain-text fixture tests source extraction and semantic analysis; it does not test photographic Hebrew reading, PDF rendering, or OCR. Keep those as separate modality diagnostics.

A copied Hebrew excerpt in a model answer is a candidate transcription. It is not independently verified source evidence. After both blind runs finish, compare material candidate facts and quoted spans against the supplied synthetic text and sealed reference. Record wrong or invented source details separately from Router omissions and cross-clause reasoning errors. A short excerpt that omits an unrequested part of a clause is not, by itself, proof that the model could not read it.

## Run A — stock baseline

Use a fresh conversation/context.

Provide only the synthetic lease and a neutral task equivalent to:

> Analyze this residential lease. Reconstruct the important contractual mechanisms, dependencies, uncertainties, and issues that would matter to a tenant. Do not assume facts not established by the supplied text.

Do not provide Foundation Core, Mechanism Map, Concept Lexicon, Expert Examples, playbook, or the gold file.

Save the complete model response unchanged. Source-reading accuracy for this arm is scored from claims in that response; this one-shot baseline has no separate extraction prompt and is not scored for Router labels.

## Run B — taught pipeline

Use another fresh conversation/context with the same model/version and, where controllable, the same reasoning settings.

### Pass 0 — source-bound candidates

Give the model the complete synthetic text and ask for candidate printed facts for every top-level clause `1`–`22` and `APPENDIX_A`, using those stable IDs. For each material fact ask for its clause locator, actor/action/object and any stated amount, time or condition; allow `UNREADABLE_OR_UNAVAILABLE`. No risk ranking, cross-clause resolution, legal conclusions, or example pairs from the sealed reference. Treat any model-copied Hebrew as a candidate transcription. Save this output unchanged.

Do not correct Pass 0 or reveal the sealed reference before Pass 1–3. The blind run observes whether an unsupported reading propagates. In a later operational use, independently verified source facts and explicit unknowns would gate any retained conclusion; this research packet does not implement that runtime gate.

### Pass 1

Provide:
- Foundation Core;
- Router / structural-discovery instructions from the current learning strategy;
- the synthetic lease.

Ask only for structural discovery / routing. Do not ask for risk or legal conclusions.

Use fixed response IDs `1`–`22` and `APPENDIX_A`, exactly one item per ID. Allow multiple families from this closed set: `TERM`, `RENT_PAYMENT`, `OTHER_PAYMENT`, `OPTION`, `NOTICE`, `SECURITY`, `REPAIR`, `PROPERTY_CONDITION`, `DAMAGE`, `TRANSFER`, `EARLY_EXIT`, `BREACH`, `VACATING`, `ACCESS`, `INSURANCE`, `OTHER`. Use `OTHER` for uncovered material content; it may coexist with a specific family. Require `{"schema_version":1,"items":[{"clause_id":"<supplied ID>","families":["<allowed label>"]}]}` as the *shape only*, with all 23 IDs actually returned. These IDs and labels define response format, not expected answers. Reread the supplied text; Pass-0 candidates are not source authority.

Save the output unchanged.

### Pass 2

Based on the Pass-1 routes, provide the selected Mechanism Map sections, Concept Lexicon slice, and connected source clauses. Freeze and record the exact family-to-module and clause-selection rule **before** inspecting any model output; apply it literally, including for multi-label and `OTHER` routes. The current packet does not define that deterministic rule, so a scored taught-pipeline run remains blocked until it is added. Do not fill this gap with operator judgment during the run.

Ask the model to reconstruct each mechanism and preserve unresolved dependencies.

Save the output unchanged.

### Pass 3

Provide the candidate analysis plus the connected clauses/references needed for reconciliation.

Ask the model to check:
- general versus specific rules;
- actor identity;
- instrument identity;
- trigger and timing;
- exception/override relationships;
- document references and unavailable material;
- unsupported factual or legal conclusions.

Save the output unchanged.

## Blindness rules

Do not turn a model-generated quote or paraphrase from Pass 0 into a verified corpus fact or a teaching example. Keep raw outputs, independent source checks, and later eligible annotations as separate records.

Before the tested model has finished:
- do not expose the gold JSON;
- do not mention the intended traps;
- do not tell the model which clauses are expected to be difficult;
- do not repair its Router output manually except by applying the retrieval rule literally;
- do not add real contracts to the model context.

The human/operator may know that the fixture is synthetic. "Blind" means the tested model has not seen the expected semantic answer.

## Primary measurements

Score both baseline and taught run against the same sealed semantic reference only after the prompts, segmentation, and retrieval rule are frozen. Compare source-reading errors, semantic omissions, invented facts, and linked-clause results across both arms. Router family omissions/extras apply only to Run B Pass 1 because Run A is not asked to emit Router labels. Report raw family counts; defer a weighted Router score until the sealed reference defines which expected families receive its critical versus noncritical omission weight. If a source-backed expected label is disputed, adjudicate and version the reference before scoring rather than silently changing it after seeing a response.

This A/B delta measures the whole taught staged pipeline against one-shot stock use. It does not isolate Foundation Core, pass splitting, or the operational source-verification gate. Run A has no dedicated extraction prompt, so only source claims actually made in its final answer can be compared with factual errors across the staged output.

Track:
- critical fact omissions;
- inverted or conflated mechanisms;
- unsupported invented facts;
- Router family omissions;
- unsupported extra routes;
- lost document dependencies;
- wrong cross-clause links;
- correct preservation of unresolved states.

The key experiment is the delta:

~~~text
stock model
vs
same model + our teaching/retrieval architecture
~~~

A better-sounding answer is not enough. Improvement must appear in the error counts and preserved dependencies.

## Fixture-specific package note

The supplied fixture includes Appendix A. Appendix B is referenced by the contract but intentionally absent from the supplied test package.

This note belongs to the operator protocol, not to the tested model's prompt. The model must discover the missing referenced material from the supplied contract/package itself.
