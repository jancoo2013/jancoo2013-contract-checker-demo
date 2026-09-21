# Expert Pack v0.1 — Core Protocol

Status: experimental machine-facing reasoning protocol for the Question Engine.

Purpose: transfer expert reading habits for residential lease analysis with a small set of stable reasoning rules. This file is not a legal rule source, does not replace repository security/privacy constraints, and does not authorize use of external law or market practice.

## 1. Input boundary

Use only the sanitized contract material supplied for the run.

Do not:
- invent missing facts;
- infer physical cheque fields that are not described in the contract;
- use market practice, typical amounts, typical notice periods, or "standard contract" judgments;
- use statutory rules unless a separate verified statutory layer is explicitly supplied;
- reconstruct handwriting or redacted personal data.

Treat absence, blank value, ambiguity, missing referenced document, and handwriting dependency as different states.

## 2. Reading order

### Pass A — establish facts

Extract literal contract facts before evaluating them.

Preserve:
- instrument type;
- amounts;
- dates and periods;
- actor/role;
- stated trigger;
- stated exception;
- clause/document reference;
- blanks or unresolved values;
- apparent contradictions.

Do not silently normalize inconsistent facts into one "likely" interpretation.

### Pass B — build mechanisms

Do not analyze clauses as isolated sentences. Group facts into practical mechanisms.

Examples:
- security instrument -> trigger -> notice/cure -> realization -> return;
- early exit -> continuing liability -> replacement route -> approval -> release;
- breach -> classification -> notice/cure -> cancellation -> vacancy;
- entry condition -> AS-IS -> repairs -> defects -> return condition;
- return inspection -> correction opportunity -> handover -> holdover consequence.

A mechanism may be distributed across several clauses.

### Pass C — reconcile related clauses

Before retaining a concern, search for clauses that may narrow, qualify, create an exception to, or contradict the first reading.

Check:
- general rule versus specific rule;
- prohibition versus explicit exception;
- broad definition versus special procedure;
- main clause versus special condition/addendum;
- one instrument versus another instrument;
- one time period versus another time period;
- referenced clause/document versus nearby text.

A second pass may confirm, narrow, clear, or leave the issue unresolved.

## 3. Scope discipline

Never migrate a fact merely because two clauses are adjacent or discuss similar topics.

In particular:
- a return rule for one security instrument does not automatically apply to another;
- a cure period for one breach does not automatically apply to every breach;
- a notice period for sale/transfer does not automatically become an early-exit notice period;
- a general assignment/subletting prohibition does not automatically cancel a specific replacement-tenant route;
- a missing payee in contract text does not prove the physical cheque has a blank payee.

When several instruments, procedures, or periods exist, keep them separate until the contract explicitly links them.

## 4. Evidence discipline

The source of a fact is the clause or evidence block that actually states it.

Do not:
- cite a neighboring clause number because it is close;
- treat a heading as proof of every detail below it;
- replace a missing source with an assumption;
- paraphrase uncertainty into certainty.

If the evidence does not establish a field, mark it unresolved or not found.

## 5. Materiality discipline

The goal is not to turn every clause into a finding.

Prioritize mechanisms that materially affect:
- money exposure;
- ability to leave or renew;
- security realization;
- breach/cure/termination;
- repair and condition responsibility;
- return and holdover;
- internal contradictions or missing dependencies.

Routine facts may remain background facts when they do not change a material mechanism.

## 6. Final self-check

Before producing the report, verify:

1. Were related clauses read together?
2. Were different instruments kept separate?
3. Were all numbers tied to the mechanism that actually contains them?
4. Did any physical fact get inferred from contract silence?
5. Did any market norm or statutory rule enter without an explicit source layer?
6. Were contradictions preserved rather than "fixed"?
7. Were unresolved dependencies left unresolved?
8. Does each material conclusion have direct source support?

## 7. Questionnaire status in this experiment

For Expert Pack v0.1, the legacy Questionnaire/Skeleton is not a reasoning input.

The intended order is:

```text
Expert Pack reasoning
-> contract analysis
-> later completeness audit/checklist
```

A future questionnaire may verify that the expert process did not omit a required topic. It must not substitute for semantic reading or certify a model's own mistaken interpretation.
