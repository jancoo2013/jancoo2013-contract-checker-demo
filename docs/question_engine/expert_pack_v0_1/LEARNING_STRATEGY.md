# Expert Memory — Learning Strategy and Foundation Core v0.1

Status: experimental model-teaching/context strategy for the Expert Memory track.

Purpose: define how lease-domain knowledge should be presented to a general-purpose model so that it learns the structure of residential-lease reasoning from general principles to specific mechanisms without receiving an oversized flat glossary in every prompt.

This document is not a legal rule source, not a statutory baseline, not model-weight training, and not a production runtime contract. It does not promote any ontology item, Router family, Gold label, or legal conclusion. Use it together with the evidence discipline in `CORE_PROTOCOL.md` and the domain-specific patterns in `MECHANISM_PLAYBOOK.md`.

## 1. Working hypothesis

The current hypothesis is that model quality may improve when lease analysis is taught as a hierarchy:

```text
foundation: what a lease is and how contractual mechanisms work
-> structural discovery / routing
-> targeted mechanism knowledge
-> cross-clause reconciliation
-> completeness audit
```

The alternative we are explicitly avoiding is a single expanding prompt containing a large flat list of terms, instrument names, risk patterns, statutory rules, and examples.

The model should first learn the type of system it is reading, then identify which parts of that system are present, and only then receive the detailed knowledge needed for those parts.

This is an empirical strategy. It must be tested against held-out or concealed examples; it is not assumed correct merely because the hierarchy is intuitively appealing.

## 2. Context-loading strategy

Do not send a complete domain textbook on every pass.

Use a small stable foundation core plus only the modules required by the current task:

```text
always:
  Foundation Core

pass 1:
  Foundation Core
  + Router / structural-discovery instructions

pass 2:
  Foundation Core
  + only the mechanism modules selected by pass 1

pass 3:
  Foundation Core
  + linked clauses / definitions / referenced-document evidence
  + reconciliation instructions

final audit:
  completeness checklist / inventory
```

The Router is therefore an indexing and retrieval layer, not the conceptual foundation of the ontology.

A growing glossary may still be useful, but concepts should be taught through function, mechanism, attributes, and boundaries rather than as isolated vocabulary.

## 3. Pass strategy

### Pass 1 — structural discovery

Goal: determine what the supplied contract contains before evaluating it.

The model should:

- identify clause or semantic-block boundaries;
- identify the functional families present;
- preserve multiple families when one clause participates in several mechanisms;
- identify definitions and internal references;
- identify referenced appendices or external documents;
- identify obvious cross-clause dependencies for later rereading;
- preserve dates, periods, actors, amounts, instruments, conditions, and exceptions needed to route later analysis;
- mark missing pages, missing referenced materials, unreadable text, and handwriting dependencies;
- avoid risk scoring, legality conclusions, market judgments, or detailed mechanism conclusions.

Output should be a semantic map of the contract, not a final analysis.

### Pass 2 — targeted mechanism analysis

For each routed family or linked family set, load only the relevant mechanism knowledge.

Reconstruct the mechanism by asking:

1. Who is the actor or affected party?
2. What is required, permitted, prohibited, or conditioned?
3. What object, payment, right, obligation, or instrument is involved?
4. What event activates the rule?
5. When does it start, how long does it operate, and what ends it?
6. What prerequisites, limits, exceptions, or cure opportunities exist?
7. What follows from performance or non-performance?
8. Which other clauses, definitions, instruments, or documents modify the result?

Do not import a detail from one mechanism merely because another mechanism is nearby or similar.

### Pass 3 — reconciliation

Before retaining a conclusion, reread the connected material.

Check:

- general rule versus specific rule;
- rule versus explicit exception;
- definition versus operative clause;
- main text versus special condition or addendum;
- one actor versus another actor;
- one instrument versus another instrument;
- one period or trigger versus another;
- internal reference versus the text actually reached by that reference;
- present document versus referenced but unavailable document.

A candidate conclusion may be confirmed, narrowed, cleared, or left unresolved.

### Final completeness audit

Only after semantic analysis, use a checklist or inventory to ask whether a material topic was accidentally omitted.

The checklist is an audit device, not a substitute for reading. It must not manufacture a defect merely because an optional or idealized clause is absent.

## 4. Foundation Core

### 4.1 What a residential lease is

A residential lease is a system of interdependent agreements between landlord and tenant concerning temporary use of a dwelling.

Its function is broader than stating the rent amount. A lease can define:

- what is being provided for use;
- the term and conditions of use;
- payment amounts, timing, and methods;
- rights and duties of each party;
- allocation of expenses, responsibilities, and risks;
- security for performance of obligations;
- procedures for change, renewal, breach, termination, and return;
- evidence of what the parties actually agreed.

The document should therefore be understood as a system of mechanisms, not as a bag of independent sentences.

### 4.2 Completeness comes before strong conclusions

Before making contract-wide conclusions, establish whether the supplied material is complete enough for them.

Check for:

- all numbered pages;
- schedules, appendices, inventories, protocols, guarantee documents, or special conditions expressly referenced by the lease;
- later amendments or attachments when the supplied text says they form part of the agreement;
- readable source text for the propositions being analyzed.

If material is missing, analysis of the available text may continue, but conclusions that depend on the missing material must remain unresolved.

In particular, `not found in the supplied text` is not equivalent to `absent from the contract` unless completeness of the relevant contract package has been established.

### 4.3 Missing information is not a negative fact

Keep these states distinct:

- the text positively establishes a fact;
- the text positively establishes the opposite fact;
- the relevant field or rule is not found;
- the source is incomplete;
- the source is unreadable;
- the answer depends on handwriting;
- several reasonable readings remain possible.

Never convert lack of evidence into a definite negative fact.

### 4.4 Readability and handwriting boundary

Unreadable text must not be reconstructed from context.

Handwriting must not be semantically transcribed, reconstructed, or guessed for this project. If a material conclusion depends on handwriting, preserve an explicit unresolved dependency.

### 4.5 Every clause has a function inside a mechanism

Before evaluating a clause, determine what it does in the contract.

For a material condition, identify:

- actor;
- action, duty, permission, prohibition, or entitlement;
- object or obligation;
- trigger;
- timing and duration;
- prerequisites;
- limits and exceptions;
- consequence;
- links to other clauses or documents.

For example, the statement that a tenant provides a cheque does not fully describe the mechanism. The analysis may still need to establish which obligation it secures, its amount, trigger for use, notice or cure process if stated, realization method if stated, and return conditions.

### 4.6 Rights, duties, permissions, and prohibitions are different

Do not collapse deontic categories.

`may`, `must`, `must not`, `is entitled to`, and `is subject to` can create different mechanisms.

A permission is not automatically a duty. A duty imposed on one party does not automatically create a symmetric duty or equivalent right for the other party.

### 4.7 Definitions and references are operative evidence

If the contract defines a term, use that contractual definition when reading later clauses.

A material cross-reference is not resolved until the referenced clause or document has been checked for subject and content. A nearby clause number is not a substitute for the referenced source.

### 4.8 A lease has temporal logic

A contractual mechanism may:

- arise only after a trigger;
- require advance notice;
- contain a cure period;
- operate only during a defined term;
- renew or extend under conditions;
- end on a separate release or return event;
- interact with another event that happens earlier or later.

Time relationships are part of the mechanism, not incidental metadata.

### 4.9 Read the contract as a connected system

A right or duty may be distributed across several clauses.

A later clause may narrow, qualify, create an exception to, or contradict an earlier clause. A special rule may operate within a broader general rule. Different instruments or actors may have separate procedures even when they appear under one heading.

Do not finalize a material conclusion until the known linked provisions have been reconciled.

### 4.10 Keep four evidence layers separate

Distinguish:

1. what the document literally states;
2. what contractual mechanism follows from those statements;
3. what practical consequences that mechanism may create;
4. what external law may require, prohibit, limit, or modify.

Do not present a statutory rule as contract text. Do not present a practical hypothesis as a literal fact. Do not use external law unless an explicitly supplied and appropriately verified legal layer authorizes it.

### 4.11 Contract asymmetry is not itself a legal conclusion

The parties do not need to have mirror-image rights and duties for every topic.

An unusual, one-sided, or economically unfavorable term is not automatically unlawful. Conversely, a signed clause is not automatically free from external legal limits.

First reconstruct the contractual mechanism. Legal comparison is a separate layer.

### 4.12 Do not invent party intent

Analyze the recorded wording and the mechanism that can be supported from it.

Statements such as `the parties obviously intended...` are hypotheses unless directly supported by the document or another authorized evidence layer.

### 4.13 Preserve uncertainty

When a conclusion requires a missing page, appendix, definition, date, factual event, readable field, handwriting, or external rule that has not been supplied, the correct result is an explicit unresolved state.

Do not choose the most plausible completion merely to produce a clean answer.

### 4.14 The goal is accurate reconstruction, not maximum risk count

The objective is to reconstruct the contract accurately:

- which mechanisms exist;
- how rights, duties, payments, risks, and procedures are distributed;
- how provisions interact;
- what is directly established;
- what remains unknown;
- where a practical or legal question genuinely arises.

A longer list of warnings is not evidence of a better analysis.

## 5. Relationship to the existing Expert Pack

This strategy sits above the current Expert Pack components:

- `CORE_PROTOCOL.md` supplies operational evidence and multi-pass discipline;
- `MECHANISM_PLAYBOOK.md` supplies targeted domain mechanism patterns;
- `EXPERT_EXAMPLES.md` supplies contrastive examples of known model-reading failures;
- Router work supplies first-pass semantic indexing and retrieval.

The current experiment is to determine whether this hierarchy performs better than feeding a model the full accumulated domain material at once.

## 6. What this version deliberately does not contain

The foundation core deliberately excludes detailed rules for:

- security cheque versus promissory note versus guarantee;
- rent-payment variants;
- option and renewal mechanics;
- repair categories;
- early-exit mechanisms;
- breach categories and remedies;
- insurance;
- statutory caps or mandatory law;
- litigation or enforcement procedure.

Those belong to targeted modules or separately verified legal layers.

Keeping them out of the foundation is intentional: the foundation teaches the model how to think about a lease before teaching it every lease-specific mechanism.
