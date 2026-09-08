"""Bounded deterministic Question Engine inventories for recurring contract facts."""

from __future__ import annotations

from .schema import QuestionInventory, QuestionSpec


ECONOMIC_CORE_INVENTORY_V1 = QuestionInventory(
    schema_version=1,
    questions=(
        QuestionSpec(
            question_id="economic.monthly_rent",
            domain="economic",
            purpose="Identify the stated recurring monthly rent used as the economic baseline.",
            answer_fields=("amount", "currency", "payment_frequency"),
        ),
        QuestionSpec(
            question_id="security.instrument_inventory",
            domain="security",
            purpose="Identify every distinct security or payment instrument required by the contract.",
            answer_fields=("instrument_types", "instrument_count"),
        ),
        QuestionSpec(
            question_id="security.instrument_relationship",
            domain="security",
            purpose="Determine whether listed security instruments are cumulative, alternative, or mixed.",
            answer_fields=("simultaneous_instruments", "alternative_instruments"),
        ),
        QuestionSpec(
            question_id="security.instrument_amounts",
            domain="security",
            purpose="Identify the stated amount of each security instrument without collapsing instrument types.",
            answer_fields=("instrument_amounts", "currency"),
        ),
        QuestionSpec(
            question_id="security.instrument_blanks",
            domain="security",
            purpose="Identify security instruments whose date, amount, or payee is blank in the contract material.",
            answer_fields=(
                "blank_date_instruments",
                "blank_amount_instruments",
                "blank_payee_instruments",
            ),
        ),
        QuestionSpec(
            question_id="security.instrument_control",
            domain="security",
            purpose="Identify named payees and any printed transfer or endorsement restrictions for security instruments.",
            answer_fields=("instrument_payees", "transfer_restrictions"),
        ),
        QuestionSpec(
            question_id="security.completion_authority",
            domain="security",
            purpose="Identify any printed authority to complete missing particulars of a security instrument.",
            answer_fields=(
                "completion_authority_role",
                "completable_fields",
                "affected_instruments",
            ),
        ),
        QuestionSpec(
            question_id="security.instrument_linkage",
            domain="security",
            purpose="Identify which obligations, periods, and separately referenced documents each security instrument is tied to.",
            answer_fields=(
                "linked_obligations",
                "linked_periods",
                "separate_document_reference",
                "separate_document_present",
            ),
        ),
        QuestionSpec(
            question_id="security.realization_chain",
            domain="security",
            purpose="Extract the contractual realization chain from trigger through amount, notice, and opportunity to cure.",
            answer_fields=(
                "realization_grounds",
                "amount_basis",
                "notice_required",
                "notice_period",
                "cure_available",
                "cure_period",
            ),
        ),
        QuestionSpec(
            question_id="security.recovery_overlap",
            domain="security",
            purpose="Identify whether multiple payment or security mechanisms can address the same underlying obligation and how the contract relates them.",
            answer_fields=(
                "overlapping_instruments",
                "overlap_obligation",
                "interaction_rule",
            ),
        ),
        QuestionSpec(
            question_id="security.option_continuity",
            domain="security",
            purpose="Identify what happens to security instruments and guarantor coverage when an option or renewal is exercised.",
            answer_fields=(
                "option_security_continuity",
                "renewal_action_required",
                "renewal_deadline",
            ),
        ),
        QuestionSpec(
            question_id="security.return_mechanics",
            domain="security",
            purpose="Identify the contractual trigger and deadline for returning security after the tenancy ends.",
            answer_fields=("return_trigger", "return_deadline"),
        ),
        QuestionSpec(
            question_id="security.guarantor_scope",
            domain="security",
            purpose="Identify the stated count, amount, duration, and period coverage of guarantor obligations when present.",
            answer_fields=(
                "guarantor_required",
                "guarantor_count",
                "guarantee_amount",
                "guarantee_duration",
            ),
        ),
    ),
)


EARLY_EXIT_CORE_INVENTORY_V1 = QuestionInventory(
    schema_version=1,
    questions=(
        QuestionSpec(
            question_id="early_exit.continuing_liability",
            domain="early_exit",
            purpose="Identify whether rent or other recurring obligations continue after the tenant leaves before the contractual end date.",
            answer_fields=(
                "continuing_rent_liability",
                "liability_end_trigger",
                "prepaid_rent_refund_rule",
            ),
        ),
        QuestionSpec(
            question_id="early_exit.replacement_route",
            domain="early_exit",
            purpose="Identify any contractual route for ending or reducing continuing liability by providing a replacement tenant.",
            answer_fields=(
                "replacement_route_present",
                "replacement_candidate_requirements",
                "replacement_route_effect",
            ),
        ),
        QuestionSpec(
            question_id="early_exit.approval_standard",
            domain="early_exit",
            purpose="Identify whether landlord approval is required for a replacement tenant and the contractual standard governing that approval or refusal.",
            answer_fields=(
                "landlord_approval_required",
                "approval_standard",
                "stated_refusal_grounds",
            ),
        ),
        QuestionSpec(
            question_id="early_exit.assignment_subletting_interaction",
            domain="early_exit",
            purpose="Identify how assignment and subletting restrictions interact with any replacement-tenant or early-exit route.",
            answer_fields=(
                "assignment_allowed",
                "subletting_allowed",
                "consent_required",
                "replacement_exception_present",
            ),
        ),
        QuestionSpec(
            question_id="early_exit.release_consequences",
            domain="early_exit",
            purpose="Identify the contractual event that releases the departing tenant from future obligations and any stated financial consequence attached to the early-exit route.",
            answer_fields=(
                "release_trigger",
                "future_rent_release",
                "additional_payment_rule",
            ),
        ),
    ),
)


FINANCIAL_SANCTIONS_CORE_INVENTORY_V1 = QuestionInventory(
    schema_version=1,
    questions=(
        QuestionSpec(
            question_id="financial_sanctions.late_payment",
            domain="financial_sanctions",
            purpose="Identify monetary additions triggered by late payment while keeping the underlying principal obligation separate.",
            answer_fields=(
                "late_payment_trigger",
                "principal_reference",
                "interest_rate",
                "interest_period",
                "partial_period_rule",
                "indexation_formula",
                "accrual_start",
                "accrual_end",
            ),
        ),
        QuestionSpec(
            question_id="financial_sanctions.holdover_compensation",
            domain="financial_sanctions",
            purpose="Identify any monetary compensation or penalty tied to remaining in the property after the contractual return date.",
            answer_fields=(
                "holdover_trigger",
                "holdover_amount",
                "holdover_formula",
                "accrual_unit",
                "accrual_start",
                "accrual_end",
            ),
        ),
        QuestionSpec(
            question_id="financial_sanctions.fixed_agreed_damages",
            domain="financial_sanctions",
            purpose="Identify any fixed agreed-damages amount or formula triggered by breach, cancellation, or another stated event.",
            answer_fields=(
                "agreed_damages_trigger",
                "agreed_damages_amount",
                "agreed_damages_formula",
                "stated_loss_head",
                "payment_timing",
            ),
        ),
        QuestionSpec(
            question_id="financial_sanctions.other_contractual_sanctions",
            domain="financial_sanctions",
            purpose="Identify other explicit contractual monetary sanctions not already captured as late-payment, holdover, or fixed agreed damages.",
            answer_fields=(
                "sanction_type",
                "sanction_trigger",
                "sanction_amount_formula",
                "sanction_start",
                "sanction_end",
                "stated_loss_head",
            ),
        ),
        QuestionSpec(
            question_id="financial_sanctions.overlap",
            domain="financial_sanctions",
            purpose="Identify whether two or more monetary mechanisms can apply to the same event or stated loss and how the contract relates them.",
            answer_fields=(
                "overlapping_mechanisms",
                "shared_trigger",
                "shared_loss_head",
                "cumulative_language",
                "interaction_rule",
            ),
        ),
    ),
)


CONDITION_DEFECTS_CORE_INVENTORY_V1 = QuestionInventory(
    schema_version=1,
    questions=(
        QuestionSpec(
            question_id="condition.entry_baseline",
            domain="condition_defects",
            purpose="Identify the contract's stated baseline condition of the dwelling and included items at entry.",
            answer_fields=(
                "entry_condition_statement",
                "cleanliness_statement",
                "fitness_statement",
                "inspection_acknowledged",
            ),
        ),
        QuestionSpec(
            question_id="condition.as_is_acknowledgment",
            domain="condition_defects",
            purpose="Identify AS-IS, inspection, acceptance, and defect-waiver wording together with any stated exceptions.",
            answer_fields=(
                "as_is_present",
                "inspection_acknowledged",
                "acceptance_statement",
                "waived_defect_categories",
                "waiver_exceptions",
            ),
        ),
        QuestionSpec(
            question_id="condition.pre_existing_defects",
            domain="condition_defects",
            purpose="Identify how known or pre-existing defects are recorded or excluded from the entry-condition acknowledgment.",
            answer_fields=(
                "known_defects_present",
                "known_defect_description_source",
                "defect_list_reference",
                "defect_list_present",
            ),
        ),
        QuestionSpec(
            question_id="condition.damage_allocation",
            domain="condition_defects",
            purpose="Identify the contractual boundary between tenant-caused damage and ordinary wear without treating them as the same condition category.",
            answer_fields=(
                "tenant_caused_damage_rule",
                "ordinary_wear_exception",
                "causation_standard",
                "repair_standard",
            ),
        ),
        QuestionSpec(
            question_id="condition.repair_mechanics",
            domain="condition_defects",
            purpose="Identify tenant and landlord repair responsibilities and the contract's notice, timing, self-help, reimbursement, or set-off mechanics.",
            answer_fields=(
                "tenant_repair_scope",
                "landlord_repair_scope",
                "notice_required",
                "repair_deadline",
                "tenant_self_help_available",
                "reimbursement_or_setoff_rule",
            ),
        ),
        QuestionSpec(
            question_id="condition.return_condition",
            domain="condition_defects",
            purpose="Identify the required condition at return, including cleaning, painting, restoration, and any ordinary-wear exception.",
            answer_fields=(
                "return_condition_standard",
                "cleaning_required",
                "painting_required",
                "restoration_required",
                "ordinary_wear_exception",
            ),
        ),
        QuestionSpec(
            question_id="condition.evidence_dependencies",
            domain="condition_defects",
            purpose="Identify referenced condition protocols, defect lists, inventories, or appendices and whether those referenced documents are present in the contract package.",
            answer_fields=(
                "condition_document_references",
                "defect_list_reference",
                "inventory_reference",
                "referenced_documents_present",
            ),
        ),
    ),
)


TERMINATION_CURE_CORE_INVENTORY_V1 = QuestionInventory(
    schema_version=1,
    questions=(
        QuestionSpec(
            question_id="termination.breach_triggers",
            domain="termination_cure",
            purpose="Identify contractual breach events that can activate termination-related remedies without collapsing them into one generic breach flag.",
            answer_fields=(
                "breach_events",
                "remedy_holders",
                "triggered_remedies",
            ),
        ),
        QuestionSpec(
            question_id="termination.fundamental_breach_definition",
            domain="termination_cure",
            purpose="Identify which breaches the contract expressly classifies as fundamental or material and any clause references used to define that category.",
            answer_fields=(
                "fundamental_breach_categories",
                "fundamental_breach_clause_references",
                "automatic_fundamental_breach_wording",
            ),
        ),
        QuestionSpec(
            question_id="termination.notice_cure",
            domain="termination_cure",
            purpose="Identify notice and cure mechanics that apply before or after a stated breach, including form, timing, and any stated exceptions.",
            answer_fields=(
                "notice_required",
                "notice_form",
                "notice_period",
                "cure_available",
                "cure_period",
                "cure_exceptions",
            ),
        ),
        QuestionSpec(
            question_id="termination.cancellation_mechanics",
            domain="termination_cure",
            purpose="Identify who may cancel the contract, the contractual trigger for cancellation, and when cancellation is stated to take effect.",
            answer_fields=(
                "cancellation_right_holder",
                "cancellation_trigger",
                "cancellation_notice_required",
                "cancellation_effective_point",
            ),
        ),
        QuestionSpec(
            question_id="termination.vacancy_demand",
            domain="termination_cure",
            purpose="Identify contractual wording allowing a demand to vacate, its trigger and deadline, while preserving any immediate-vacancy or self-help wording as contract text only.",
            answer_fields=(
                "vacancy_demand_available",
                "vacancy_trigger",
                "vacancy_deadline",
                "immediate_vacancy_wording",
                "self_help_or_physical_removal_wording",
            ),
        ),
        QuestionSpec(
            question_id="termination.cross_clause_interaction",
            domain="termination_cure",
            purpose="Map how breach classifications, notice/cure rules, cancellation rights, and vacancy demands interact across the contract and identify unresolved interaction ambiguity.",
            answer_fields=(
                "linked_breach_categories",
                "linked_notice_cure_rules",
                "linked_cancellation_rules",
                "linked_vacancy_rules",
                "interaction_ambiguity",
            ),
        ),
    ),
)


__all__ = (
    "CONDITION_DEFECTS_CORE_INVENTORY_V1",
    "EARLY_EXIT_CORE_INVENTORY_V1",
    "ECONOMIC_CORE_INVENTORY_V1",
    "FINANCIAL_SANCTIONS_CORE_INVENTORY_V1",
    "TERMINATION_CURE_CORE_INVENTORY_V1",
)
