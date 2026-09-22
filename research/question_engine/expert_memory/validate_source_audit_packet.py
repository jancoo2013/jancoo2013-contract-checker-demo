"""Offline integrity gate for source leads, not verification of their legal truth."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "research/question_engine/expert_memory"
ALLOWED_HOSTS = {"fs.knesset.gov.il", "main.knesset.gov.il", "www.gov.il"}
FIELDS = {
    "source": {"id", "title", "publisher", "kind", "url", "source_date",
               "checked_on", "access_level", "locator", "limit"},
    "claim": {"id", "source_id", "locator", "proposition", "support",
              "does_not_support", "review"},
    "link": {"case_id", "claim_ids", "relation"},
    "unresolved": {"id", "question", "source_ids", "needs_specialist_review"},
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def fields(value: object, expected: set[str], label: str) -> None:
    require(isinstance(value, dict) and set(value) == expected,
            f"{label}: missing or unexpected fields")


def unique(items: list[dict], label: str) -> dict[str, dict]:
    require(isinstance(items, list), f"{label}: expected array")
    result: dict[str, dict] = {}
    for item in items:
        require(isinstance(item, dict) and isinstance(item.get("id"), str)
                and item["id"] and item["id"] not in result,
                f"{label}: duplicate or invalid id")
        result[item["id"]] = item
    return result


def identifiers(value: object, allowed: set[str], label: str) -> None:
    require(isinstance(value, list) and bool(value)
            and all(isinstance(x, str) for x in value)
            and len(set(value)) == len(value) and set(value) <= allowed,
            f"{label}: unknown, duplicated or missing references")


def valid_date(value: object, label: str) -> date:
    require(isinstance(value, str) and len(value) == 10, f"{label}: invalid date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label}: invalid date") from exc


def validate(packet: dict, expert_cases: dict, overlay: dict) -> None:
    fields(packet, {"schema_version", "prepared_on", "status", "sources",
                    "claims", "case_links", "unresolved"}, "packet")
    require(type(packet["schema_version"]) is int and packet["schema_version"] == 1,
            "unsupported packet version")
    require(packet["status"] == "SOURCE_DISCOVERY_NOT_EXPERT_VERIFIED",
            "source packet must not be promoted")
    prepared = valid_date(packet["prepared_on"], "prepared_on")
    sources = unique(packet["sources"], "sources")
    require(4 <= len(sources) <= 7, "expected a bounded 4-7 source packet")
    for item in sources.values():
        fields(item, FIELDS["source"], "source")
        for key in ("title", "publisher", "locator", "limit"):
            require(isinstance(item[key], str) and item[key].strip(),
                    f"source {item['id']}: invalid {key}")
        uri = urlsplit(item["url"])
        require(uri.scheme == "https" and uri.hostname in ALLOWED_HOSTS
                and not uri.username and not uri.password and uri.port is None
                and not uri.fragment and uri.path.startswith("/"),
                f"source {item['id']}: unapproved source URL")
        require(valid_date(item["checked_on"], "checked_on") == prepared,
                "source check date differs from packet date")
        if item["source_date"] is not None:
            require(valid_date(item["source_date"], "source_date") <= prepared,
                    "source publication date is in the future")
        access = item["access_level"]
        kind = item["kind"]
        require((kind == "ENACTED_HISTORICAL" and access == "PRIMARY_TEXT_READ")
                or (kind == "ENACTED_AMENDMENT" and access == "GAZETTE_COPY_READ")
                or (kind == "LIVE_CATALOG" and access == "CATALOG_METADATA_ONLY")
                or (kind in {"PROPOSED_NOT_LAW", "AGENCY_SERVICE",
                             "AGENCY_PROCEDURE"} and access == "INDEX_EXCERPT_ONLY"),
                "source authority/access mismatch")

    claims = unique(packet["claims"], "claims")
    require(len(claims) >= 4, "insufficient source propositions")
    for claim in claims.values():
        fields(claim, FIELDS["claim"], "claim")
        require(claim["source_id"] in sources, "claim: unknown source")
        for key in ("locator", "proposition", "does_not_support"):
            require(isinstance(claim[key], str) and claim[key].strip(),
                    f"claim: missing {key}")
        require(claim["review"] == "NEEDS_PRIMARY_SOURCE_AND_SPECIALIST_REVIEW",
                "claim promoted without independent verification")
        kind = sources[claim["source_id"]]["kind"]
        support = claim["support"]
        require((kind == "ENACTED_HISTORICAL" and support == "DIRECT_HISTORICAL_TEXT")
                or (kind == "ENACTED_AMENDMENT"
                    and support == "DIRECT_ENACTED_TEXT")
                or (kind == "PROPOSED_NOT_LAW"
                    and support == "INDEX_EXCERPT_PROPOSAL_ONLY")
                or (kind in {"AGENCY_SERVICE", "AGENCY_PROCEDURE"}
                    and support == "INDEX_EXCERPT_RECHECK"),
                "claim: unsupported source authority or review level")

    # The enactment's commencement stays in the citation record, not in
    # an ExpertCase activation rule. This validator checks source integrity.
    require(overlay.get("snapshot_id") == "israel-rental-and-loan-amendment-2026-v1"
            and overlay.get("status") == "ENACTED_GAZETTE_NOT_EXPERT_REVIEWED",
            "unsupported 2026 overlay or review promotion")
    law = overlay["amending_law"]
    effective = overlay["commencement"]
    source = sources.get("knesset_2026_enacted_rental_security")
    require(source is not None and source["kind"] == "ENACTED_AMENDMENT"
            and source["access_level"] == "GAZETTE_COPY_READ"
            and source["url"] == law["official_publication_pdf"]
            and source["source_date"] == law["publication_date"],
            "2026 overlay/source provenance mismatch")
    require(law["publication_issue"] == 3510 and law["amending_section"] == 24
            and law["commencement_section"] == 37
            and law["published_pages"] == [363, 364, 370]
            and law["original_official_pdf_fetch"] == "UNAVAILABLE_DURING_THIS_REVIEW"
            and law["gazette_copy_read"] == "PAGES_363_364_AND_370",
            "2026 Gazette locator or access overstatement")
    require(overlay["as_of"] == packet["prepared_on"]
            and effective["chapter"] == "VI",
            "2026 overlay/packet mismatch")
    valid_date(effective["effective_from"], "commencement")
    require(overlay["normalized_changes"]["section_25y_b_opening"]["after"]
            == "ערבות בנקאית, ערבות מנותן ערבות אחר"
            and overlay["normalized_changes"]["section_25y_a"]["provider_classes"]
            == ["licensed_credit_provider", "licensed_deposit_and_credit_provider",
                "licensed_financially_stable_payment_service_provider", "insurer"]
            and overlay["normalized_changes"]["section_25y_b_opening"]
                ["contract_type_dependency"] == "RESIDENTIAL_SCOPE_25טו"
            and overlay["usage"]["production_runtime_wired"] is False
            and overlay["usage"]["expert_verified"] is False,
            "2026 security amendment content or authority promotion")
    require(claims["enacted_2026_other_guarantee_providers"]["source_id"]
            == source["id"] and
            claims["enacted_2026_other_guarantee_providers"]["support"]
            == "DIRECT_ENACTED_TEXT",
            "2026 enacted claim missing or misattributed")

    require(expert_cases.get("schema_version") == 1, "unknown ExpertCase version")
    case_ids = {case["case_id"] for case in expert_cases["cases"]}
    require(len(case_ids) == len(expert_cases["cases"]), "duplicate ExpertCase ID")
    links: set[str] = set()
    require(isinstance(packet["case_links"], list), "case_links: expected array")
    for link in packet["case_links"]:
        fields(link, FIELDS["link"], "case link")
        cid = link["case_id"]
        require(cid in case_ids and cid not in links, "missing or duplicate case link")
        links.add(cid)
        identifiers(link["claim_ids"], set(claims), "claim links")
        require(link["relation"] in {"LEGAL_CONTEXT_NOT_CASE_ORACLE",
                                     "INSTRUMENT_SCOPE_QUESTION_ONLY"},
                "case link overstates source evidence")
        require(all(sources[claims[x]["source_id"]]["kind"] not in
                    {"LIVE_CATALOG", "PROPOSED_NOT_LAW"} for x in link["claim_ids"]),
                "cannot treat metadata or proposal as case authority")
    require(links == case_ids, "missing ExpertCase coverage")

    unresolved = unique(packet["unresolved"], "unresolved")
    require(len(unresolved) >= 3, "insufficient explicit verification gaps")
    for item in unresolved.values():
        fields(item, FIELDS["unresolved"], "unresolved")
        require(isinstance(item["question"], str) and item["question"].strip()
                and item["needs_specialist_review"] is True,
                "unresolved: missing review question")
        identifiers(item["source_ids"], set(sources), "unresolved sources")
    unresolved_sources = {x for item in unresolved.values() for x in item["source_ids"]}
    require({sid for sid, s in sources.items() if s["kind"] in
             {"LIVE_CATALOG", "PROPOSED_NOT_LAW", "AGENCY_PROCEDURE"}}
            <= unresolved_sources, "index/legislation gaps must remain explicit")



def validate_procedure_edition(edition: dict, packet: dict) -> None:
    """Reject a guessed full text or unjustified promotion of indexed evidence."""
    required = {"schema_version", "document_id", "source_id", "authority",
                "title_he", "official_pdf_url", "edition_label",
                "edition_date_basis", "reviewed_on", "evidence_level",
                "full_pdf_retrieved", "original_pdf_sha256",
                "current_revision_independently_confirmed", "expert_verified",
                "editorial_use", "index_supported_points", "unverified_questions",
                "review_boundary"}
    fields(edition, required, "procedure edition")
    source = next((x for x in packet["sources"]
                   if x["id"] == "raa_2025_check_procedure"), None)
    require(source is not None and edition["source_id"] == source["id"]
            and edition["official_pdf_url"] == source["url"]
            and source["access_level"] == "INDEX_EXCERPT_ONLY"
            and source["source_date"] is None,
            "procedure source or access-level mismatch")
    require(edition["schema_version"] == 1
            and edition["document_id"] == "raa_cheque_and_note_opening_2025_06_29"
            and edition["edition_label"] == "2025-06-29"
            and edition["edition_date_basis"] == "OFFICIAL_PDF_FILENAME_ONLY"
            and edition["reviewed_on"] == packet["prepared_on"]
            and edition["evidence_level"] == "OFFICIAL_SEARCH_INDEX_EXCERPTS_ONLY"
            and edition["full_pdf_retrieved"] is False
            and edition["original_pdf_sha256"] is None
            and edition["current_revision_independently_confirmed"] is False
            and edition["expert_verified"] is False
            and edition["editorial_use"] == "PROVISIONAL_RESEARCH_ONLY",
            "unverified procedure promoted beyond indexed-only evidence")
    points = unique(edition["index_supported_points"], "indexed points")
    require(set(points) == {"purpose", "eligible_holder", "timing"},
            "unexpected indexed coverage")
    for point in points.values():
        fields(point, {"id", "official_index_heading_he", "paraphrase",
                       "source_basis", "exact_pdf_page"}, "indexed point")
        require(point["source_basis"] == "INDEXED_PDF_SNIPPET"
                and point["exact_pdf_page"] is None
                and all(isinstance(point[k], str) and point[k].strip()
                        for k in ("official_index_heading_he", "paraphrase")),
                "indexed excerpt falsely claims primary text")
    questions = unique(edition["unverified_questions"], "procedure gaps")
    require(set(questions) == {"security_cheque_specific_rules",
                              "version_currentness", "procedural_vs_substantive"}
            and all(x["status"] in {"NEEDS_FULL_PRIMARY_TEXT",
                                    "NEEDS_CURRENT_VERSION_CONFIRMATION",
                                    "NEEDS_INDEPENDENT_LEGAL_SOURCES"}
                    and isinstance(x["question"], str) and x["question"].strip()
                    for x in questions.values())
            and isinstance(edition["review_boundary"], str)
            and bool(edition["review_boundary"].strip()),
            "procedure gaps or review boundary missing")


def read(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink()
            and path.stat().st_size < 300_000, "unsafe or oversized JSON")
    def no_duplicates(pairs: list[tuple[str, object]]) -> dict:
        result: dict = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON field")
            result[key] = value
        return result
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=no_duplicates)
    require(isinstance(value, dict), "root must be JSON object")
    return value


if __name__ == "__main__":
    packet = read(BASE / "source_audit_packet_v1.json")
    expert_cases = read(BASE / "expert_cases_v1.json")
    overlay = read(ROOT / "docs/statutory/ISRAEL_RENTAL_AND_LOAN_AMENDMENT_2026_V1.json")
    validate(packet, expert_cases, overlay)
    procedure = read(BASE / "authority_cheque_procedure_2025_06_29_v1.json")
    validate_procedure_edition(procedure, packet)
    print(f"Source audit: {len(packet['sources'])} leads, "
          f"{len(packet['claims'])} limited propositions, "
          f"{len(packet['case_links'])} case links; NOT legally verified.")
