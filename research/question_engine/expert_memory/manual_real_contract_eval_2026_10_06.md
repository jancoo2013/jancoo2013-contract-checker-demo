# Expert Memory — Real-contract manual evaluation observation, 2026-10-06

Status: research-only record of an owner-operated manual model evaluation. This file does not authorize production runtime changes, does not alter repository privacy/security invariants, and does not contain raw contract images, raw OCR, recoverable PII, signatures, bank/account identifiers, or verbatim private contract text.

## 1. Why this record exists

The synthetic blind-evaluation path prepared in PRs #313–#315 was not executed to completion. During the manual research session on 2026-10-06, the product owner explicitly changed the evaluation direction:

- stop inventing synthetic contracts for model-quality evaluation;
- stop splitting a lease into isolated fragments before model analysis;
- evaluate semantic reading on one complete real lease as a whole document;
- keep the existing rule that handwriting is detected but not semantically reconstructed or analyzed.

This is a research-method decision for owner-operated manual evaluation. It is **not** authorization for the repository runtime to send restricted raw material or PII to downstream LLMs. `SECURITY.md`, the Israel-only boundary, and the no-raw-downstream-LLM production constraint remain binding.

The existing synthetic fixtures are retained as historical research artifacts; they are not deleted or redefined as failed evidence.

## 2. Test material and model context

The manual test used one private, owner-supplied, three-page residential lease. The original pages are not committed to this repository and this record intentionally omits all party names, addresses, signatures, bank/account details, and other recoverable identifiers.

Observed model path:

1. Gemini 3.1 Pro — Pass 1 Router over the complete real lease.
2. Gemini 3.1 Pro — Pass 2 over the complete real lease, with:
   - the model's unchanged Pass 1 Router output;
   - current `CORE_PROTOCOL.md`;
   - current `MECHANISM_MAP.md`;
   - current `CONCEPT_LEXICON.md`.
3. Pass 3 was not completed on Gemini 3.1 Pro because the UI quota for that model was exhausted. The UI automatically switched to Gemini 3.5 Flash; the prior conversational context was no longer available to that model. No scored Flash semantic result was produced.

The test therefore provides qualitative evidence about Pass 1 and Pass 2 on Gemini 3.1 Pro, plus a process observation about model/version continuity. It does not provide a completed multi-pass score.

## 3. Pass 1 observation — Router alone was structurally useful but unreliable

The Router pass returned all requested clause identifiers and produced broad topical coverage, but it showed two important failure modes.

### 3.1 Consecutive clause-boundary shift

A contiguous region of the contract was mapped to the meaning of neighboring clauses rather than to the exact printed clause identifiers. The clearest sequence was approximately:

- clause 6b was routed as transfer-related although the printed clause concerned a non-rent monetary obligation assigned to the landlord;
- clause 7 was routed as early-exit/rent/term/vacating although the printed clause was a transfer/subletting restriction;
- clause 8a was routed as repair/property-condition/vacating/damage although the printed clause concerned continued rent liability after early departure;
- later clauses around 9–10 also showed boundary drift.

This is not merely a taxonomy disagreement. It is a source-localization error: semantic content was attached to the wrong clause number.

### 3.2 Over-routing

The model often attached every topic mentioned inside a clause as a Router family even when the clause's operative mechanism belonged to one narrower family. Security clauses were a clear example: the fact that an instrument secures rent, charges, or vacating obligations does not mean the security clause itself should automatically be routed as independent RENT_PAYMENT, OTHER_PAYMENT, VACATING, TERM, and OPTION mechanisms.

### 3.3 Implication

Router output cannot be treated as authoritative evidence or as a hard gate that is allowed to starve later semantic analysis. A later pass must be able to revisit source boundaries and override the Router.

## 4. Pass 2 observation — Expert Memory materially improved reconstruction

Pass 2 was given the complete real lease again, plus the full current Expert Memory teaching layers and the unchanged Router output.

The model corrected several of its own Pass 1 errors without being given the correct answer:

- corrected the 6b/7/8a routing shift;
- reconstructed separate rent, option, transfer, early-departure, repair, damage, security, notice, holdover, and document-reference mechanisms;
- recognized a missing referenced appendix as an unresolved dependency rather than inventing its contents;
- identified a printed internal term inconsistency: the stated duration and the printed start/end dates did not agree;
- identified a printed terminology mismatch between the security instrument named in one clause and the instrument named in the adjacent return clause;
- removed a false insurance interpretation from a liability-only clause.

This is meaningful evidence that the current Core Protocol + Mechanism Map + Concept Lexicon can improve semantic reading beyond the model's first structural pass. The improvement is qualitative; no formal accuracy percentage is recorded here.

## 5. Pass 2 residual failures

Expert Memory did not eliminate the two most important semantic-integrity errors.

### 5.1 Clause-boundary drift remained around clauses 9–10

Manual source review showed that the model still attached several mechanisms to neighboring clause numbers:

- the landlord-repair / tenant self-help and cost-recovery route belonged to the preceding printed clause, not the clause assigned by the model;
- third-party damage/liability belonged to the next printed clause, not the following one;
- the separate vacating/return-of-possession clause was consequently lost as an independent mechanism.

This indicates that semantic teaching can improve classification while still failing source localization.

### 5.2 An unresolved instrument conflict was simultaneously treated as resolved

The model explicitly recorded that two adjacent clauses used different instrument terms and marked the identity relationship as unresolved.

Despite that, it also created a `SECURITY_RETURN` mechanism and linked the return rule to the earlier security-cheque mechanism as though both clauses referred to the same instrument.

This is a critical consistency failure:

```text
model detects ambiguity
-> writes ambiguity into unresolved
-> simultaneously propagates an attribute across the ambiguous identity
```

The invariant needed for later work is therefore stronger than "mention uncertainty": an unresolved identity must block attribute migration and block graph edges that depend on the unresolved identity.

### 5.3 Graph-integrity defect

The Pass 2 answer also emitted at least one relation target that did not correspond to an existing `mechanism_id`. This is a structural validation failure independent of legal interpretation.

### 5.4 Smaller taxonomy issues

Several Router corrections remained debatable because monetary consequences were sometimes relabeled as ordinary rent rather than as a distinct monetary effect. These are lower priority than the source-boundary and unresolved-identity failures above.

## 6. What this session establishes

The strongest observations from the session are:

1. A complete real document exposed source-localization failures that synthetic planning alone did not resolve.
2. The Router is useful for recall/indexing but is not a reliable source map.
3. The current Expert Memory teaching stack can cause a general model to self-correct meaningful Router errors.
4. Expert Memory still needs an explicit invariant for **source-clause identity**.
5. Expert Memory still needs an explicit invariant for **unresolved object identity**:
   - if two instruments may or may not be the same, keep them separate;
   - do not migrate amount, return rule, realization rule, date, payee, or other attributes across them;
   - do not create graph relations that require the unresolved identity to be true.
6. A graph-level validator should reject relations to nonexistent mechanism IDs.
7. Model/version continuity is a controlled experimental variable. A silent model switch invalidates a same-model multi-pass continuation unless the entire required state is supplied again.
8. Conversation memory must not be the only carrier of experimental state. Any future reproducible multi-pass run should be restorable from an explicit packet, while still presenting the contract itself as a complete document rather than semantic fragments.

## 7. Model-switch observation

During the attempted next pass, the Gemini 3.1 Pro usage limit was exhausted and the UI automatically switched to Gemini 3.5 Flash. The newly active model did not retain the prior working context.

The session does **not** establish that Gemini 3.5 Flash is intrinsically worse at contract reading. It establishes only that the model/version changed and the previous conversational state was not available after that switch.

Future comparisons must record the exact model/version used for every pass and must not score a mixed-model sequence as one continuous run.

## 8. Evaluation direction after this session

For the current Expert Memory research direction:

- do not make the synthetic blind evaluation the next canonical model-quality task;
- prefer complete real-contract evaluation for manual research;
- do not split the contract into semantic fragments before the tested model reads it;
- preserve handwriting as blocked/unresolved rather than reconstructing it;
- keep Router as a revisable indexing hypothesis rather than an authority;
- evaluate source localization separately from semantic mechanism quality;
- require cross-pass consistency checks for unresolved identities and graph references.

Repository privacy/security rules remain unchanged. No real contract, raw image, raw OCR, or recoverable PII is to be committed to GitHub, CI, logs, or repository fixtures.

## 9. Next bounded research step

When testing resumes, the next useful bounded step is not another synthetic lease. It is to formalize and run a reproducible **complete-real-contract, full-document evaluation protocol** that measures at least:

- clause/source localization;
- mechanism reconstruction;
- object/instrument identity preservation;
- unresolved-dependency preservation;
- graph-reference validity;
- self-correction between Router and semantic passes;
- model/version continuity.

The protocol should record only sanitized evaluation observations in the repository. It must not weaken or bypass the production privacy/security boundary.
