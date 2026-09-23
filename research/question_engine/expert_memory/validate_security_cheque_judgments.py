"""Offline case-law source-integrity checks, not a legal Gold-set oracle."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from urllib.parse import urlsplit

DATA = Path(__file__).with_name("security_cheque_judgments_v1.json")
EXPECTED = {
    "35226-02-20": ("he.afiklaw.com", "PUBLIC_FULL_JUDGMENT_MIRROR",
                    "SECURITY_NOTE_CLAIM_DISMISSED"),
    "8191-03-20": ("lawbuzz.co.il", "SEARCH_INDEX_JUDGMENT_EXCERPTS",
                  "SMALL_PART_OF_AMENDED_CLAIM_ALLOWED_EXACT_AMOUNT_NOT_READ"),
    "52670-10-12": ("judgments.org.il", "SEARCH_INDEX_JUDGMENT_TRANSCRIPT",
                    "PARTLY_ALLOWED_27244_ILS_INDEXED"),
    "18162-02-13": ("www.psakdin.co.il", "PUBLIC_PARTIAL_JUDGMENT_MIRROR",
                    "FINAL_DISPOSITION_NOT_VISIBLE"),
    "5433-09": ("www.psakdin.co.il", "PUBLIC_FULL_JUDGMENT_MIRROR",
                "BOTH_CLAIMS_DISMISSED_EXECUTION_FILE_CLOSED"),
}


def ensure(ok: bool, why: str) -> None:
    if not ok:
        raise ValueError(why)


def validate(data: dict) -> None:
    ensure(isinstance(data, dict) and set(data) ==
           {"schema_version", "reviewed_on", "status", "purpose", "cases",
            "gaps", "training_eligible", "gold_eligible"},
           "invalid cohort structure")
    ensure(type(data["schema_version"]) is int and data["schema_version"] == 1
           and data["status"] == "MIRRORED_CASE_LAW_RESEARCH_NOT_OFFICIAL_NOT_GOLD"
           and data["training_eligible"] is False
           and data["gold_eligible"] is False, "case law promoted beyond research")
    reviewed = date.fromisoformat(data["reviewed_on"])
    ensure(isinstance(data["purpose"], str) and bool(data["purpose"].strip())
           and isinstance(data["cases"], list) and len(data["cases"]) == 5,
           "expected five documented case-law leads")
    seen: set[str] = set()
    for c in data["cases"]:
        ensure(isinstance(c, dict) and set(c) ==
               {"id", "docket", "judgment_date", "court", "source_url",
                "access", "statutory_era", "instrument", "judicial_evidence",
                "disposition", "possible_model_error", "required_cross_checks",
                "limits", "error_origin", "review_status"},
               "invalid case-law record")
        docket = c["docket"]
        ensure(docket in EXPECTED and docket not in seen, "duplicate/unknown docket")
        seen.add(docket)
        hostname, access, disposition = EXPECTED[docket]
        url = urlsplit(c["source_url"])
        ensure(url.scheme == "https" and url.hostname == hostname
               and url.username is None and url.password is None
               and url.port is None and not url.fragment and bool(url.path),
               "unapproved or malformed case-law mirror")
        ensure(c["access"] == access and c["disposition"] == disposition,
               "source access or unseen disposition promoted")
        judged = date.fromisoformat(c["judgment_date"])
        era = "POST_2017" if judged >= date(2017, 9, 17) else "PRE_2017"
        ensure(judged <= reviewed and c["statutory_era"] == era,
               "judgment date or statutory-era mismatch")
        ensure(c["court"].endswith("Magistrates Court")
               and c["error_origin"] ==
               "HYPOTHESIZED_FROM_COURT_FACT_PATTERN_NOT_OBSERVED_MODEL_FAILURE"
               and c["review_status"] == "NEEDS_ORIGINAL_AND_SPECIALIST_REVIEW",
               "judicial hierarchy, expert or model-error origin overstated")
        ensure(isinstance(c["judicial_evidence"], list)
               and len(c["judicial_evidence"]) >= 2
               and all(isinstance(e, dict) and set(e) == {"locator", "finding"}
                       and all(isinstance(e[k], str) and e[k].strip()
                               for k in ("locator", "finding"))
                       for e in c["judicial_evidence"]),
               "missing traceable judicial evidence")
        for field in ("id", "instrument", "possible_model_error", "limits"):
            ensure(isinstance(c[field], str) and c[field].strip(),
                   "missing case identifier, risk hypothesis or limitation")
        checks = c["required_cross_checks"]
        ensure(isinstance(checks, list) and len(checks) >= 3
               and len(checks) == len(set(checks))
               and all(isinstance(x, str) and x for x in checks),
               "missing cross-clause or evidentiary dependencies")
    ensure(seen == set(EXPECTED), "five selected cases missing")
    ensure(isinstance(data["gaps"], list) and len(data["gaps"]) >= 3
           and all(isinstance(x, str) and x.strip() for x in data["gaps"]),
           "unverified court originals and retrieval gaps must be explicit")


def read(path: Path = DATA) -> dict:
    ensure(path.is_file() and not path.is_symlink()
           and path.stat().st_size <= 100_000,
           "unsafe or oversized case-law dataset")
    def strict_pairs(pairs: list[tuple[str, object]]) -> dict:
        out: dict = {}
        for key, value in pairs:
            ensure(key not in out, "duplicate JSON field")
            out[key] = value
        return out
    value = json.loads(path.read_text(encoding="utf-8"),
                       object_pairs_hook=strict_pairs)
    ensure(isinstance(value, dict), "case-law dataset is not an object")
    return value


if __name__ == "__main__":
    data = read()
    validate(data)
    print(f"Case law: {len(data['cases'])} mirrored/indexed judgments; "
          "NOT official originals, observed model failures, or legal Gold.")
