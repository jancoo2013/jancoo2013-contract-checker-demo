"""First bounded deterministic Question Engine inventory for economic/security facts."""

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


__all__ = ("ECONOMIC_CORE_INVENTORY_V1",)
