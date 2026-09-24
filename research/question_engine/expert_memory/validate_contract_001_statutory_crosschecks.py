"""Offline schema/provenance gate for three unreviewed legal crosschecks."""

from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).parent
DATA = BASE / "contract_001_statutory_crosschecks_v1.json"
GOLD = ROOT / "research/question_engine/golden_contracts/contract_001_he.txt"
OVERLAY = ROOT / "docs/statutory/ISRAEL_RENTAL_AND_LOAN_AMENDMENT_2026_V1.json"
EXPECTED = {
    "renewal_true_option_vs_new_consent": {
        "clauses": {"3", "4"}, "sources": {"law_2017"},
        "failures": {"AUTOFILL_60_DAYS_INTO_BLANK",
                     "LABEL_CONSENT_DEPENDENT_RENEWAL_AS_UNILATERAL_OPTION"},
    },
    "repair_urgent_exception_and_defect_waiver": {
        "clauses": {"4", "9", "12"}, "sources": {"law_2017"},
        "failures": {"FORCE_30_DAY_WAIT_ON_URGENT_HABITABILITY_DEFECT",
                     "DENY_EMERGENCY_SELF_HELP_FOR_LACK_OF_PRIOR_DEMAND",
                     "EQUATE_SET_OFF_WITH_RENT_REDUCTION"},
    },
    "security_cheque_vs_bank_guarantee_rule_split": {
        "clauses": {"4", "11"}, "sources": {"law_2017", "law_2026"},
        "failures": {"CAP_EVERY_SECURITY_CHEQUE_AT_THREE_MONTHS",
                     "EXEMPT_CHEQUE_FROM_ALL_25י_SUBSECTIONS",
                     "APPLY_2026_AMENDMENT_BEFORE_EFFECTIVE_DATE"},
    },
}
SECTION_SETS = {
    "renewal_true_option_vs_new_consent": {
        "law_2017": {"25יב(a)", "25יב(c)", "25יד", "25טו"},
    },
    "repair_urgent_exception_and_defect_waiver": {
        "law_2017": {"8", "9(a)", "9(b)", "9(c)", "25ח(a)",
                     "25ח(b)", "25ח(c)", "25ו", "25יד", "25טו"},
    },
    "security_cheque_vs_bank_guarantee_rule_split": {
        "law_2017": {"25י(a)", "25י(b)", "25י(c)", "25י(d)",
                     "25י(e)", "25יד", "25טו"},
        "law_2026": {"24", "37"},
    },
}
GATES = {"RESIDENTIAL_SCOPE_AND_25טו_EXCLUSIONS",
         "VERSION_AT_RELEVANT_DATE",
         "25יד_NON_DEROGATION_AND_FAVORABLE_TERMS",
         "ORIGINAL_AND_APPENDICES_NOT_VERIFIED",
         "SPECIALIST_PROPOSITION_REVIEW_PENDING"}


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def read(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink()
            and path.stat().st_size < 45_000, "unsafe research JSON")
    def unique(pairs: list[tuple[str, object]]) -> dict:
        out: dict = {}
        for key, value in pairs:
            require(key not in out, "duplicate JSON key")
            out[key] = value
        return out
    value = json.loads(path.read_text(encoding="utf-8"),
                       object_pairs_hook=unique)
    require(isinstance(value, dict), "JSON root must be an object")
    return value


def validate(data: dict, gold: str, overlay: dict) -> None:
    require(set(data) == {"schema_version", "as_of", "status",
            "source_contract", "source_review", "source_registry",
            "global_gates", "checks", "use"}
            and data["schema_version"] == 1 and data["as_of"] == "2026-09-23"
            and data["status"] == "SOURCE_BACKED_RESEARCH_HYPOTHESES_NOT_GOLD"
            and data["source_contract"] ==
            "research/question_engine/golden_contracts/contract_001_he.txt"
            and data["source_review"] ==
            "OWNER_TEXT_SIGNOFF_AND_PRIVATE_FAMILY_LINK_PENDING",
            "source or legal Gold promoted")
    registry = data["source_registry"]
    require(set(registry) == {"law_2017", "law_2026"}
            and registry["law_2017"]["url"] ==
            "https://fs.knesset.gov.il/20/law/20_lsr_389390.pdf"
            and registry["law_2026"]["url"] ==
            overlay["amending_law"]["official_publication_pdf"]
            and registry["law_2026"]["overlay"] ==
            "docs/statutory/ISRAEL_RENTAL_AND_LOAN_AMENDMENT_2026_V1.json"
            and registry["law_2026"]["effective_from"] ==
            overlay["commencement"]["effective_from"] == "2026-09-30"
            and registry["law_2017"]["verified_by_this_pr"].endswith(
                "NOT_OFFICIAL_PDF_BYTES")
            and registry["law_2026"]["verified_by_this_pr"] ==
            "EXISTING_DATED_OVERLAY_OFFICIAL_PDF_BYTES_UNAVAILABLE",
            "source provenance or future effective date changed")
    require(set(data["global_gates"]) == GATES
            and len(data["global_gates"]) == len(GATES), "applicability gate lost")
    marks = list(re.finditer(r"(?m)^(\d+)\.\s", gold))
    sections = {m[1]: gold[m.start():marks[i + 1].start()
                if i + 1 < len(marks) else len(gold)]
                for i, m in enumerate(marks)}
    checks = data["checks"]
    require(isinstance(checks, list) and len(checks) == 3
            and {x.get("id") for x in checks} == set(EXPECTED),
            "missing or duplicated statutory check")
    for x in checks:
        require(set(x) == {"id", "contract_clauses", "contract_quotes",
                "legal_sources", "working_hypothesis", "adversarial_check",
                "unresolved", "failure_modes", "review"},
                "unexpected crosscheck fields")
        expected = EXPECTED[x["id"]]
        require(set(x["contract_clauses"]) == expected["clauses"]
                and len(x["contract_clauses"]) == len(expected["clauses"]),
                "contract scope drift")
        require(len(x["contract_quotes"]) >= 2, "missing source evidence")
        for q in x["contract_quotes"]:
            require(set(q) == {"clause", "text"}
                    and q["clause"] in expected["clauses"]
                    and 4 <= len(q["text"]) <= 100
                    and "[" not in q["text"] and q["text"] in sections[q["clause"]],
                    "fabricated or redacted quote")
        legal_sources = x["legal_sources"]
        expected_sections = SECTION_SETS[x["id"]]
        require(isinstance(legal_sources, list)
                and len(legal_sources) == len(expected_sections)
                and all(isinstance(s, dict)
                        and set(s) == {"source", "sections"}
                        and s["source"] in registry
                        and s["source"] in expected_sections
                        and isinstance(s["sections"], list)
                        and len(s["sections"]) ==
                            len(expected_sections[s["source"]])
                        and all(isinstance(v, str) for v in s["sections"])
                        and set(s["sections"]) ==
                            expected_sections[s["source"]]
                        for s in legal_sources)
                and {s["source"] for s in legal_sources} ==
                    expected["sources"], "unverified legal source")
        require(set(x["failure_modes"]) >= expected["failures"]
                and len(x["failure_modes"]) == len(set(x["failure_modes"])),
                "required adversarial error coverage lost")
        require(all(isinstance(x[k], str) and len(x[k]) >= 100
                    for k in ("working_hypothesis", "adversarial_check"))
                and isinstance(x["unresolved"], list) and len(x["unresolved"]) >= 3
                and x["review"] == "PRIMARY_SOURCE_AND_SPECIALIST_REVIEW_REQUIRED",
                "legal uncertainty or specialist review suppressed")
    require(data["use"] == {
        "production_runtime": False, "expert_case_gold": False,
        "legal_verdicts": False,
        "private_contract_cohort": "BLOCKED_PENDING_PRIVATE_FAMILY_LINK",
        "next_canonical_step_unmodified":
            "expert-memory-contract-001-source-family-verification-v1",
    }, "unreviewed findings promoted to runtime, Gold or evaluation")


if __name__ == "__main__":
    validate(read(DATA), GOLD.read_text(encoding="utf-8"), read(OVERLAY))
    print("Three statute crosschecks: sourced hypotheses only; "
          "no runtime, legal Gold or cohort promotion.")
