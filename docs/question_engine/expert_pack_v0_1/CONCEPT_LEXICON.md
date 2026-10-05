# Expert Memory — Concept Lexicon v0.3

Status: experimental third learning layer for the Expert Memory track.

Purpose: teach a general-purpose model the concrete concepts that make up residential-lease mechanisms after it has learned the Foundation Core and the Mechanism Map.

This lexicon is not a Router schema, extraction schema, legal rule source, statutory baseline, Gold annotation set, risk catalogue, runtime contract, or claim that every concept must appear in every lease.

It consolidates the historical 30-concept research inventory, the later SECURITY cards, the two glossary decisions DOCUMENT_REFERENCE and REPAIR_COST_RECOVERY, and distinctions exposed by the Mechanism Map v0.2 and the currently reviewed sanitized/printed corpus. The current compact teaching set contains 54 top-level concepts plus 10 reusable temporal roles.

## 1. Position in the knowledge hierarchy

The teaching hierarchy is:

~~~text
Foundation Core
-> Mechanism Map
-> Concept Lexicon
-> detailed mechanism cards / examples
-> verified legal overlays where authorized
~~~

The operational analysis pipeline is different:

~~~text
pass 1:
  Foundation Core
  + compact structural / Router instructions

pass 2:
  Foundation Core
  + relevant Mechanism Map section
  + only the relevant Concept Lexicon slice
  + detailed cards/examples when needed

pass 3:
  linked clauses / definitions / referenced documents
  + reconciliation

final:
  completeness audit
~~~

The whole lexicon should not be loaded into every prompt merely because it exists.

## 2. Concept kinds

The kind field prevents different semantic levels from being treated as interchangeable.

- ACTOR_ROLE: a contractual role occupied by a participant.
- OBJECT: the dwelling, property, item, or other non-document thing to which a mechanism refers.
- DOCUMENT: a document-like contractual object such as an inventory, defects list, or inspection protocol.
- INSTRUMENT: a payment, security, guarantee, or similar operative instrument.
- OBLIGATION: a duty to pay, repair, vacate, restore, provide evidence, register an account, or perform another action.
- PERMISSION: a contractual permission or conditional entitlement.
- PROCEDURE: an ordered route made of actions, triggers, prerequisites, and consequences.
- CONDITION: a trigger, restriction, prerequisite, exception, or classification that affects another mechanism.
- ASSERTION: a contractual statement or acknowledgment about a fact, state, capacity, or condition that is evidence of what the document says but not independent proof that the statement is true.
- DEFINITION: an explicit contractual definition that assigns meaning to a term or role inside the document.
- RELATION: a directed semantic relation between actors, objects, payments, documents, or mechanisms.
- TEMPORAL_STRUCTURE: a contract-level interval or period such as the lease term itself, distinct from a deadline attached to an action.
- MONETARY_EFFECT: an amount or formula arising from a defined event beyond the ordinary principal obligation.
- DOCUMENT_LINK: a relation to another document, document version, protocol, appendix, or priority rule.
- SOURCE_STATE: status of a source or document version, not proof of its truth.
- EXTERNAL_DEPENDENCY: a value, source, proceeding, framework, or external rule whose content/effect must be checked outside the immediate clause.
- TEMPORAL_ROLE: a named role played by a date, duration, deadline, threshold, or delay.

Kinds describe how to reason about a concept. They are not production enums.

### Second-pass audit findings

The v0.3 audit compared v0.2 against the Foundation Core, Mechanism Map v0.2, the current Question Engine recurring inventory, Expert Pack examples/playbook, and the reviewed sanitized/printed contract mechanism packets.

The audit found two kinds of defects:

1. taxonomy errors: assertions were being labeled as conditions/relations, document objects were being labeled as document links, LEASE_TERM lacked a temporal-structure kind, and DISPUTE_FORUM was incorrectly typed as an external dependency rather than a contractual relation whose legal effect is external;
2. coverage gaps: contractual definitions, ordinary use/occupancy rules, landlord-side transfer/sale rules, property left behind after return, evidence-production duties, service/account registration duties, and externally referenced finance frameworks lacked explicit concepts.

v0.3 corrects those points without turning the lexicon into a clause checklist or runtime schema.

## 3. Global concept rules

For every concept:

- identify the target instance before attaching attributes;
- keep actor, object, trigger, amount, period, instrument, and source attached to that instance;
- preserve several instances of the same type separately;
- do not convert a contractual statement into proof that the stated event actually occurred;
- do not convert a missing value into the opposite fact;
- do not reconstruct handwriting or unreadable values;
- do not import attributes from a neighboring concept merely because wording, amount, or timing looks similar;
- a lexical match may suggest a concept but does not prove the complete mechanism;
- legal validity, enforceability, market practice, and statutory effect remain separate layers.

## 4. M00 — Contract frame, actors, object, and document structure

### PARTY_ROLE
- kind: ACTOR_ROLE
- definition: a role defined or used by the contract, such as granting party, tenant, guarantor, payer, occupant, or representative.
- essential_slots: role name; participants grouped under it; clauses that distinguish one participant; role-specific rights/duties.
- relations: CONTRACT_OBJECT, LETTING_ENTITLEMENT_CLAIM, payment and obligation concepts.
- do_not_confuse: named person; payer; occupant; guarantor; collective tenant role.
- evidence_boundary: several names in a header do not justify invented numbered roles if operative text treats them collectively.

### CONTRACT_OBJECT
- kind: OBJECT
- definition: the dwelling and other property expressly included in the lease relationship.
- essential_slots: dwelling/property description; included rooms; parking/storage; fixtures/furniture; exclusions; linked inventory.
- relations: PROPERTY_INVENTORY, CONDITION_ACKNOWLEDGMENT, VACATING_OBLIGATION.
- do_not_confuse: tenant property; common property; an item merely mentioned in a repair clause.
- evidence_boundary: do not supply an omitted address, item, or accessory from context or another edition.

### CONTRACT_DEFINITION
- kind: DEFINITION
- definition: an explicit contract rule assigning a meaning, role, scope, or referent to a term used elsewhere in the document.
- essential_slots: defined term; defining text; scope; target actor/object/mechanism; exceptions; clauses that rely on it.
- relations: PARTY_ROLE, DOCUMENT_REFERENCE, and any mechanism whose wording uses the defined term.
- do_not_confuse: ordinary-language meaning; an external legal definition; a cross-reference that does not itself define a term.
- evidence_boundary: apply only the definition actually supplied by the contract; do not expand it from common usage, another template, or external law without a separately authorized layer.

### LETTING_ENTITLEMENT_CLAIM
- kind: ASSERTION
- definition: the contract's statement that a granting party owns, holds, leases, controls, or otherwise claims authority to let the property.
- essential_slots: claimant role; claimed basis; target property; upstream agreement/source if named; qualification/dispute if stated.
- relations: PARTY_ROLE, CONTRACT_OBJECT, DOCUMENT_REFERENCE, EXTERNAL_PROCEEDING_REFERENCE.
- do_not_confuse: verified title; verified ownership; court-confirmed authority.
- evidence_boundary: the recital proves what the contract says, not the truth of title or the outcome of an external dispute.

### DOCUMENT_STATUS
- kind: SOURCE_STATE
- definition: the status of the supplied document or version, such as draft, signed agreement, later edition, amendment, receipt, or incorporated prior document.
- essential_slots: status asserted by source; date/version if printed; signature/execution evidence if safely available; relation to other versions.
- relations: DOCUMENT_REFERENCE, DOCUMENT_PRECEDENCE_RULE.
- do_not_confuse: printed proposal with executed event; later edition with amendment; recital with receipt.
- evidence_boundary: an unsigned or undated draft does not prove performance, delivery, or historical facts merely because it describes them.

### DOCUMENT_REFERENCE
- kind: DOCUMENT_LINK
- definition: an explicit relation from one clause/document to another clause, appendix, draft, inventory, guarantee, protocol, judgment, or external source.
- essential_slots: source clause; target; relation type; target availability; exact reference; dependency created by missing text.
- relations: DEFECTS_LIST, PROPERTY_INVENTORY, CONDITION_PROTOCOL, DOCUMENT_PRECEDENCE_RULE, EXTERNAL_PROCEEDING_REFERENCE.
- do_not_confuse: mere thematic similarity; assumed contents; absence from supplied packet versus absence from original contract.
- evidence_boundary: preserve an unavailable target as an unresolved dependency; never reconstruct its content.

### DOCUMENT_PRECEDENCE_RULE
- kind: DOCUMENT_LINK
- definition: a clause that states how main text, appendix, prior draft, special condition, amendment, or later writing relates when sources overlap or conflict.
- essential_slots: source documents; claimed priority; entire-agreement/supersession wording; written-change requirement; exception/incorporation.
- relations: DOCUMENT_STATUS, DOCUMENT_REFERENCE.
- do_not_confuse: reference to a document with a rule that it prevails; general entire-agreement wording with exclusion of an expressly incorporated document.
- evidence_boundary: do not resolve a conflict whose incorporated target text is unavailable.

### EXTERNAL_PROCEEDING_REFERENCE
- kind: EXTERNAL_DEPENDENCY
- definition: a contractual reference to a court case, judgment, dispute, estate matter, administrative proceeding, or other external adjudicative event.
- essential_slots: stated proceeding; parties/subject if sanitized and relevant; date/citation if available; contractual consequence claimed; source availability.
- relations: LETTING_ENTITLEMENT_CLAIM, DOCUMENT_REFERENCE, DISPUTE_FORUM.
- do_not_confuse: the contract's recital with a verified judgment or verified outcome.
- evidence_boundary: external facts remain unverified until separately sourced.

## 5. M01 — Term, continuation, and renewal

### LEASE_TERM
- kind: TEMPORAL_STRUCTURE
- definition: the initial tenancy period expressed by dates, duration, or both.
- essential_slots: start; end; duration; unit; effective boundaries.
- relations: RENT_OBLIGATION, LEASE_EXTENSION, VACATING_OBLIGATION.
- do_not_confuse: option period; replacement tenant's new term; number of rent cheques.
- evidence_boundary: preserve date/duration conflict instead of silently choosing one; do not calculate blocked handwritten values.

### LEASE_EXTENSION
- kind: PROCEDURE
- definition: a route for continuing the tenancy after the initial term with its own holder, prerequisites, notice, consent, duration, and economic terms.
- essential_slots: holder; extension duration; activation event; notice; consent; performance prerequisites; rent formula; new instruments/security.
- relations: LEASE_TERM, CONTRACT_NOTICE, RENT_OBLIGATION, SECURITY_RETURN.
- do_not_confuse: unconditional option; request to negotiate; replacement tenant's new term.
- evidence_boundary: the word "option" does not erase stated consent or performance conditions; price terms do not prove exercise.

## 6. M02 — Rent and payment mechanics

### RENT_OBLIGATION
- kind: OBLIGATION
- definition: the principal obligation to pay rent for a defined period.
- essential_slots: payer; creditor; amount/currency; accrual period; due logic; price formula; applicable term.
- relations: LEASE_TERM, RENT_PAYMENT_SCHEDULE, PAYMENT_CHANNEL, LEASE_EXTENSION, EARLY_DEPARTURE_PAYMENT.
- do_not_confuse: security amount; utility advance; holdover compensation; breach compensation.
- evidence_boundary: multiple payment instruments or recipients do not automatically multiply the rent obligation.

### RENT_PAYMENT_SCHEDULE
- kind: PROCEDURE
- definition: the method, count, dates, and instrument instances used to discharge rent.
- essential_slots: payment method; declared count; itemized instances; dates; amounts; recipient/channel; deposit/presentation timing.
- relations: RENT_OBLIGATION, PAYMENT_CHANNEL, LEASE_TERM.
- do_not_confuse: rent accrual; security cheque; actual physical delivery; bank presentation.
- evidence_boundary: preserve disagreement between a heading count and itemized schedule; do not create extra payments to reconcile wording.

### PAYMENT_CHANNEL
- kind: RELATION
- definition: the route by which money or a payment instrument is directed to a recipient/account without changing the identity or amount of the underlying obligation by itself.
- essential_slots: underlying obligation; payer; recipient/account; channel; allocation if split; timing.
- relations: RENT_OBLIGATION, RENT_PAYMENT_SCHEDULE, OCCUPANCY_CHARGE.
- do_not_confuse: two recipients with two separate debts; payee of security with creditor of rent.
- evidence_boundary: a split transfer instruction does not by itself double the monthly obligation.

### EXTERNAL_VALUE_LINKAGE
- kind: EXTERNAL_DEPENDENCY
- definition: a clause that makes an amount depend on an external index, currency rate, bank/reference rate, or another value outside the immediate contract text.
- essential_slots: target amount; external value/source; base date/value; comparison date; direction/formula; floor/cap if stated.
- relations: RENT_OBLIGATION, LATE_PAYMENT_INTEREST, monetary concepts in M12.
- do_not_confuse: calendar duration; fixed percentage increase; an external framework whose economic/legal effect is not merely a numeric index.
- evidence_boundary: the clause establishes dependency, not the actual external value unless separately supplied.

## 7. M03 — Other monetary obligations

### OCCUPANCY_CHARGE
- kind: OBLIGATION
- definition: an obligation to pay a specified running cost associated with use or occupancy of the property.
- essential_slots: charge type; payer; creditor/recipient; period; calculation basis; fault condition if any; proof/receipt requirement.
- relations: UTILITY_ADVANCE_RECONCILIATION, PAYMENT_CHANNEL, CONTRACT_NOTICE, REPAIR_OBLIGATION.
- do_not_confuse: physical repair; damages; utility security cheque.
- evidence_boundary: a fault-qualified consumption rule must not be extended to a non-fault event.

### UTILITY_ADVANCE_RECONCILIATION
- kind: PROCEDURE
- definition: a process for paying utility advances and later comparing them with measured or allocated consumption.
- essential_slots: service; advance; reconciliation period; meter; allocation denominator; additional payment; refund/credit rule.
- relations: OCCUPANCY_CHARGE, PAYMENT_CHANNEL, SECURITY_CHECK.
- do_not_confuse: direct supplier payment; utility security; water rule with electricity rule.
- evidence_boundary: a clause requiring a shortfall payment does not imply a symmetric overpayment refund unless stated.

## 8. M04 — Condition, defects, repair, and damage

### REPAIR_OBLIGATION
- kind: OBLIGATION
- definition: a duty assigned to a party to correct a defined defect or malfunction under stated conditions.
- essential_slots: responsible role; defect/system; cause/category; notice; urgency; response period; exclusions; cost allocation.
- relations: REPAIR_COST_RECOVERY, CONTRACT_NOTICE, DAMAGE_RESPONSIBILITY, CONDITION_ACKNOWLEDGMENT.
- do_not_confuse: utility bill; damage indemnity; condition acknowledgment.
- evidence_boundary: a broad condition waiver does not erase a separate printed repair duty merely by proximity.

### REPAIR_COST_RECOVERY
- kind: PROCEDURE
- definition: a directed route in which one party performs or arranges repair work and may seek the resulting cost from another party after stated prerequisites.
- essential_slots: original repair obligor; acting party; prerequisite notice; response/cure condition; performed work; proof/receipts; claimant; debtor; reimbursement/set-off sequence.
- relations: REPAIR_OBLIGATION, CONTRACT_NOTICE, SETOFF_RULE, RENT_OBLIGATION.
- do_not_confuse: automatic right to repair; automatic debt; tenant-only reimbursement; damage compensation.
- evidence_boundary: direction matters. Landlord-to-tenant recovery and tenant-to-landlord recovery are different instances of the same concept.

### TENANT_REPAIR_RECOVERY
- kind: PROCEDURE
- definition: historical narrower specialization of REPAIR_COST_RECOVERY where the tenant repairs a landlord-side defect and seeks reimbursement, potentially followed by conditional set-off.
- essential_slots: landlord repair duty; tenant notice; elapsed response period; repair; receipts; reimbursement demand; non-reimbursement; set-off condition.
- relations: REPAIR_COST_RECOVERY, REPAIR_OBLIGATION, SETOFF_RULE.
- do_not_confuse: the reverse route where the landlord repairs a tenant-side defect and charges the tenant.
- evidence_boundary: retain as a subtype for continuity with the historical inventory; do not use it as the parent concept.

### CONDITION_ACKNOWLEDGMENT
- kind: ASSERTION
- definition: a statement by a party about inspection, suitability, AS-IS condition, or limits on condition-related complaints.
- essential_slots: speaker; property/object; stated condition; scope; exceptions; linked defects/protocol.
- relations: DEFECTS_LIST, CONDITION_PROTOCOL, REPAIR_OBLIGATION, DAMAGE_RESPONSIBILITY.
- do_not_confuse: proved absence of defects; future repair allocation; validity of a waiver.
- evidence_boundary: read together with exceptions and repair duties; do not turn acknowledgment into factual proof of perfect condition.

### DEFECTS_LIST
- kind: DOCUMENT
- definition: a referenced list or appendix identifying defects or exceptions to a general condition statement.
- essential_slots: target document; purpose; availability; printed defects if supplied; relation to condition acknowledgment.
- relations: DOCUMENT_REFERENCE, CONDITION_ACKNOWLEDGMENT, REPAIR_OBLIGATION.
- do_not_confuse: property inventory; pre-return protocol; missing document with empty document.
- evidence_boundary: a reference does not establish the unseen list's contents.

### PROPERTY_INVENTORY
- kind: DOCUMENT
- definition: an inventory of furniture, fixtures, equipment, or other property linked to use, condition, custody, or return.
- essential_slots: document/reference; items; quantity; condition; source for each value; availability.
- relations: DOCUMENT_REFERENCE, CONTRACT_OBJECT, DAMAGE_RESPONSIBILITY, VACATING_OBLIGATION.
- do_not_confuse: defects list; tenant belongings; proof of handover from mere mention.
- evidence_boundary: blocked handwriting cannot supply items or quantities.

### CONDITION_PROTOCOL
- kind: DOCUMENT
- definition: an entry, handover, inspection, or pre-return protocol used to record property condition and possible corrective work.
- essential_slots: protocol type; timing; participants; availability; observations; correction route; relation to final handover.
- relations: DOCUMENT_REFERENCE, CONDITION_ACKNOWLEDGMENT, REPAIR_OBLIGATION, VACATING_OBLIGATION.
- do_not_confuse: inventory; defects appendix; proof that an inspection actually occurred.
- evidence_boundary: a contractual plan for a protocol does not establish that the protocol was created or signed.

### DAMAGE_RESPONSIBILITY
- kind: OBLIGATION
- definition: allocation of responsibility for a defined category of loss, damage, or third-party claim.
- essential_slots: responsible role; injured party/object; causal condition; scope; exclusions; amount/measure; evidence.
- relations: REPAIR_OBLIGATION, PROPERTY_INVENTORY, SECURITY_REALIZATION, INSURANCE_ROUTE.
- do_not_confuse: ordinary wear; repair duty; utility charge; nominal security amount.
- evidence_boundary: keep damage to third parties, tenant property, and leased property separate unless the contract links them.

## 9. M05 — Use, occupancy, alterations, and access

### USE_OCCUPANCY_RULE
- kind: CONDITION
- definition: a rule permitting, prohibiting, or conditioning how the dwelling may be used, who may reside there, or what conduct is allowed in the property or common areas.
- essential_slots: actor/occupant; use or conduct; permission/prohibition; consent; named occupants; guests/pets/business/common-area scope; exceptions; special condition.
- relations: PARTY_ROLE, CONTRACT_OBJECT, TRANSFER_RESTRICTION, CONTRACT_NOTICE.
- do_not_confuse: ordinary occupancy with assignment/subletting; conduct restrictions with damage liability; a specific agreed occupant with an unauthorized transferee.
- evidence_boundary: a specific occupancy clause may narrow a general restriction; do not classify residence, guests, pets, or conduct as a transfer without textual support.

### ALTERATION_PERMISSION
- kind: PERMISSION
- definition: a rule allowing, prohibiting, or conditioning physical changes, installations, drilling, painting, or other alterations.
- essential_slots: actor; alteration type; consent; form of consent; limits; restoration consequence.
- relations: IMPROVEMENT_DISPOSITION, DAMAGE_RESPONSIBILITY, VACATING_OBLIGATION.
- do_not_confuse: repair work; ordinary maintenance; ownership of the resulting improvement.
- evidence_boundary: permission to alter does not imply reimbursement or ownership rights.

### IMPROVEMENT_DISPOSITION
- kind: RELATION
- definition: the contract's rule for ownership, removal, restoration, or leaving in place an alteration or improvement.
- essential_slots: improvement; maker; owner/beneficiary claimed; removal/restoration duty; handover event; compensation if stated.
- relations: ALTERATION_PERMISSION, VACATING_OBLIGATION.
- do_not_confuse: permission to make the change; repair obligation; automatic reimbursement.
- evidence_boundary: a rule that an improvement remains does not prove consent to create it.

### ACCESS_PERMISSION
- kind: PERMISSION
- definition: a right or permission for a landlord/representative to enter for specified purposes and under stated coordination, timing, or notice conditions.
- essential_slots: entrant; purpose; time; coordination; notice; emergency/special exception.
- relations: CONTRACT_NOTICE, REPAIR_OBLIGATION.
- do_not_confuse: unlimited access; transfer of possession; physical eviction.
- evidence_boundary: preserve the exact strength of wording such as "coordinate", "with consent", or "where possible".

## 10. M06 — Transfer, substitution, and early exit

### TRANSFER_RESTRICTION
- kind: CONDITION
- definition: a restriction on assignment, subletting, transfer of contractual rights, transfer of possession, or another act that changes who holds or exercises the tenant-side position.
- essential_slots: actor; prohibited/conditioned transfer; target person; consent; exception; special replacement route.
- relations: REPLACEMENT_TENANT_ROUTE, USE_OCCUPANCY_RULE, CONTRACT_NOTICE.
- do_not_confuse: guest/occupant permission; ordinary residence/use; a specific replacement route; landlord-side transfer.
- evidence_boundary: a general restriction does not erase a more specific permitted replacement route, and an occupancy rule does not automatically become an assignment rule.

### LANDLORD_TRANSFER_RULE
- kind: PROCEDURE
- definition: a contractual route describing sale, assignment, or other transfer by the landlord/granting side and the stated effect on the tenancy.
- essential_slots: transferring role; transfer/sale event; successor role; notice; continuity of tenant rights/duties; termination branch if stated; handover of payments/security/documents if stated.
- relations: CONTRACT_NOTICE, TERMINATION_ROUTE, LETTING_ENTITLEMENT_CLAIM, DOCUMENT_REFERENCE.
- do_not_confuse: tenant transfer restriction; no-cause termination; verified completion or legal effect of a sale.
- evidence_boundary: a sale/transfer clause does not prove that a transfer occurred, who acquired title, or what external law does beyond the printed contractual rule.

### EARLY_DEPARTURE_PAYMENT
- kind: OBLIGATION
- definition: a rule that rent or another defined payment continues after physical departure until a stated release event or end date.
- essential_slots: departing role; payment; start; release/end event; exceptions; replacement/reletting relation.
- relations: RENT_OBLIGATION, REPLACEMENT_TENANT_ROUTE, RELETTING_REFUND.
- do_not_confuse: holdover; ordinary rent before departure; proven termination.
- evidence_boundary: moving out does not itself prove release from future payment.

### REPLACEMENT_TENANT_ROUTE
- kind: PROCEDURE
- definition: a special route in which a proposed replacement may assume tenancy obligations subject to notice, criteria, acceptance, execution, and release events.
- essential_slots: proposing party; candidate; notice; acceptance standard; approving actor; new term/price; security; execution; old tenant release.
- relations: TRANSFER_RESTRICTION, EARLY_DEPARTURE_PAYMENT, CONTRACT_NOTICE, SECURITY_CHECK.
- do_not_confuse: nomination with acceptance; acceptance with executed substitution; replacement tenant with guest/subtenant.
- evidence_boundary: a candidate proposal alone does not prove release.

### RELETTING_REFUND
- kind: MONETARY_EFFECT
- definition: a rule returning or crediting some rent for a period in which the property is relet while the original tenant had already paid or remained liable.
- essential_slots: original payment; reletting event; overlap period; refund percentage/formula; payor; recipient; conditions.
- relations: EARLY_DEPARTURE_PAYMENT, RENT_OBLIGATION.
- do_not_confuse: replacement-tenant release; full rent refund; security return.
- evidence_boundary: actual reletting and overlapping payments must be established before calculating a refund.

## 11. M07 — Security and performance assurance

### SECURITY_CHECK
- kind: INSTRUMENT
- definition: a cheque identified by the contract as security for specified obligations.
- essential_slots: instrument instance/count; amount/cap; cap scope; payee; custodian; secured obligations; delivery; blank-completion authority.
- relations: SECURITY_REALIZATION, SECURITY_RETURN, payment/charge concepts.
- do_not_confuse: rent cheque; utility payment cheque; promissory note; guarantee; cash deposit.
- evidence_boundary: contract wording about a cheque does not prove actual delivery, filled fields, or realization.

### PROMISSORY_NOTE
- kind: INSTRUMENT
- definition: a promissory note separately identified as a security instrument.
- essential_slots: instrument instance; amount/cap; secured obligations; guarantor relation; separate document; issuance status.
- relations: PERSONAL_GUARANTEE, SECURITY_REALIZATION, SECURITY_RETURN.
- do_not_confuse: security cheque; guarantee; deposit.
- evidence_boundary: listing the note does not prove that it was executed or delivered.

### PERSONAL_GUARANTEE
- kind: INSTRUMENT
- definition: a personal guarantor undertaking tied to a stated obligation or instrument.
- essential_slots: guarantor role/count; target obligation/instrument; separate document; execution status.
- relations: PROMISSORY_NOTE, SECURITY_CHECK.
- do_not_confuse: tenant; cheque drawer; institutional guarantor.
- evidence_boundary: a printed guarantor requirement does not prove signatures or completed guarantee documents.

### INSTITUTIONAL_GUARANTEE
- kind: INSTRUMENT
- definition: a guarantee identified as being issued by a bank or another institutional guarantee provider; the provider's exact class, licensing, and any applicable legal overlay are established separately.
- essential_slots: instrument instance; issuer; issuer class/license if relevant; amount; tenant financial outlay; secured obligations; validity/realization/release terms.
- relations: SECURITY_REALIZATION, SECURITY_RETURN, EXTERNAL_VALUE_LINKAGE when amount changes by formula.
- do_not_confuse: personal guarantee; security cheque; promissory note.
- evidence_boundary: the instrument type does not prove issuer licensing, statutory cap applicability, issuance, or realization.

### SECURITY_REALIZATION
- kind: PROCEDURE
- definition: a contractual route for using a specific security instrument after a stated trigger.
- essential_slots: target instrument; initiator; trigger/debt; claimed amount; notice; cure; method; collection costs.
- relations: security instruments; BREACH_TRIGGER; CONTRACT_NOTICE.
- do_not_confuse: authority to fill blanks; bank processing; proven debt; separate damages.
- evidence_boundary: contractual authorization does not prove actual realization or its legal validity.

### SECURITY_RETURN
- kind: PROCEDURE
- definition: a route for returning, cancelling, or releasing a particular security instrument after a stated event and prerequisites.
- essential_slots: target instrument; returning party; recipient; trigger; deadline; settlement/proof conditions; extension effect.
- relations: security instruments; LEASE_EXTENSION; VACATING_OBLIGATION.
- do_not_confuse: issue/delivery deadline; instrument validity period; actual historical return.
- evidence_boundary: a return rule for one instrument does not migrate to adjacent instruments.

## 12. M08 — Breach, cure, and termination

### BREACH_TRIGGER
- kind: CONDITION
- definition: a defined event or non-performance that the contract classifies as breach or attaches breach consequences to.
- essential_slots: obligation; triggering event; threshold; classification; exception; linked remedy.
- relations: BREACH_TERMINATION, TERMINATION_ROUTE, SECURITY_REALIZATION, monetary effects.
- do_not_confuse: cure period; notice-delivery delay; automatic physical eviction.
- evidence_boundary: a broad breach label does not establish that every remedy applies identically to every breach.

### TERMINATION_ROUTE
- kind: PROCEDURE
- definition: a route by which the contract purports to end the tenancy after a stated trigger, notice, condition, or contractual right.
- essential_slots: initiating role; trigger/type; notice; cure/prerequisite; effective event/date; resulting duties.
- relations: BREACH_TERMINATION, CONTRACT_NOTICE, VACATING_OBLIGATION.
- do_not_confuse: physical departure; end of fixed term; lawful eviction procedure.
- evidence_boundary: reconstruct the contractual route first; external-law validity and enforcement are separate.

### BREACH_TERMINATION
- kind: PROCEDURE
- definition: specialization of TERMINATION_ROUTE where the stated trigger is breach or non-performance.
- essential_slots: breach trigger; initiating role; notice; cure; effective termination event; linked monetary/vacating consequences.
- relations: BREACH_TRIGGER, TERMINATION_ROUTE, VACATING_OBLIGATION.
- do_not_confuse: no-cause/convenience route; breach classification with actual termination.
- evidence_boundary: a right to terminate does not prove that termination was exercised.

## 13. M09 — End of tenancy, return, and holdover

### VACATING_OBLIGATION
- kind: OBLIGATION
- definition: a duty to return possession and any linked property at the end of the relevant route or period.
- essential_slots: obligated role; trigger/date; possession; keys/items; condition; utilities/receipts; protocol; restoration.
- relations: LEASE_TERM, TERMINATION_ROUTE, CONDITION_PROTOCOL, SECURITY_RETURN.
- do_not_confuse: early departure; holdover compensation; physical eviction.
- evidence_boundary: a contractual duty to vacate does not itself establish lawful self-help or enforcement procedure.

### LEFT_BEHIND_PROPERTY_RULE
- kind: PROCEDURE
- definition: a contractual rule addressing tenant-owned property or belongings remaining in the dwelling after a return, termination, or vacating event.
- essential_slots: property category; triggering event; notice; storage/removal/disposal claim; retrieval opportunity; stated costs; relation to possession handover.
- relations: VACATING_OBLIGATION, DAMAGE_RESPONSIBILITY, EVIDENCE_PRODUCTION_OBLIGATION.
- do_not_confuse: landlord-owned inventory; proof of abandonment; the landlord's right to physical eviction.
- evidence_boundary: the clause does not prove that property was actually left behind or that any stated disposal route is legally effective.

### HOLDOVER_COMPENSATION
- kind: MONETARY_EFFECT
- definition: a payment or compensation formula triggered by failure to return possession after the relevant end point.
- essential_slots: trigger; amount/formula; accrual unit; start/end; payer; recipient; relation to continuing charges.
- relations: VACATING_OBLIGATION, RENT_OBLIGATION, other M12 monetary effects.
- do_not_confuse: ordinary rent; early-departure liability; two separate charges merely because wording repeats a daily amount.
- evidence_boundary: actual holdover chronology must be established before calculation.

## 14. M10 — Insurance and liability

### INSURANCE_ROUTE
- kind: PROCEDURE
- definition: a conditional route for presenting, procuring, or replacing insurance and allocating consequences depending on which branch occurs.
- essential_slots: actor; option/duty; deadline; fallback trigger; policy holder; insured risk; recourse/subrogation rule; proof.
- relations: DAMAGE_RESPONSIBILITY, CONTRACT_NOTICE.
- do_not_confuse: optional presentation with unconditional tenant duty; policy existence with contractual requirement.
- evidence_boundary: a fallback branch applies only when its trigger occurs; do not transfer recourse language to another branch.

## 15. M11 — Notices, evidence, and procedural connectors

### SERVICE_ACCOUNT_REGISTRATION
- kind: OBLIGATION
- definition: a duty to register, transfer, update, or close a municipal, utility, building, or other service account/status in connection with the tenancy.
- essential_slots: obligated actor; authority/provider; service/account; required action; trigger; deadline; proof/receipt; end-of-term reversal if stated.
- relations: OCCUPANCY_CHARGE, CONTRACT_NOTICE, EVIDENCE_PRODUCTION_OBLIGATION, VACATING_OBLIGATION.
- do_not_confuse: paying the underlying charge; merely notifying the landlord; proof that registration actually occurred.
- evidence_boundary: a registration duty and its deadline do not establish performance, the account holder shown by the external provider, or a breach without the relevant chronology.

### EVIDENCE_PRODUCTION_OBLIGATION
- kind: OBLIGATION
- definition: a duty to retain, obtain, show, or deliver documentary evidence such as receipts, payment confirmations, no-debt confirmations, policies, consents, or inspection records.
- essential_slots: obligated actor; evidence type; event/claim it supports; recipient; trigger; deadline; form; stated consequence.
- relations: OCCUPANCY_CHARGE, SECURITY_RETURN, INSURANCE_ROUTE, CONDITION_PROTOCOL, CONTRACT_NOTICE.
- do_not_confuse: the duty to provide evidence with proof that the underlying event occurred; a notice with the document that proves compliance.
- evidence_boundary: a requirement to produce a receipt or confirmation does not prove that the document exists, was delivered, or is substantively correct.

### CONTRACT_NOTICE
- kind: PROCEDURE
- definition: a contractually relevant communication about a specified action or event between identified actors or an external body.
- essential_slots: sender; recipient; subject; form; channel; sending deadline; deemed-receipt rule; proof.
- relations: renewal, replacement, repair, breach, termination, payment, registration, and security concepts.
- do_not_confuse: cure period; breach threshold; actual receipt.
- evidence_boundary: a deemed-receipt rule does not prove that a notice was sent.

## 16. M12 — Monetary remedies, sanctions, set-off, and overlap

### EXTERNAL_FINANCIAL_FRAMEWORK
- kind: EXTERNAL_DEPENDENCY
- definition: a contractual reference to an external financial or religious-finance framework that purports to qualify, structure, or explain an interest/payment arrangement beyond the numeric formula printed in the immediate clause.
- essential_slots: target payment/interest rule; named framework/source; incorporated text availability; contractual effect claimed; external verification status.
- relations: LATE_PAYMENT_INTEREST, DOCUMENT_REFERENCE, EXTERNAL_VALUE_LINKAGE.
- do_not_confuse: a numeric index or exchange rate; a fixed contractual interest rate; proof that the framework validates the payment term.
- evidence_boundary: preserve the reference as part of the contract while leaving the framework's legal/economic effect unresolved until its external source is separately verified.

### LATE_PAYMENT_INTEREST
- kind: MONETARY_EFFECT
- definition: interest or a comparable finance charge tied to delayed payment.
- essential_slots: overdue principal; trigger; rate/formula; accrual period; compounding/index linkage if stated.
- relations: RENT_OBLIGATION, OCCUPANCY_CHARGE, EXTERNAL_VALUE_LINKAGE, BREACH_TRIGGER.
- do_not_confuse: principal debt; breach compensation; holdover compensation.
- evidence_boundary: the clause establishes a formula, not the actual accrued amount without chronology and values.

### BREACH_CANCELLATION_COMPENSATION
- kind: MONETARY_EFFECT
- definition: a separate amount triggered by cancellation/termination following a specified breach.
- essential_slots: debtor; recipient; termination/breach trigger; amount/formula; accrual event; stated purpose.
- relations: BREACH_TRIGGER, BREACH_TERMINATION, other monetary effects.
- do_not_confuse: unpaid rent; late interest; holdover; security realization.
- evidence_boundary: multiple monetary clauses do not prove automatic cumulative recovery.

### SETOFF_RULE
- kind: CONDITION
- definition: a rule permitting, prohibiting, or conditioning deduction of one claim from another contractual payment.
- essential_slots: actor; claim being set off; target obligation; permission/prohibition; prerequisites; sequence; exceptions.
- relations: REPAIR_COST_RECOVERY, RENT_OBLIGATION, monetary effects.
- do_not_confuse: reimbursement right with automatic set-off; broad prohibition with legal validity.
- evidence_boundary: record the contractual rule first; statutory effect belongs to a separate verified layer.

## 17. M13 — Dispute forum and adjudication

### DISPUTE_FORUM
- kind: RELATION
- definition: a contractual relation that directs or refers future disputes to a court, arbitration, Beit Din, tribunal, or other forum.
- essential_slots: forum type; forum identity if readable; covered parties/issues; mandatory/permissive wording; exclusivity claim; incorporated rules/document.
- relations: DOCUMENT_REFERENCE, EXTERNAL_PROCEEDING_REFERENCE, CONTRACT_NOTICE.
- do_not_confuse: named forum with verified jurisdiction; forum clause with breach/termination clause.
- evidence_boundary: the forum relation is a contract fact; validity, jurisdiction, exclusivity, waiver, procedural effect, and the forum's external rules remain separate. Handwritten forum identity remains blocked.

## 18. Temporal roles

Temporal roles are not standalone mechanisms. They attach a time value to a specific actor, action, trigger, target instance, and source.

A temporal extraction should preserve:

~~~text
actor
-> action
-> trigger / reference event
-> value + unit
-> direction of counting
-> target concept / instance
-> source
-> consequence if explicitly stated
~~~

Current reusable roles:

| Temporal role | Meaning | Common parent concepts |
| --- | --- | --- |
| PAYMENT_DUE_DATE | when a specified payment is due | RENT_OBLIGATION, OCCUPANCY_CHARGE |
| OPTION_EXERCISE_DEADLINE | lead time/deadline for exercising an extension route | LEASE_EXTENSION, CONTRACT_NOTICE |
| EXIT_NOTICE_LEAD_TIME | notice period before an early-exit/replacement/termination event | REPLACEMENT_TENANT_ROUTE, TERMINATION_ROUTE |
| NOTICE_DEEMED_RECEIPT_DELAY | contractual delay before a sent notice is treated as received | CONTRACT_NOTICE |
| REPAIR_RESPONSE_PERIOD | response period after a repair request | REPAIR_OBLIGATION |
| URGENT_REPAIR_RESPONSE_PERIOD | shorter response period for an urgent repair branch | REPAIR_OBLIGATION, REPAIR_COST_RECOVERY |
| SECURITY_DELIVERY_DEADLINE | deadline to provide a security instrument | security instruments |
| SECURITY_RETURN_DEADLINE | deadline to return/release a target security after its trigger | SECURITY_RETURN |
| LATE_PAYMENT_BREACH_THRESHOLD | delay/threshold that changes the contractual classification of non-payment | BREACH_TRIGGER |
| CURE_PERIOD | period to correct a specified breach after the stated triggering notice/event | BREACH_TRIGGER, BREACH_TERMINATION |

### Temporal boundaries

- the same number of days does not make two periods equivalent;
- a deemed-receipt delay is not a cure period;
- a late-payment breach threshold is not automatically a cure period;
- a security-delivery deadline is not a pre-realization notice period;
- calendar duration and a money cap expressed as "N months of rent" have different semantic dimensions.

## 19. Legacy and specialization decisions

#### TENANT_REPAIR_RECOVERY

Retained for continuity with the historical inventory, but treated as a specialization of REPAIR_COST_RECOVERY.

The generalized parent is required because the reviewed corpus contains both directions:

~~~text
tenant repairs landlord-side defect
-> possible recovery from landlord

landlord repairs tenant-side defect
-> possible recovery from tenant
~~~

The roles must reverse with the source obligation; they must not be copied from one branch to the other.

#### INSTITUTIONAL_GUARANTEE

Included as a concrete security-instrument concept because the maintained SECURITY cards and dated statutory overlay now distinguish institutional guarantees from personal guarantees, cheques, and promissory notes.

This does not create a new Router family: routing remains SECURITY.

### Historical inventory status

The old 30-concept document remains a dated research snapshot. This lexicon supersedes it only as the current teaching glossary; it does not rewrite the historical source record.

## 20. Concepts deliberately not promoted to the core lexicon

The following remain outside the compact core until source coverage or teaching value justifies separate concepts:

- CASH_DEPOSIT: known generic security form but not sufficiently evidenced in the reviewed contract corpus for a dedicated current card;
- separate BANK_GUARANTEE: represented for now by INSTITUTIONAL_GUARANTEE plus issuer class rather than a parallel top-level concept;
- POST_TERM_VALIDITY: insufficient source support as a distinct contract concept;
- standalone pre-return timing concept: represented by CONDITION_PROTOCOL plus temporal attributes rather than another top-level concept;
- separate pet/guest/business/noise/cleanliness concept IDs: represented as subtypes/slots of USE_OCCUPANCY_RULE until evidence shows a reconstruction-relevant boundary;
- separate sale-notice concept: represented within LANDLORD_TRANSFER_RULE plus CONTRACT_NOTICE rather than duplicating the same route.

Not promoting a term does not mean ignoring the clause. Unmatched material stays visible for OTHER/novel-issue review.

## 21. Retrieval guidance

The Concept Lexicon is a semantic vocabulary, not a flat prompt appendix.

Recommended use:

~~~text
Router families
-> select likely Mechanism Map sections
-> select concept slice
-> retrieve detailed cards/examples only for those concepts
~~~

Examples:

~~~text
SECURITY
-> M07
-> SECURITY_CHECK / PROMISSORY_NOTE / PERSONAL_GUARANTEE /
   INSTITUTIONAL_GUARANTEE / SECURITY_REALIZATION / SECURITY_RETURN

REPAIR + PROPERTY_CONDITION
-> M04
-> REPAIR_OBLIGATION / REPAIR_COST_RECOVERY /
   CONDITION_ACKNOWLEDGMENT / DEFECTS_LIST /
   PROPERTY_INVENTORY / CONDITION_PROTOCOL

EARLY_EXIT + TRANSFER
-> M06
-> EARLY_DEPARTURE_PAYMENT / REPLACEMENT_TENANT_ROUTE /
   RELETTING_REFUND / TRANSFER_RESTRICTION

BREACH + NOTICE + OTHER_PAYMENT
-> M08 + M11 + M12
-> BREACH_TRIGGER / TERMINATION_ROUTE / BREACH_TERMINATION /
   CONTRACT_NOTICE / EVIDENCE_PRODUCTION_OBLIGATION /
   LATE_PAYMENT_INTEREST / BREACH_CANCELLATION_COMPENSATION /
   SETOFF_RULE / EXTERNAL_FINANCIAL_FRAMEWORK

ACCESS + TRANSFER + EARLY_EXIT
-> M05 + M06
-> USE_OCCUPANCY_RULE / ACCESS_PERMISSION /
   TRANSFER_RESTRICTION / LANDLORD_TRANSFER_RULE /
   EARLY_DEPARTURE_PAYMENT / REPLACEMENT_TENANT_ROUTE

NOTICE + OTHER
-> M00 + M11
-> CONTRACT_DEFINITION / DOCUMENT_REFERENCE /
   SERVICE_ACCOUNT_REGISTRATION / EVIDENCE_PRODUCTION_OBLIGATION /
   CONTRACT_NOTICE
~~~

A concept slice may cross Mechanism Map boundaries when the contract itself creates a cross-clause dependency.

## 22. Completeness and expansion rule

Against the currently reviewed sanitized/printed corpus and the structural requirements of Foundation Core / Mechanism Map v0.2, this v0.3 lexicon gives an explicit teaching concept or parent concept to the material distinctions identified in the second-pass audit.

This is not universal completeness.

When a new contract exposes a materially different concept:

1. preserve the clause under existing Router families or OTHER;
2. identify which existing concept almost fits and exactly where it fails;
3. determine whether the difference is a new concept, subtype, relation, slot, temporal role, or merely a new lexical form;
4. add a new top-level concept only when the distinction changes how the mechanism must be reconstructed;
5. keep source provenance and observed-model-error evidence separate from the concept definition.

Ontology growth should follow semantic necessity, not vocabulary count.
