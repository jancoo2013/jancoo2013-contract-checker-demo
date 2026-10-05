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

## Run A — stock baseline

Use a fresh conversation/context.

Provide only the synthetic lease and a neutral task equivalent to:

> Analyze this residential lease. Reconstruct the important contractual mechanisms, dependencies, uncertainties, and issues that would matter to a tenant. Do not assume facts not established by the supplied text.

Do not provide Foundation Core, Mechanism Map, Concept Lexicon, Expert Examples, playbook, or the gold file.

Save the complete model response unchanged.

## Run B — taught pipeline

Use another fresh conversation/context with the same model/version and, where controllable, the same reasoning settings.

### Pass 1

Provide:
- Foundation Core;
- Router / structural-discovery instructions from the current learning strategy;
- the synthetic lease.

Ask only for structural discovery / routing. Do not ask for risk or legal conclusions.

Save the output unchanged.

### Pass 2

Based on the Pass-1 routes, provide only:
- the relevant Mechanism Map sections;
- the relevant Concept Lexicon slice;
- the contract clauses required by those mechanisms and their explicit links.

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

Before the tested model has finished:
- do not expose the gold JSON;
- do not mention the intended traps;
- do not tell the model which clauses are expected to be difficult;
- do not repair its Router output manually except by applying the retrieval rule literally;
- do not add real contracts to the model context.

The human/operator may know that the fixture is synthetic. "Blind" means the tested model has not seen the expected semantic answer.

## Primary measurements

Score both baseline and taught run against the same sealed gold.

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
