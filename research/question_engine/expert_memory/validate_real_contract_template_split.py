"""Offline audit of the anonymized real-contract template-family split."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "research/question_engine/expert_memory"
DATA = BASE / "real_contract_template_split_v1.json"
EXPECTED = {
    "TF_A": (["RC01", "RC04"],
             "SAME_EXECUTED_AGREEMENT_DIFFERENT_CAPTURE_CONFIRMED",
             "DEVELOPMENT_DUPLICATE_CHAIN_ONE_CONTENT_INSTANCE"),
    "TF_B": (["RC02", "RC03", "RC05"],
             "SHARED_PRINTED_TEMPLATE_DISTINCT_AGREEMENT_EDITIONS_CONFIRMED",
             "DEVELOPMENT"),
    "TF_C": (["RC06"], "DISTINCT_SINGLETON_TEMPLATE_CONFIRMED",
             "INDEPENDENT_TEST_RESERVED"),
    "TF_D": (["RC07"], "DISTINCT_SINGLETON_TEMPLATE_CONFIRMED",
             "INDEPENDENT_TEST_RESERVED"),
}
PRIVACY_FIELDS = {
    "original_filenames_committed", "original_library_ids_committed",
    "byte_hash_values_committed", "source_identity_map_committed",
    "original_page_images_committed", "raw_OCR_committed",
    "external_contract_provider_runs", "sidecar_report_used_as_evidence",
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
        "schema_version", "prepared_on", "status", "source_summary",
        "families", "golden_fixture", "prior_two_contract_research",
        "cohort_boundary", "still_unknown", "privacy",
    } and data["schema_version"] == 1
            and data["prepared_on"] == "2026-09-23"
            and data["status"] == "PRIVATE_LOCAL_TEMPLATE_FAMILY_SPLIT_NOT_GOLD",
            "template research status overstated")

    source = data["source_summary"]
    require(set(source) == {
        "scope", "pdf_count", "distinct_byte_groups",
        "exact_duplicate_extra_copies", "method", "identifiers_persisted",
    } and source["pdf_count"] == 8
            and source["distinct_byte_groups"] == 7
            and source["exact_duplicate_extra_copies"] == 1
            and source["identifiers_persisted"] is False
            and "no OCR" in source["method"]
            and "no report or sidecar JSON" in source["scope"],
            "private local source evidence changed")

    prior_ids = {item["id"] for item in inventory["contracts"]}
    require(prior_ids == {f"RC{i:02d}" for i in range(1, 8)}
            and inventory["status"] == "PRIVATE_LIBRARY_METADATA_INVENTORY_ONLY",
            "private inventory identity changed")
    families = data["families"]
    require(isinstance(families, list) and len(families) == 4
            and {item["id"] for item in families} == set(EXPECTED),
            "four confirmed template families required")
    covered: list[str] = []
    cohort_by_group: dict[str, str] = {}
    for family in families:
        require(set(family) == {
            "id", "groups", "relation", "evidence", "evidence_grade", "cohort",
        }, "unexpected sensitive family field")
        ids, relation, cohort = EXPECTED[family["id"]]
        require(family["groups"] == ids and family["relation"] == relation
                and family["cohort"] == cohort,
                "confirmed family or cohort assignment changed")
        require(family["evidence_grade"].startswith("PRIVATE_")
                and 40 <= len(family["evidence"]) <= 500
                and "@" not in family["evidence"]
                and "http" not in family["evidence"].lower(),
                "source identity or unsupported public evidence")
        for group in ids:
            require(group not in cohort_by_group, "group crosses template families")
            cohort_by_group[group] = cohort
        covered.extend(ids)
    require(set(covered) == prior_ids and len(covered) == len(prior_ids),
            "anonymous PDF groups omitted or duplicated")

    require(all(item["coverage"] == "UNKNOWN_NOT_REVIEWED"
                for item in coverage["private_groups"]),
            "template comparison fabricated mechanism coverage")
    gold = data["golden_fixture"]
    require(set(gold) == {
        "source", "linked_family", "excluded_direct_matches", "other_private_groups",
        "selection", "training_eligibility", "product_owner_text_review",
    } and gold["source"] ==
            "research/question_engine/golden_contracts/contract_001_he.txt"
            and gold["linked_family"] == "UNKNOWN"
            and gold["excluded_direct_matches"] == ["RC07"]
            and gold["other_private_groups"] == "UNKNOWN"
            and gold["selection"] == "SELECTED_NEXT_DEEP_EXPERT_REVIEW"
            and gold["training_eligibility"] ==
            "BLOCKED_PENDING_PRIVATE_FAMILY_LINKAGE"
            and gold["product_owner_text_review"] == "PENDING"
            and "product-owner text-level review not yet recorded"
            in gold_meta["review_status"],
            "unverified Golden Fixture identity or training use claimed")

    old = data["prior_two_contract_research"]
    require(set(old) == {"source", "original_groups", "family_mapping", "reason"}
            and old["source"] ==
            "research/question_engine/dispute_practice/cross_contract_mechanism_matrix_v1.json"
            and old["original_groups"] == old["family_mapping"] == "UNKNOWN"
            and len(old["reason"]) >= 50,
            "prior two-contract originals wrongly attributed")

    split = data["cohort_boundary"]
    require(set(split) == {
        "status", "development_families", "independent_test_families",
        "unassigned_families", "rationale", "leakage_rule",
    } and split["status"] == "FAMILY_DISJOINT_SPLIT_RESERVED"
            and split["development_families"] == ["TF_A", "TF_B"]
            and split["independent_test_families"] == ["TF_C", "TF_D"]
            and split["unassigned_families"] == []
            and set(split["development_families"]).isdisjoint(
                split["independent_test_families"])
            and all(family["id"] in split["development_families"]
                    for family in families if family["cohort"].startswith("DEVELOPMENT"))
            and all(family["id"] in split["independent_test_families"]
                    for family in families if family["cohort"] ==
                    "INDEPENDENT_TEST_RESERVED"),
            "family-disjoint cohort boundary violated")
    require(isinstance(data["still_unknown"], list)
            and len(data["still_unknown"]) == 4
            and all(isinstance(item, str) and len(item) > 40
                    for item in data["still_unknown"]),
            "material uncertainty suppressed")
    require(set(data["privacy"]) == PRIVACY_FIELDS
            and all(value is False for value in data["privacy"].values()),
            "private source data or provider use promoted")


if __name__ == "__main__":
    validate(read(DATA), read(BASE / "real_contract_inventory_v1.json"),
             read(BASE / "real_contract_coverage_v1.json"),
             read(ROOT / "research/question_engine/golden_contracts/contract_001.meta.json"))
    print("Template split: 4 families / 7 anonymous groups; family-disjoint "
          "development and reserved independent-test cohorts; not legal Gold.")
