"""Validate a nonblind development router trace and later structured responses."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "research/question_engine/expert_memory/first_pass_router_smoke_v1.json"
FIXTURE = ROOT / "research/question_engine/golden_contracts/contract_001_he.txt"
SOURCE_REVIEW = (
    "research/question_engine/expert_memory/contract_001_source_family_crosscheck_v1.json"
)
LABELS = {
    "TERM", "RENT_PAYMENT", "OTHER_PAYMENT", "OPTION", "NOTICE", "SECURITY",
    "REPAIR", "PROPERTY_CONDITION", "DAMAGE", "TRANSFER", "EARLY_EXIT",
    "BREACH", "VACATING", "ACCESS", "INSURANCE", "OTHER",
}
KEY_ROUTES = {
    "B13": {"RENT_PAYMENT"},
    "B14": {"OPTION", "NOTICE"},
    "B15": {"BREACH", "VACATING"},
    "B21": {"TRANSFER"},
    "B22": {"EARLY_EXIT"},
    "B23": {"REPAIR", "PROPERTY_CONDITION", "DAMAGE", "VACATING"},
    "B24": {"REPAIR", "RENT_PAYMENT"},
    "B27": {"SECURITY", "OPTION"},
    "B28": {"SECURITY"},
    "B29": {"PROPERTY_CONDITION"},
    "B34": {"VACATING", "OTHER_PAYMENT"},
    "B38": {"NOTICE"},
    "B41": {"RENT_PAYMENT", "OTHER"},
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink()
            and path.stat().st_size < 100_000, "unsafe or oversized JSON input")

    def unique(pairs: list[tuple[str, object]]) -> dict:
        result: dict = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON field")
            result[key] = value
        return result

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    require(isinstance(value, dict), "expected JSON object")
    return value


def validate_response(response: dict, block_count: int) -> dict[str, set[str]]:
    """Check shape and coverage, not semantic accuracy against a model."""
    require(set(response) == {"schema_version", "items"}
            and response["schema_version"] == 1
            and isinstance(response["items"], list),
            "router response shape invalid")
    by_id: dict[str, set[str]] = {}
    for item in response["items"]:
        require(isinstance(item, dict)
                and set(item) == {"block_id", "families"},
                "router response contains generated quote, value or extra field")
        block = item["block_id"]
        families = item["families"]
        require(isinstance(block, str) and re.fullmatch(r"B\d{2}", block)
                and block not in by_id, "duplicate or malformed block ID")
        require(isinstance(families, list) and families
                and all(isinstance(label, str) for label in families)
                and len(families) == len(set(families))
                and set(families) <= LABELS | {"EXCLUDED"}
                and ("EXCLUDED" not in families or families == ["EXCLUDED"]),
                "unknown, duplicate or mixed excluded family")
        by_id[block] = set(families)
    expected = {f"B{i:02}" for i in range(1, block_count + 1)}
    require(set(by_id) == expected, "missing or fabricated source block")
    require(by_id[f"B{block_count:02}"] == {"EXCLUDED"}
            and all("EXCLUDED" not in by_id[key]
                    for key in expected - {f"B{block_count:02}"}),
            "signature marker was routed semantically")
    return by_id


def validate_packet(packet: dict, source: str) -> None:
    require(set(packet) == {"schema_version", "prepared_on", "status", "source",
                            "router_contract", "trace", "second_pass_dependencies",
                            "limitations"}
            and packet["schema_version"] == 1
            and packet["status"] ==
            "ASSISTANT_NONBLIND_DEVELOPMENT_TRACE_NOT_EVALUATION_OR_GOLD",
            "router packet promoted or malformed")
    blocks = [part.strip() for part in re.split(r"\n\s*\n", source.strip())
              if part.strip()]
    origin = packet["source"]
    require(origin["fixture"] == FIXTURE.relative_to(ROOT).as_posix()
            and origin["source_review"] == SOURCE_REVIEW
            and origin["block_count"] == len(blocks) == 43
            and origin["handwriting_excluded"] is True,
            "fixture segmentation or privacy boundary changed")
    router = packet["router_contract"]
    require(set(router["labels"]) == LABELS
            and len(router["labels"]) == len(LABELS)
            and router["special_label"] == "EXCLUDED"
            and len(router["instructions"]) == 4,
            "router contract drift")
    trace = packet["trace"]
    require(isinstance(trace, list) and len(trace) == len(blocks),
            "incomplete development trace")
    routed = validate_response({"schema_version": 1, "items": [
        {"block_id": item["block_id"], "families": item["families"]}
        for item in trace]}, len(blocks))
    for item in trace:
        require(set(item) == {"block_id", "clause", "families", "reason"}
                and isinstance(item["clause"], str) and item["clause"]
                and isinstance(item["reason"], str)
                and 10 <= len(item["reason"]) <= 400,
                "development trace has unsupported fields")
    for block, labels in KEY_ROUTES.items():
        require(labels <= routed[block], "material first-pass route disappeared")
    require("SECURITY" not in routed["B13"]
            and "EARLY_EXIT" not in routed["B34"]
            and routed["B43"] == {"EXCLUDED"},
            "payment, event or excluded-content boundary blurred")
    links = packet["second_pass_dependencies"]
    require(isinstance(links, list) and len(links) == 6
            and all(set(link) == {"blocks", "issue"}
                    and len(link["blocks"]) >= 2
                    and set(link["blocks"]) <= set(routed)
                    and 30 <= len(link["issue"]) <= 300 for link in links),
            "second-pass dependency missing or unanchored")
    limits = packet["limitations"]
    require(limits["same_assistant_had_prior_contract_and_ontology_context"] is True
            and limits["independent_model_run"] is False
            and limits["external_provider_calls"] is False
            and limits["gold_labels"] is False
            and limits["accuracy_or_recall_score"] is None
            and limits["training_eligible"] is False,
            "nonblind smoke trace mislabeled as model evaluation")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--response", type=Path,
                        help="optional model JSON; validate shape and coverage only")
    args = parser.parse_args()
    packet = read(DATA)
    source = FIXTURE.read_text(encoding="utf-8")
    validate_packet(packet, source)
    if args.response:
        validate_response(read(args.response), packet["source"]["block_count"])
        print("Router response shape and block coverage pass; semantic accuracy unmeasured.")
    else:
        print("First-pass development trace: 43 blocks and six cross-clause checks; not independent evaluation.")


if __name__ == "__main__":
    main()
