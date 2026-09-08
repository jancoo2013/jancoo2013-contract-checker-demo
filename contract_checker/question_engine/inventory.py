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


__all__ = ("EARLY_EXIT_CORE_INVENTORY_V1", "ECONOMIC_CORE_INVENTORY_V1")
