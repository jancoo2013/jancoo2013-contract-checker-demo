"""Offline metadata-only inventory gate; never read or commit private originals."""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).with_name("real_contract_inventory_v1.json")
RECORD_FIELDS = {
    "id", "pages", "printed_pdf_text_layer", "library_record_candidates",
    "duplicate_evidence", "independently_reviewed_content",
    "mechanism_coverage", "template_family", "cohort_role", "privacy",
}
EVIDENCE = {
    "SINGLE_DISCOVERED_COPY",
    "FILENAME_SIZE_CANDIDATES_NOT_HASH_VERIFIED",
    "ONE_HASH_VERIFIED_DUPLICATE_PAIR_OTHER_COPY_UNVERIFIED",
}


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def validate(data: dict) -> None:
    require(isinstance(data, dict) and set(data) == {
        "schema_version", "prepared_on", "status", "scope", "observed_pdf_records",
        "retrieved_local_files", "distinct_local_sha256_groups",
        "raw_sha256_values_persisted", "confirmed_byte_identical_extra_copy_count",
        "contracts", "prior_sanitized_assets", "privacy_gate", "next_step",
    }, "invalid inventory schema")
    require(data["schema_version"] == 1
            and data["status"] == "PRIVATE_LIBRARY_METADATA_INVENTORY_ONLY"
            and data["prepared_on"] == "2026-09-23",
            "unreviewed inventory status")
    records = data["contracts"]
    require(isinstance(records, list) and len(records) == 7,
            "expected seven byte-distinct sampled documents")
    require({x.get("id") for x in records} == {
        "RC01", "RC02", "RC03", "RC04", "RC05", "RC06", "RC07",
    }, "missing or repeated anonymous record IDs")
    require(data["retrieved_local_files"] == 8
            and data["distinct_local_sha256_groups"] == 7
            and data["confirmed_byte_identical_extra_copy_count"] == 1
            and data["raw_sha256_values_persisted"] is False,
            "local duplicate evidence mismatch")
    require(sum(x["library_record_candidates"] for x in records)
            == data["observed_pdf_records"] == 14,
            "discovered PDF-record count mismatch")
    for x in records:
        require(isinstance(x, dict) and set(x) == RECORD_FIELDS,
                "unexpected private original identifier or metadata")
        require(type(x["pages"]) is int and 1 <= x["pages"] <= 20
                and type(x["library_record_candidates"]) is int
                and x["library_record_candidates"] >= 1
                and x["printed_pdf_text_layer"] in {"PRESENT", "ABSENT"}
                and x["duplicate_evidence"] in EVIDENCE,
                "invalid bounded PDF metadata")
        require(x["independently_reviewed_content"] is False
                and x["mechanism_coverage"] == "NOT_YET_MAPPED"
                and x["template_family"] == "NOT_YET_COMPARED"
                and x["cohort_role"] == "UNASSIGNED"
                and x["privacy"] == "ORIGINAL_REMAINS_IN_USER_LIBRARY",
                "source analysis or evaluation promoted without verification")
    require(sum(x["duplicate_evidence"] ==
                "ONE_HASH_VERIFIED_DUPLICATE_PAIR_OTHER_COPY_UNVERIFIED"
                for x in records) == 1,
            "verified duplicate count must be independently bounded")
    old = data["prior_sanitized_assets"]
    require(old["golden_fixture"] ==
            "research/question_engine/golden_contracts/contract_001_he.txt"
            and old["fixture_source_pages"] == 3
            and old["fixture_to_private_pdf_match"] == "NOT_ESTABLISHED"
            and old["matrix_contracts_compared"] == 2
            and old["matrix_to_private_pdf_match"] == "NOT_ESTABLISHED",
            "unverified cross-source linkage promoted")
    required_privacy = {
        "original_filenames_committed", "original_file_ids_committed",
        "original_file_hashes_committed", "unredacted_pdf_bytes_committed",
        "contract_facts_committed",
    }
    require(set(data["privacy_gate"]) == required_privacy
            and all(v is False for v in data["privacy_gate"].values()),
            "private source data may not be committed")


def read(path: Path = DATA) -> dict:
    require(path.is_file() and not path.is_symlink()
            and path.stat().st_size < 40_000,
            "unsafe or oversized inventory JSON")
    def no_duplicates(pairs: list[tuple[str, object]]) -> dict:
        out: dict = {}
        for key, value in pairs:
            require(key not in out, "duplicate JSON field")
            out[key] = value
        return out
    result = json.loads(path.read_text(encoding="utf-8"),
                        object_pairs_hook=no_duplicates)
    require(isinstance(result, dict), "inventory root must be object")
    return result


if __name__ == "__main__":
    inventory = read()
    validate(inventory)
    print(f"Private inventory: {len(inventory['contracts'])} anonymized "
          "byte-distinct PDF groups; originals not committed.")
