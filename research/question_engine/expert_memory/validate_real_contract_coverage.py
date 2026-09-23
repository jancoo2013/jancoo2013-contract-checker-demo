"""Validate research-only source-scoped coverage; never read private lease PDFs."""

from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "research/question_engine/expert_memory"
DATA = BASE / "real_contract_coverage_v1.json"
GOLD_CLAUSES = {
    "security_and_enforcement": ["4", "11"],
    "early_exit_and_replacement_tenant": ["7", "8"],
    "financial_sanctions_and_overlap": ["4", "9", "17"],
    "condition_as_is_defects_damage": ["9", "12"],
    "termination_cure_notice_eviction": ["4", "19", "21"],
    "option_and_renewal": ["3", "4", "11"],
    "utilities_and_occupancy_charges": ["5", "6"],
    "landlord_access": ["15"],
    "alterations_and_restoration": ["9", "14", "16"],
    "third_party_indemnity": ["9"],
}
UNESTABLISHED = {
    "broad_no_setoff", "shared_meter_accounting",
    "inventory_handwriting_dependency",
}
CHECK_IDS = {
    "term_and_option", "instrument_identity_and_return",
    "exit_and_assignment", "condition_repairs_and_appendix",
    "cancellation_and_notice", "overlapping_money_heads",
    "third_party_and_repair",
}
SOURCE_PATHS = {
    "golden_fixture": "research/question_engine/golden_contracts/contract_001_he.txt",
    "golden_metadata": "research/question_engine/golden_contracts/contract_001.meta.json",
    "aggregate_matrix": "research/question_engine/dispute_practice/cross_contract_mechanism_matrix_v1.json",
    "private_inventory": "research/question_engine/expert_memory/real_contract_inventory_v1.json",
}


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def read(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink() and
            path.stat().st_size < 70_000, "unsafe or oversized source")
    def unique(pairs: list[tuple[str, object]]) -> dict:
        out: dict = {}
        for key, value in pairs:
            require(key not in out, "duplicate JSON field")
            out[key] = value
        return out
    obj = json.loads(path.read_text(encoding="utf-8"),
                     object_pairs_hook=unique)
    require(isinstance(obj, dict), "root must be object")
    return obj


def validate(data: dict, matrix: dict, inventory: dict,
             meta: dict, gold_text: str) -> None:
    require(isinstance(data, dict) and set(data) == {
        "schema_version", "prepared_on", "status", "sources", "linkage",
        "mechanisms", "golden_cross_clause_checks", "private_groups", "policy",
    } and data["schema_version"] == 1 and data["prepared_on"] == "2026-09-23"
            and data["status"] == "SANITIZED_SOURCE_SCOPED_RESEARCH_NOT_GOLD",
            "unsupported coverage schema or review promotion")
    sources = data["sources"]
    require(set(sources) == set(SOURCE_PATHS) |
            {"golden_review", "aggregate_evidence"}
            and all(sources[k] == v for k, v in SOURCE_PATHS.items())
            and sources["golden_review"] ==
            "ASSISTANT_TWO_PASS_OWNER_REVIEW_PENDING"
            and sources["aggregate_evidence"] ==
            "TWO_CONTRACT_RESEARCH_CLASSIFICATION_NOT_PER_DOCUMENT_ORACLE",
            "unverified source evidence promoted")
    require(meta["fixture_id"] == "contract_001"
            and meta["source_pages"] == 3 and meta["pii_removed"] is True
            and "product-owner text-level review not yet recorded"
            in meta["review_status"], "golden fixture review or privacy mismatch")
    require(matrix["artifact_status"] ==
            "CROSS_CONTRACT_CLASSIFICATION_RESEARCH_ONLY_DO_NOT_USE_AS_LEGAL_AUTHORITY"
            and matrix["contracts_compared"] == 2
            and inventory["status"] == "PRIVATE_LIBRARY_METADATA_INVENTORY_ONLY",
            "aggregate or private source status promoted")
    require(set(data["linkage"]) == {
        "golden_to_inventory", "aggregate_to_inventory", "golden_to_aggregate"}
            and all(x == "NOT_ESTABLISHED" for x in data["linkage"].values()),
            "unverified source identity inferred")
    known_clauses = set(re.findall(r"(?m)^(\d+)\.\s", gold_text))
    rows = data["mechanisms"]
    require(isinstance(rows, list) and len(rows) == 13
            and all(isinstance(x, dict) and set(x) == {
                "id", "classification", "aggregate_seen", "aggregate_total",
                "golden_status", "golden_clause_ids", "note"} for x in rows),
            "invalid mechanism rows")
    by_id = {x["id"]: x for x in rows}
    prior = {x["id"]: x for x in matrix["mechanism_families"]}
    require(len(by_id) == len(rows) and set(by_id) == set(prior)
            == set(GOLD_CLAUSES) | UNESTABLISHED,
            "missing, duplicate or invented mechanism")
    for key, x in by_id.items():
        old = prior[key]
        expected = GOLD_CLAUSES.get(key, [])
        require(x["classification"] == old["classification"]
                and x["aggregate_seen"] == old["seen_in_contracts"]
                and x["aggregate_total"] == matrix["contracts_compared"],
                "aggregate research re-attributed or altered")
        require(x["golden_clause_ids"] == expected
                and set(expected) <= known_clauses
                and x["golden_status"] == (
                    "EVIDENCED_IN_SANITIZED_FIXTURE" if expected else
                    "NOT_ESTABLISHED_IN_SANITIZED_FIXTURE")
                and isinstance(x["note"], str) and x["note"].strip(),
                "unreviewed golden fixture claim or unsupported clause")
    checks = data["golden_cross_clause_checks"]
    require(isinstance(checks, list) and len(checks) == len(CHECK_IDS)
            and {x.get("id") for x in checks} == CHECK_IDS,
            "missing cross-clause challenges")
    for x in checks:
        require(set(x) == {"id", "clauses", "question", "must_not_assume"}
                and isinstance(x["clauses"], list) and len(x["clauses"]) >= 2
                and len(set(x["clauses"])) == len(x["clauses"])
                and set(x["clauses"]) <= known_clauses
                and all(isinstance(x[k], str) and x[k].strip()
                        for k in ("question", "must_not_assume")),
                "cross-clause question lacks printed evidence or caveat")
    groups = data["private_groups"]
    require(isinstance(groups, list) and
            {x.get("id") for x in groups} ==
            {x["id"] for x in inventory["contracts"]}
            and len(groups) == len(inventory["contracts"]) == 7,
            "private inventory references not synchronized")
    for x in groups:
        require(set(x) == {"id", "coverage", "template_family", "cohort"}
                and x["coverage"] == "UNKNOWN_NOT_REVIEWED"
                and x["template_family"] == "UNVERIFIED"
                and x["cohort"] == "UNASSIGNED",
                "private contract coverage or holdout fabricated")
    require(data["policy"] == {
        "no_negative_inference_from_unmentioned_clause": True,
        "do_not_infer_handwriting": True,
        "eligible_gold": False,
        "training_or_evaluation_assignment": "PENDING_PRIVATE_TEMPLATE_COMPARISON",
        "real_contract_provider_runs": False,
    }, "real-contract privacy, Gold or evaluation boundary relaxed")


if __name__ == "__main__":
    evidence = {k: ROOT / v for k, v in SOURCE_PATHS.items()}
    validate(read(DATA), read(evidence["aggregate_matrix"]),
             read(evidence["private_inventory"]), read(evidence["golden_metadata"]),
             evidence["golden_fixture"].read_text(encoding="utf-8"))
    print("Coverage: 13 mechanism families, 7 cross-clause checks, "
          "7 private groups UNKNOWN; NOT legal Gold.")
