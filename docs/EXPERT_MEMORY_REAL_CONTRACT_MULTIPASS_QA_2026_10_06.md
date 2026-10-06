# Real-contract multi-pass QA observation — 2026-10-06

Status: **USER_REPORTED_DEVELOPMENT_OBSERVATION_NOT_GOLD_OR_TRAINING**.

This note preserves the bounded results of the 2026-10-06 manual real-contract experiment. It does not publish the private contract, handwriting, signatures, addresses, account details, or raw images. It does not create Gold labels and does not change the runtime provider or legal-analysis layer.

## What improved on Pass 2

Compared with the earlier pass, the model materially improved structural reconstruction:

- it corrected a substantial part of the earlier clause-boundary shift around the transition `6b -> 7 -> 8a`;
- it reconstructed the lease term, payment mechanisms, option, security mechanisms, Appendix B reference, notices and holdover as separate topics more reliably;
- it independently surfaced two material internal tensions already visible in the printed source:
  - a stated `12 months` duration versus the printed start/end dates;
  - `שיק ערבון` in §11a versus `ערבות בנקאית` in §11b.

This is evidence that the multi-pass / Expert Memory structure can improve reconstruction. It is not a scored benchmark and does not establish a model-wide accuracy rate.

## What remained wrong

### 1. Clause-boundary integrity still failed

The source places the landlord-repair / tenant repair-and-setoff mechanism in §9b, third-party damage liability in §9c, and the independent vacating / return-of-possession duty in §10.

The model shifted these boundaries: repair content was assigned to §9c, third-party liability to §10, and the independent §10 vacating mechanism was effectively lost.

Lesson: a later semantic pass must re-check the printed clause number for every retained mechanism. A plausible mechanism with the wrong source clause is still a source error.

### 2. Distinct security instruments were detected, then silently merged

The model correctly noticed that §11a names a security cheque while §11b names a bank guarantee, but later transferred a return/release rule across those instruments and created a relation as though their identity had been established.

This violates the core instance rule:

- separate named instruments remain separate objects;
- an unresolved identity question does not authorize attribute transfer;
- an unresolved conflict cannot simultaneously be treated as resolved in the mechanism graph.

This is the clearest semantic-integrity failure from the run.

### 3. Relation integrity was not fully preserved

Additional observed problems:

- a conflict relation was created between the lease term and option even though the relevant inconsistency was internal to §3 rather than between those mechanisms;
- a relation target used a document-reference label where no real `MECH-...` target existed;
- relations therefore require both endpoint existence and source-supported identity/connection.

### 4. Monetary consequences need instance/type discipline

The `200 ₪ per day` holdover amount in §17 should not be collapsed into ordinary rent merely because it is monetary. It is a distinct holdover consequence / monetary sanction. §18 likewise should not be reduced mechanically to `RENT_PAYMENT` without reconstructing its own function.

Lesson: monetary amount does not determine mechanism type. Trigger and function do.

## Methodological conclusion

The run supports a narrower conclusion than “the model succeeded” or “the model failed”:

- Expert Memory / multi-pass prompting improved several earlier reconstruction errors;
- the remaining high-value failure classes are **clause-boundary integrity**, **object-instance identity**, **cross-instance attribute leakage**, and **relation validity**;
- these must be tested separately from source-reading/OCR quality.

A proposed Pass 3 was therefore designed to re-check every mechanism directly against the source, verify clause boundaries, keep distinct instruments separate, reject relations to non-existent mechanism IDs, and prevent an unresolved issue from being silently resolved elsewhere. That Pass 3 was not completed as a clean continuation of the same model run.

## Model/session continuity incident

The owner reported that the active Gemini 3.1 Pro quota was exhausted and the interface automatically switched to Gemini 3.5 Flash. The owner then observed loss of the prior conversational context.

This is a user-reported UI/session observation, not a provider log verified by this repository. Therefore:

- the 3.5 Flash continuation must not be scored as the next pass of the 3.1 Pro experiment;
- the incident is not evidence that Expert Memory caused context loss;
- a multi-pass evaluation is valid only while the declared model/version remains unchanged;
- if an automatic fallback changes the model, the prior run ends and later output is a separate observation;
- for reproducibility, each pass should have a recoverable self-contained input package, even when the UI normally preserves chat history.

## Durable rules extracted from the run

1. Re-verify `source_clause` from the printed source on every semantic pass; never inherit it blindly from the previous pass.
2. Preserve object identity: cheque, bank guarantee, promissory note, payment, notice, period, and document reference are separate instances unless the source explicitly links them.
3. Never transfer amount, trigger, timing, release, realization, notice, or return conditions across unresolved instances.
4. `unresolved` is non-authorizing: an unresolved identity or conflict cannot be used elsewhere as an established relation.
5. Every graph relation must point to existing mechanism IDs and be independently source-supported.
6. Monetary consequences are typed by function and trigger, not by the mere presence of money.
7. Scored multi-pass experiments require the same declared model/version for all passes; automatic model fallback terminates comparability.
8. Preserve the original model outputs as observations; do not silently repair them and then score the repaired version.

