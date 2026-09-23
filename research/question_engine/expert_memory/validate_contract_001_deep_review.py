"""Offline provenance gate for assistant's first contract_001 review (not legal Gold)."""

from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
DATA = Path(__file__).with_name("contract_001_deep_review_v1.json")
GOLD = ROOT / "research/question_engine/golden_contracts/contract_001_he.txt"
META = ROOT / "research/question_engine/golden_contracts/contract_001.meta.json"
SPLIT = Path(__file__).with_name("real_contract_template_split_v1.json")
IDS = {
    "term_payment_option_security_return",
    "security_cheque_not_bank_guarantee",
    "late_payment_indexation_termination_notice",
    "early_exit_transfer_and_remaining_rent",
    "repair_setoff_vs_default",
    "defects_as_is_appendix_and_lost_property",
    "moveout_condition_holdover_security",
    "individual_payer_collective_tenant",
    "alterations_drilling_and_ownership",
    "entry_coordination_qualifier",
    "tenant_goods_and_third_party_loss",
    "documents_notice_and_precedence",
}
ESSENTIAL = {
    "term_payment_option_security_return": {"3", "4", "8", "11", "17"},
    "security_cheque_not_bank_guarantee": {"4", "11"},
    "late_payment_indexation_termination_notice": {"4", "9", "19", "21"},
    "early_exit_transfer_and_remaining_rent": {"3", "7", "8"},
    "repair_setoff_vs_default": {"4", "9", "12"},
    "defects_as_is_appendix_and_lost_property": {"9", "12", "22"},
    "moveout_condition_holdover_security": {"9", "10", "11", "17"},
    "individual_payer_collective_tenant": {"4", "11", "24"},
    "alterations_drilling_and_ownership": {"9", "14", "16"},
    "entry_coordination_qualifier": {"15"},
    "tenant_goods_and_third_party_loss": {"9", "22"},
    "documents_notice_and_precedence": {"12", "21", "23"},
}
LIMITS = [
    "No handwriting or signature reconstruction",
    "No inference that Appendix B is absent from the original",
    "No assumption of live statutory enforceability or case outcome",
    "No inference that two-contract aggregate is a separate independent template",
    "Only materially relevant conditional questions are for the user; document questions precede them.",
]


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def read(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink()
            and path.stat().st_size < 60_000, "unsafe or oversized research JSON")
    def unique(pairs: list[tuple[str, object]]) -> dict:
        out: dict = {}
        for k, v in pairs:
            require(k not in out, "duplicate JSON key")
            out[k] = v
        return out
    data = json.loads(path.read_text(encoding="utf-8"),
                      object_pairs_hook=unique)
    require(isinstance(data, dict), "root must be a JSON object")
    return data


def clause_sections(text: str) -> dict[str, str]:
    marks = list(re.finditer(r"(?m)^(\d+)\.\s", text))
    return {m.group(1): text[m.start():marks[i + 1].start()
            if i + 1 < len(marks) else len(text)]
            for i, m in enumerate(marks)}


def validate(review: dict, printed_text: str,
             meta: dict, family_split: dict) -> None:
    require(set(review) == {"schema_version", "review_id", "source",
            "source_review", "scope", "private_original_link",
            "development_cohort", "mechanisms", "scope_limits", "state"}
            and review["schema_version"] == 1
            and review["review_id"] == "contract_001_deep_review_v1"
            and review["source"] ==
            "research/question_engine/golden_contracts/contract_001_he.txt"
            and review["source_review"] ==
            "ASSISTANT_VISUAL_TRANSCRIPTION_OWNER_NOT_SIGNED_OFF"
            and review["scope"] ==
            "OFFLINE_SANITIZED_PRINTED_TEXT_ONLY_NOT_LEGAL_GOLD"
            and review["private_original_link"] == "UNKNOWN_EXCEPT_RC07_EXCLUDED"
            and review["development_cohort"] ==
            "BLOCKED_PENDING_PRIVATE_FAMILY_LINKAGE"
            and review["state"] ==
            "FIRST_INDEPENDENT_ASSISTANT_PASS_OWNER_REVIEW_PENDING",
            "unverified review promoted or provenance changed")
    require(meta["fixture_id"] == "contract_001"
            and meta["pii_removed"] is True
            and "product-owner text-level review not yet recorded"
            in meta["review_status"], "source review status mismatch")
    require(family_split["golden_fixture"]["linked_family"] == "UNKNOWN"
            and family_split["golden_fixture"]["training_eligibility"] ==
            "BLOCKED_PENDING_PRIVATE_FAMILY_LINKAGE",
            "private source cohort must remain blocked")
    require(review["scope_limits"] == LIMITS, "missing evidence boundary")
    sections = clause_sections(printed_text)
    require(set(sections) == {str(i) for i in range(1, 25)},
            "expected exactly 24 printed clauses in the sanitized fixture")
    items = review["mechanisms"]
    require(isinstance(items, list) and len(items) == len(IDS)
            and {x.get("id") for x in items} == IDS,
            "missing or duplicate human-style mechanism")
    total_quotes = 0
    for x in items:
        require(set(x) == {"id", "clauses", "quotes", "first_read",
                "second_pass", "status", "gaps", "avoid", "ask_document",
                "ask_user", "signal"}, "unexpected mechanism fields")
        cls = x["clauses"]
        require(isinstance(cls, list) and len(cls) == len(set(cls))
                and ESSENTIAL[x["id"]] <= set(cls)
                and set(cls) <= set(sections),
                "invalid clause links in mechanism")
        require(x["signal"] in {"MAIN", "CONDITIONAL"}
                and x["status"].startswith((
                    "UNRESOLVED_", "CONFIRMED_", "NARROWED_")),
                "unreviewed verdict or risk rating")
        for key in ("first_read", "second_pass", "avoid"):
            require(isinstance(x[key], str) and len(x[key]) >= 45,
                    "missing independent reasoning or counter-check")
        for key in ("gaps", "ask_document", "ask_user"):
            require(isinstance(x[key], list) and all(
                isinstance(v, str) and v.strip() for v in x[key]),
                "invalid unknowns or discussion questions")
        require(len(x["gaps"]) >= 1, "lack of explicit uncertainty")
        quotes = x["quotes"]
        require(isinstance(quotes, list) and len(quotes) >= 2,
                "insufficient direct evidence")
        for q in quotes:
            require(set(q) == {"clause", "quote"}
                    and q["clause"] in cls and 4 <= len(q["quote"]) <= 140
                    and q["quote"] in sections[q["clause"]],
                    "fabricated or misattributed Hebrew source quote")
        total_quotes += len(quotes)
    require(total_quotes >= 40, "evidence coverage unexpectedly reduced")


if __name__ == "__main__":
    validate(read(DATA), GOLD.read_text(encoding="utf-8"),
             read(META), read(SPLIT))
    print("Deep contract_001: 12 source-anchored mechanisms verified; "
          "assistant first pass, not reviewed Gold.")
