"""Offline ExpertCase v1 provenance gate; validates structure, not legal truth."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from contract_checker.question_engine.inventory import ECONOMIC_CORE_INVENTORY_V1

ROOT = Path(__file__).resolve().parents[3]
SOURCE_PATH = "research/question_engine/smart_analysis_corpus_v1.json"
SEED_PATH = Path(__file__).with_name("expert_cases_v1.json")
QUESTIONS = {q.question_id: q for q in ECONOMIC_CORE_INVENTORY_V1.questions}
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
REF = re.compile(r"^c[0-9]+$")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def keys(value: object, required: set[str], optional: set[str] = set()) -> None:
    check(isinstance(value, dict), "expected object")
    check(required <= value.keys() and value.keys() <= required | optional,
          "invalid object keys: " + repr(value.keys()))


def unique_json(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        check(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(path: Path, limit: int = 2_000_000) -> tuple[dict, bytes]:
    check(path.is_file() and not path.is_symlink() and path.stat().st_size <= limit,
          "unsafe or oversized JSON input")
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_json)
    check(isinstance(value, dict), "root must be an object")
    return value, raw


def refs(value: object, valid: set[str], *, allow_scope: bool = False) -> set[str]:
    check(isinstance(value, list) and bool(value), "empty or invalid evidence refs")
    check(all(isinstance(v, str) for v in value), "non-string evidence ref")
    check(len(value) == len(set(value)), "duplicate evidence refs")
    allowed = valid | ({"@scope"} if allow_scope else set())
    check(set(value) <= allowed, "invented or misplaced evidence ref")
    return set(value)


def validate(dataset: dict, source: dict, raw_source: bytes) -> None:
    keys(dataset, {"schema_version", "source_corpus_path", "source_git_blob_sha", "cases"})
    check(type(dataset["schema_version"]) is int and dataset["schema_version"] == 1,
          "unsupported ExpertCase schema version")
    check(dataset["source_corpus_path"] == SOURCE_PATH, "unapproved source corpus")
    blob = hashlib.sha1(b"blob " + str(len(raw_source)).encode() + b"\0" + raw_source).hexdigest()
    check(dataset["source_git_blob_sha"] == blob, "source corpus revision changed")
    check(source.get("schema_version") == 2, "unexpected source corpus version")
    check(isinstance(dataset["cases"], list) and 1 <= len(dataset["cases"]) <= 256,
          "invalid ExpertCase count")
    original = {c["case_id"]: c for c in source["cases"]}
    check(len(original) == len(source["cases"]), "duplicate source case id")
    case_ids: set[str] = set()
    source_ids: set[str] = set()
    family_split: dict[str, str] = {}
    seen_text: dict[str, str] = {}
    splits: set[str] = set()
    for case in dataset["cases"]:
        required = {"case_id", "source_case_id", "source_basis", "error_origin",
                    "template_family", "split", "review", "spans", "mechanisms",
                    "facts", "links", "wrong_reading", "corrected_reading", "discriminator"}
        keys(case, required)
        cid = case["case_id"]
        check(isinstance(cid, str) and cid.startswith("em_") and
              IDENTIFIER.fullmatch(cid), "invalid ExpertCase id")
        check(cid not in case_ids, "duplicate ExpertCase id")
        case_ids.add(cid)
        sid = case["source_case_id"]
        check(isinstance(sid, str) and sid in original and sid not in source_ids,
              "missing or reused source case")
        source_ids.add(sid)
        src = original[sid]
        check(src["domain"] == "security" and src["basis"] == case["source_basis"] and
              case["source_basis"] in {"synthetic_from_observed_pattern",
                                       "synthetic_boundary_case"},
              "source provenance mismatch")
        check(case["error_origin"] == "CONSTRUCTED_WRONG_READING",
              "synthetic example cannot claim an observed model error")
        review = case["review"]
        keys(review, {"status", "reviewer_ref", "review_evidence_refs"})
        check(review == {"status": "UNVERIFIED", "reviewer_ref": None,
                         "review_evidence_refs": []},
              "synthetic/generated case cannot claim independent expert review")
        split, family = case["split"], case["template_family"]
        check(split in {"train", "evaluation"} and isinstance(family, str) and
              IDENTIFIER.fullmatch(family), "invalid split or template family")
        check(family_split.setdefault(family, split) == split,
              "template family leaks across train/evaluation")
        splits.add(split)

        check(case["spans"] == src["clauses"], "source spans differ from pinned corpus")
        clause_refs = {c["ref"] for c in src["clauses"]}
        check(len(clause_refs) == len(src["clauses"]) and
              all(REF.fullmatch(r) for r in clause_refs), "duplicate/invalid source ref")
        for span in src["clauses"]:
            normalized = " ".join(span["text_he"].split())
            previous = seen_text.setdefault(normalized, split)
            check(previous == split, "identical source span leaks across splits")

        source_facts = {}
        for assertion in src["assertions"]:
            key = (assertion["question_id"], assertion.get("mechanism_id"),
                   assertion["field"])
            check(key not in source_facts, "duplicate source assertion")
            check("state" not in assertion, "v1 seed does not support stateful assertions")
            source_facts[key] = assertion
        mechanisms = {}
        for mechanism in case["mechanisms"]:
            keys(mechanism, {"mechanism_id", "anchor_ref"})
            mid = mechanism["mechanism_id"]
            check(isinstance(mid, str) and IDENTIFIER.fullmatch(mid) and
                  mid not in mechanisms, "duplicate/invalid mechanism id")
            check(mechanism["anchor_ref"] in clause_refs, "invalid mechanism anchor")
            mechanisms[mid] = mechanism["anchor_ref"]
        expected_ids = {key[1] for key in source_facts if key[1] is not None}
        check(set(mechanisms) == expected_ids, "missing or invented mechanism")
        fact_keys: set[tuple[str, str | None, str]] = set()
        used_by_mechanism: dict[str, set[str]] = {m: set() for m in mechanisms}
        for fact in case["facts"]:
            keys(fact, {"question_id", "field", "expected", "refs"}, {"mechanism_id"})
            question_id, field = fact["question_id"], fact["field"]
            question = QUESTIONS.get(question_id)
            check(question is not None and question.domain == "security" and
                  field in question.answer_fields, "invalid Question Engine field")
            mid = fact.get("mechanism_id")
            check(mid is None or mid in mechanisms, "unknown fact mechanism")
            key = (question_id, mid, field)
            check(key in source_facts and key not in fact_keys,
                  "invented or duplicate fact")
            fact_keys.add(key)
            source_fact = source_facts[key]
            check(fact == {k: source_fact[k] for k in source_fact},
                  "fact value, mechanism or source refs differ from oracle")
            cited = refs(fact["refs"], clause_refs,
                         allow_scope=question_id in src.get("complete_for", []))
            if mid is not None:
                used_by_mechanism[mid].update(cited - {"@scope"})
        check(fact_keys == set(source_facts), "missing source-backed facts")
        for mid, anchor in mechanisms.items():
            typed = [a for a in src["assertions"] if a.get("mechanism_id") == mid
                     and a["field"] == "instrument_types"]
            if typed:
                check(anchor in typed[0]["refs"], "mechanism anchor belongs to another instrument")
            else:
                candidate_refs = set(src.get("candidate", {}).get("subject_refs", []))
                check(anchor in used_by_mechanism[mid] | candidate_refs,
                      "mechanism anchor has no source support")
        check(isinstance(case["links"], list), "links must be a list")
        link_keys: set[tuple[str, str]] = set()
        for link in case["links"]:
            keys(link, {"mechanism_id", "from_ref", "to_ref", "kind"})
            mid = link["mechanism_id"]
            check(mid in mechanisms and link["from_ref"] == mechanisms[mid] and
                  link["to_ref"] in used_by_mechanism[mid] and
                  link["to_ref"] != link["from_ref"] and
                  link["kind"] in {"QUALIFIES", "PROCEDURAL_STEP", "RETURN_RULE"},
                  "unsupported or cross-instrument link")
            check((mid, link["to_ref"]) not in link_keys, "duplicate cross-clause link")
            link_keys.add((mid, link["to_ref"]))
        readings = {}
        for name in ("wrong_reading", "corrected_reading", "discriminator"):
            reading = case[name]
            keys(reading, {"text", "refs"})
            check(isinstance(reading["text"], str) and reading["text"].strip(),
                  "empty reasoning evidence text")
            reading_refs = refs(reading["refs"], clause_refs,
                                allow_scope=bool(src.get("complete_for")))
            readings[name] = reading_refs
        check(readings["corrected_reading"] & (
              set().union(*used_by_mechanism.values()) | {"@scope"}),
              "corrected reading has no assertion evidence")
        check(all(link["to_ref"] in readings["discriminator"] for link in case["links"]),
              "discriminator omits a cross-clause link")
        if len(mechanisms) > 1:
            check(all(readings["discriminator"] & used_by_mechanism[mid]
                      for mid in mechanisms),
                  "discriminator omits an instrument")
    check(splits == {"train", "evaluation"}, "both train and evaluation required")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=SEED_PATH)
    parser.add_argument("--source", type=Path, default=ROOT / SOURCE_PATH)
    args = parser.parse_args()
    dataset, _ = read_json(args.cases)
    source, raw = read_json(args.source)
    validate(dataset, source, raw)
    print(f"ExpertCase v1: {len(dataset['cases'])} synthetic cases validated; "
          "no independent legal review claimed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
