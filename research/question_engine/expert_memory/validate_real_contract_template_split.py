"""Offline audit of anonymous, provisional PDF-template and cohort links."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "research/question_engine/expert_memory"
DATA = BASE / "real_contract_template_split_v1.json"
EXPECTED = {
    "TF_A": (["RC01", "RC04"],
             "SAME_EXECUTED_DOCUMENT_DIFFERENT_CAPTURE_STRONGLY_SUPPORTED",
             "PRIVATE_MULTIPAGE_VISUAL_MATCH", "QUARANTINE_DUPLICATE_CHAIN"),
    "TF_B": (["RC02", "RC03", "RC05"],
             "SHARED_PRINTED_TEMPLATE_DISTINCT_AGREEMENT_EDITIONS",
             "PRIVATE_MULTIPAGE_VISUAL_MATCH",
             "DEVELOPMENT_CANDIDATE_SANITIZATION_REQUIRED"),
    "TF_C": (["RC06"], "VISUALLY_DISTINCT_SINGLETON_TEMPLATE",
             "PRIVATE_SAMPLED_PAGES_ONLY", "HOLDOUT_CANDIDATE_NOT_ACTIVATED"),
    "TF_D": (["RC07"], "VISUALLY_DISTINCT_SINGLETON_TEMPLATE",
             "PRIVATE_SAMPLED_PAGES_ONLY", "HOLDOUT_CANDIDATE_NOT_ACTIVATED"),
}
EXPECTED_PRIVACY = {
    "original_filenames_committed", "original_library_ids_committed",
    "byte_hashes_committed", "source_identity_map_committed",
    "original_page_images_committed", "raw_OCR_committed",
    "external_contract_provider_runs", "existing_fixture_modified",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink()
            and path.stat().st_size < 60_000, "unsafe or oversized research file")
    def no_duplicates(pairs: list[tuple[str, object]]) -> dict:
        result: dict = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON field")
            result[key] = value
        return result
    value = json.loads(path.read_text(encoding="utf-8"),
                       object_pairs_hook=no_duplicates)
    require(isinstance(value, dict), "expected JSON object")
    return value


def validate(data: dict, inventory: dict, coverage: dict, gold_meta: dict) -> None:
    require(set(data) == {
        "schema_version", "prepared_on", "status", "method", "families",
        "golden_fixture", "two_contract_matrix", "cohort_boundary",
        "still_unknown", "privacy",
    } and data["schema_version"] == 1
            and data["prepared_on"] == "2026-09-23"
            and data["status"] == "PRIVATE_VISUAL_FAMILY_RESEARCH_NOT_GOLD"
            and "OCR-free" in data["method"],
            "research review or source method overstated")
    prior_ids = {x["id"] for x in inventory["contracts"]}
    require(prior_ids == {f"RC{i:02d}" for i in range(1, 8)}
            and inventory["status"] == "PRIVATE_LIBRARY_METADATA_INVENTORY_ONLY"
            and all(x["cohort_role"] == "UNASSIGNED"
                    for x in inventory["contracts"]),
            "private inventory modified or independently reviewed")
    groups = data["families"]
    require(isinstance(groups, list) and len(groups) == 4
            and {x["id"] for x in groups} == set(EXPECTED),
            "four distinct template families required")
    covered: list[str] = []
    for family in groups:
        require(isinstance(family, dict) and set(family) == {
            "id", "groups", "relation", "basis", "review", "cohort",
        }, "unexpected sensitive family field")
        ids, relation, review, cohort = EXPECTED[family["id"]]
        require(family["groups"] == ids and family["relation"] == relation
                and family["review"] == review and family["cohort"] == cohort,
                "unverified template or cohort promoted")
        require(isinstance(family["basis"], str)
                and 30 <= len(family["basis"]) <= 500
                and "@" not in family["basis"]
                and "http" not in family["basis"].lower(),
                "source identity or unbounded unsupported evidence")
        covered.extend(family["groups"])
    require(len(covered) == len(prior_ids) and set(covered) == prior_ids,
            "anonymous PDFs omitted or duplicated")
    previous = coverage["private_groups"]
    require({x["id"] for x in previous} == prior_ids
            and all(x["coverage"] == "UNKNOWN_NOT_REVIEWED"
                    and x["cohort"] == "UNASSIGNED" for x in previous),
            "old source coverage silently rewritten")
    gold = data["golden_fixture"]
    require(set(gold) == {"source", "linked_family", "RC07_direct_match",
                          "others", "product_owner_text_review"}
            and gold["source"] ==
            "research/question_engine/golden_contracts/contract_001_he.txt"
            and gold["linked_family"] == "NOT_ESTABLISHED"
            and gold["RC07_direct_match"] ==
            "INCONSISTENT_PRINTED_TERM_AND_SECTION_STRUCTURE"
            and gold["others"] == "NOT_ESTABLISHED"
            and gold["product_owner_text_review"] == "PENDING"
            and "product-owner text-level review not yet recorded"
            in gold_meta["review_status"],
            "unverified Golden Fixture identity or review claimed")
    old = data["two_contract_matrix"]
    require(set(old) == {"source", "family_mapping", "relationship_to_golden"}
            and old["source"] ==
            "research/question_engine/dispute_practice/cross_contract_mechanism_matrix_v1.json"
            and old["family_mapping"] == old["relationship_to_golden"]
            == "NOT_ESTABLISHED", "two-contract aggregate wrongly attributed")
    split = data["cohort_boundary"]
    require(set(split) == {
        "split_status", "development_candidate", "holdout_candidates",
        "quarantined", "risk",
    } and split["split_status"] ==
            "CANDIDATES_ONLY_NO_INDEPENDENT_HOLDOUT_YET"
            and split["development_candidate"] == ["TF_B"]
            and split["holdout_candidates"] == ["TF_C", "TF_D"]
            and split["quarantined"] == ["TF_A"]
            and isinstance(split["risk"], str) and split["risk"].strip(),
            "independent cohort or held-out Gold fabricated")
    require(isinstance(data["still_unknown"], list)
            and len(data["still_unknown"]) == 3
            and all(isinstance(x, str) and len(x) > 25
                    for x in data["still_unknown"]),
            "unresolved primary-source overlap suppressed")
    require(set(data["privacy"]) == EXPECTED_PRIVACY
            and all(value is False for value in data["privacy"].values()),
            "private originals or provider use promoted")


if __name__ == "__main__":
    source = read(DATA)
    validate(source, read(BASE / "real_contract_inventory_v1.json"),
             read(BASE / "real_contract_coverage_v1.json"),
             read(ROOT / "research/question_engine/golden_contracts/contract_001.meta.json"))
    print("Template split: 4 candidate families / 7 anonymized PDFs; "
          "dev/holdout NOT ACTIVATED and NOT legal Gold.")
