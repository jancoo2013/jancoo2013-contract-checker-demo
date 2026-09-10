from __future__ import annotations
import json
import os
from pathlib import Path
import re
import time
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "research/question_engine/smart_analysis_corpus_v1.json"
DEFAULT_MODEL = "gemini-3.6-flash"
FALLBACK_MODEL = "gemini-3.5-flash"
MODEL = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
REQUEST_SPACING_SECONDS = 30
REQUEST_TIMEOUT_SECONDS = 120
MAX_ATTEMPTS = 4
RETRYABLE_HTTP_CODES = {429, 503}
CASES = (
    "security_broad_trigger_confirmed",
    "security_broad_trigger_narrowed_by_notice_cure",
    "security_generic_trigger_cleared_by_specific_limit",
    "multiple_security_instruments_keep_identity",
    "missing_security_instrument_dependency",
    "executed_blank_security_amount",
    "handwriting_dependency_without_guessing",
    "security_mechanism_split_with_distractors",
    "security_recovery_overlap_cumulative",
    "referenced_security_document_present_without_amount",
)
DEFAULT_STATE = {
    "presence": "PRESENT", "value": "PROVIDED",
    "evidence": "SUFFICIENT", "source": "CLEAR",
}
STATE_VALUES = {
    "presence": ["PRESENT", "ABSENT", "UNKNOWN"],
    "value": ["PROVIDED", "OMITTED", "BLANK", "UNKNOWN"],
    "evidence": ["SUFFICIENT", "HANDWRITING_DEPENDENCY", "MISSING_DEPENDENCY", "UNREADABLE"],
    "source": ["CLEAR", "AMBIGUOUS", "CONTRADICTORY"],
}


def desktop_dirs():
    bases = [Path.home()]
    bases += [Path(v) for k in ("USERPROFILE", "OneDrive", "OneDriveConsumer")
              if (v := os.environ.get(k))]
    return list(dict.fromkeys(
        base / name for base in bases for name in ("Desktop", "Рабочий стол")
    ))


def load_key():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key, None
    for folder in desktop_dirs():
        path = folder / ".env.local"
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            if raw.strip().startswith("GEMINI_API_KEY="):
                key = raw.split("=", 1)[1].strip().strip("\"'")
                if key:
                    return key, path
    raise RuntimeError("GEMINI_API_KEY not found. Put .env.local on the Desktop.")


def target_assertions(case):
    return [{
        "question_id": item["question_id"],
        "mechanism_id": item.get("mechanism_id"),
        "field": item["field"],
    } for item in case["assertions"]]


def case_input(case):
    data = {
        "lifecycle": case["lifecycle"], "clauses": case["clauses"],
        "complete_for": case.get("complete_for", []),
        "documents": case.get("documents", []),
        "redactions": case.get("redactions", []),
        "target_assertions": target_assertions(case),
    }
    if case.get("candidate"):
        data["candidate"] = case["candidate"]
    return data


def build_prompt(case):
    return json.dumps({
        "task": "Read sanitized Hebrew lease evidence and answer only the requested security assertion slots.",
        "rules": [
            "Use only supplied clauses/package/redaction metadata and declared complete scope.",
            "Do not use outside law and do not give advice.",
            "Never guess handwriting or missing document contents.",
            "Return exactly one assertion for every target_assertions item and no others.",
            "Copy question_id, mechanism_id and field from each target_assertions item exactly; never merge repeated fields across mechanisms.",
            "Keep instruments separate: first security instrument=security_1, second=security_2; first rent cheque=rent_cheque_1.",
            "Use minimal direct refs for each returned field. Resolution reviewed_refs may include all clauses reviewed for the candidate.",
            "Use only supplied refs. @scope may support absence only for questions in complete_for.",
            "Durations and deadlines are integer day counts such as 14, never ISO-8601 strings such as P14D.",
            "A known boolean false is still a PROVIDED value. state.presence describes whether evidence establishes the requested fact/status, not whether its boolean value is true.",
            "Use state.value=BLANK only for an explicit blank in the supplied source; return value=null and keep state.presence=PRESENT when that blank is visible.",
            "If handwriting redaction blocks a requested value, return value=null, state.value=UNKNOWN, state.evidence=HANDWRITING_DEPENDENCY, and cite the source clause plus the relevant redaction ref.",
            "If a referenced document is marked MISSING and a requested value depends on it, return value=null, state.value=UNKNOWN, state.evidence=MISSING_DEPENDENCY, and cite the source clause plus the package-document ref.",
            "Use state.presence=ABSENT with state.value=OMITTED only when the declared complete scope establishes that the requested fact is absent.",
            "Return all four state axes explicitly for every assertion.",
            "If candidate exists, resolve exactly that claim as CONFIRMED, NARROWED or CLEARED.",
            "Normalize annex ג as annex_c and ד as annex_d.",
            "Use canonical values: security_cheque, promissory_note, rent_cheque; any_contract_breach, unpaid_rent_only, unpaid_debt; cumulative, alternative, mixed, unclear.",
        ],
        "state_values": STATE_VALUES,
        "input": case_input(case),
    }, ensure_ascii=False, separators=(",", ":"))


def response_schema(assertion_count):
    state_schema = {
        "type": "object",
        "properties": {
            key: {"type": "string", "enum": values}
            for key, values in STATE_VALUES.items()
        },
        "required": list(STATE_VALUES),
        "additionalProperties": False,
    }
    value_schema = {
        "anyOf": [
            {"type": "string"},
            {"type": "number"},
            {"type": "boolean"},
            {"type": "array", "items": {"type": "string"}},
            {"type": "null"},
        ]
    }
    assertion_schema = {
        "type": "object",
        "properties": {
            "question_id": {"type": "string"},
            "mechanism_id": {"type": ["string", "null"]},
            "field": {"type": "string"},
            "value": value_schema,
            "state": state_schema,
            "refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        },
        "required": ["question_id", "mechanism_id", "field", "value", "state", "refs"],
        "additionalProperties": False,
    }
    resolution_schema = {
        "anyOf": [
            {"type": "null"},
            {
                "type": "object",
                "properties": {
                    "outcome": {"type": "string", "enum": ["CONFIRMED", "NARROWED", "CLEARED"]},
                    "reviewed_refs": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["outcome", "reviewed_refs"],
                "additionalProperties": False,
            },
        ]
    }
    return {
        "type": "object",
        "properties": {
            "assertions": {
                "type": "array", "items": assertion_schema,
                "minItems": assertion_count, "maxItems": assertion_count,
            },
            "resolution": resolution_schema,
        },
        "required": ["assertions", "resolution"],
        "additionalProperties": False,
    }


def request_body(prompt, assertion_count):
    return {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 3000,
            "responseMimeType": "application/json",
            "responseJsonSchema": response_schema(assertion_count),
        },
    }


def parse_provider_text(text):
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        raise RuntimeError("Malformed Gemini JSON: invalid_json") from None
    if not isinstance(parsed, dict):
        raise RuntimeError("Malformed Gemini JSON: root_not_object")
    return parsed


def retry_wait_seconds(detail, headers, attempt):
    if headers:
        raw = headers.get("Retry-After")
        try:
            if raw:
                return min(max(float(raw), 1.0), 120.0)
        except (TypeError, ValueError):
            pass
    match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", detail, re.IGNORECASE)
    if match:
        return min(max(float(match.group(1)) + 1.0, 1.0), 120.0)
    return min(15.0 * (2 ** (attempt - 1)), 60.0)


def is_timeout_error(exc):
    reason = getattr(exc, "reason", exc)
    return isinstance(reason, TimeoutError) or "timed out" in str(reason).lower()


def request_for_model(model, key, body):
    return request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )


def call_gemini(key, prompt, assertion_count):
    body = request_body(prompt, assertion_count)
    current_model = MODEL
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = request_for_model(current_model, key, body)
        try:
            with request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                envelope = json.load(response)
            break
        except error.HTTPError as exc:
            detail = exc.read(1200).decode("utf-8", "replace").replace(key, "[REDACTED]")
            if exc.code == 503 and current_model != FALLBACK_MODEL and attempt < MAX_ATTEMPTS:
                print(f"Gemini HTTP 503 on {current_model}; switching to {FALLBACK_MODEL}")
                current_model = FALLBACK_MODEL
                continue
            if exc.code in RETRYABLE_HTTP_CODES and attempt < MAX_ATTEMPTS:
                wait = retry_wait_seconds(detail, exc.headers, attempt)
                print(f"Gemini HTTP {exc.code} on {current_model}; retrying in {wait:.0f}s "
                      f"({attempt}/{MAX_ATTEMPTS - 1} retries used)")
                time.sleep(wait)
                continue
            raise RuntimeError(f"Gemini HTTP {exc.code} on {current_model}: {detail}") from None
        except error.URLError as exc:
            if is_timeout_error(exc) and current_model != FALLBACK_MODEL and attempt < MAX_ATTEMPTS:
                print(f"Gemini network timeout on {current_model}; switching to {FALLBACK_MODEL}")
                current_model = FALLBACK_MODEL
                continue
            if is_timeout_error(exc) and attempt < MAX_ATTEMPTS:
                wait = retry_wait_seconds("", None, attempt)
                print(f"Gemini network timeout on {current_model}; retrying in {wait:.0f}s "
                      f"({attempt}/{MAX_ATTEMPTS - 1} retries used)")
                time.sleep(wait)
                continue
            raise RuntimeError(f"Gemini network error on {current_model}: {exc.reason}") from None
        except TimeoutError as exc:
            if current_model != FALLBACK_MODEL and attempt < MAX_ATTEMPTS:
                print(f"Gemini read timeout on {current_model}; switching to {FALLBACK_MODEL}")
                current_model = FALLBACK_MODEL
                continue
            if attempt < MAX_ATTEMPTS:
                wait = retry_wait_seconds("", None, attempt)
                print(f"Gemini read timeout on {current_model}; retrying in {wait:.0f}s "
                      f"({attempt}/{MAX_ATTEMPTS - 1} retries used)")
                time.sleep(wait)
                continue
            raise RuntimeError(
                f"Gemini timeout on {current_model} after {MAX_ATTEMPTS} total attempts: {exc}"
            ) from None
    else:
        raise RuntimeError("Gemini request retry loop ended unexpectedly")
    try:
        text = "".join(p.get("text", "") for p in envelope["candidates"][0]["content"]["parts"])
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f"Malformed Gemini response envelope from {current_model}") from None
    return parse_provider_text(text), current_model


def canon(value):
    if isinstance(value, list):
        return sorted(value, key=lambda x: json.dumps(x, sort_keys=True))
    return value


def score_case(case, actual):
    if not isinstance(actual, dict):
        return {"assertions_exact": 0, "assertions_total": len(case["assertions"]),
                "value_matches": 0, "state_matches": 0, "refs_matches": 0,
                "resolution_ok": False, "hard_failures": ["invalid_root"]}
    allowed = {x["ref"] for x in case["clauses"]} | {"@scope"}
    allowed |= {x["ref"] for n in ("documents", "redactions") for x in case.get(n, [])}
    got, hard = {}, []
    assertions = actual.get("assertions", [])
    if not isinstance(assertions, list):
        assertions, hard = [], ["assertions_not_list"]
    for item in assertions:
        if not isinstance(item, dict):
            hard.append("assertion_not_object")
            continue
        key = (item.get("question_id"), item.get("mechanism_id"), item.get("field"))
        if key in got:
            hard.append("duplicate_assertion")
        got[key] = item
        refs = item.get("refs", [])
        if not isinstance(refs, list) or not set(refs).issubset(allowed):
            hard.append("unsupported_ref")
    exact = values = states = refs_ok = 0
    expected_keys = set()
    for want in case["assertions"]:
        key = (want["question_id"], want.get("mechanism_id"), want["field"])
        expected_keys.add(key)
        item = got.get(key)
        state = dict(DEFAULT_STATE)
        state.update(want.get("state", {}))
        v_ok = item is not None and canon(item.get("value")) == canon(want.get("expected"))
        s_ok = item is not None and item.get("state") == state
        refs = item.get("refs", []) if item else []
        r_ok = isinstance(refs, list) and sorted(refs) == sorted(want.get("refs", []))
        values += v_ok
        states += s_ok
        refs_ok += r_ok
        exact += v_ok and s_ok and r_ok
        if state["evidence"] in {"HANDWRITING_DEPENDENCY", "MISSING_DEPENDENCY"}:
            if item is not None and item.get("value") is not None:
                hard.append("guessed_unavailable_value")
    if any(key not in expected_keys for key in got):
        hard.append("unexpected_assertion")
    want_res, got_res = case.get("resolution"), actual.get("resolution")
    if want_res is None:
        res_ok = got_res in (None, {})
    else:
        res_ok = (
            isinstance(got_res, dict)
            and got_res.get("outcome") == want_res["outcome"]
            and sorted(got_res.get("reviewed_refs", [])) == sorted(want_res["reviewed_refs"])
        )
    return {
        "assertions_exact": exact, "assertions_total": len(case["assertions"]),
        "value_matches": values, "state_matches": states, "refs_matches": refs_ok,
        "resolution_ok": res_ok, "hard_failures": sorted(set(hard)),
    }


def render(report):
    s = report["summary"]
    lines = [
        "Gemini security provider experiment", f"Primary model: {report['model']}",
        f"Fallback model: {report['fallback_model']}",
        f"Fallback cases: {s['fallback_cases']}",
        f"Cases: {s['cases_completed']}/{s['cases_requested']}",
        f"Exact assertions: {s['assertions_exact']}/{s['assertions_total']}",
        f"Values: {s['value_matches']}/{s['assertions_total']}",
        f"States: {s['state_matches']}/{s['assertions_total']}",
        f"Evidence refs: {s['refs_matches']}/{s['assertions_total']}",
        f"Resolutions: {s['resolution_matches']}/{s['resolution_cases']}",
        f"Hard failures: {s['hard_failures']}", "", "Per case:",
    ]
    for item in report["results"]:
        if item["status"] == "ERROR":
            lines.append(f"- {item['case_id']}: ERROR — {item['error']}")
        else:
            x = item["score"]
            lines.append(f"- {item['case_id']}: {x['assertions_exact']}/{x['assertions_total']} exact; "
                         f"model={item['model_used']}; "
                         f"resolution={'OK' if x['resolution_ok'] else 'FAIL'}; hard={len(x['hard_failures'])}")
    return "\n".join(lines) + "\n"


def run():
    key, key_path = load_key()
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    by_id = {x["case_id"]: x for x in corpus["cases"]}
    missing = [case_id for case_id in CASES if case_id not in by_id or by_id[case_id].get("domain") != "security"]
    if missing:
        raise RuntimeError(f"Corpus selection invalid: {', '.join(missing)}")
    results, started = [], time.time()
    for n, case_id in enumerate(CASES, 1):
        if n > 1:
            time.sleep(REQUEST_SPACING_SECONDS)
        case = by_id[case_id]
        print(f"[{n}/{len(CASES)}] {case_id}")
        try:
            actual, model_used = call_gemini(key, build_prompt(case), len(case["assertions"]))
            results.append({"case_id": case_id, "status": "OK", "model_used": model_used,
                            "score": score_case(case, actual), "actual": actual})
        except RuntimeError as exc:
            results.append({"case_id": case_id, "status": "ERROR",
                            "error": str(exc).replace(key, "[REDACTED]")})
    scored = [x["score"] for x in results if x["status"] == "OK"]
    resolution_results = [x for x in results if x["status"] == "OK" and by_id[x["case_id"]].get("resolution")]
    summary = {
        "cases_requested": len(CASES), "cases_completed": len(scored),
        "fallback_cases": sum(x.get("model_used") == FALLBACK_MODEL for x in results),
        "assertions_exact": sum(x["assertions_exact"] for x in scored),
        "assertions_total": sum(x["assertions_total"] for x in scored),
        "value_matches": sum(x["value_matches"] for x in scored),
        "state_matches": sum(x["state_matches"] for x in scored),
        "refs_matches": sum(x["refs_matches"] for x in scored),
        "resolution_matches": sum(bool(x["score"]["resolution_ok"]) for x in resolution_results),
        "resolution_cases": len(resolution_results),
        "hard_failures": sum(len(x["hard_failures"]) for x in scored),
    }
    folders = desktop_dirs()
    out = key_path.parent if key_path else (folders[0] if folders else ROOT)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    json_path = out / f"security_provider_experiment_{stamp}.json"
    report = {"experiment": "question-engine-security-provider-experiment-v1",
              "model": MODEL, "fallback_model": FALLBACK_MODEL,
              "duration_seconds": round(time.time() - started, 2),
              "summary": summary, "results": results}
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    txt = json_path.with_suffix(".txt")
    txt.write_text(render(report), encoding="utf-8")
    return report, txt


def main():
    try:
        report, txt = run()
    except (RuntimeError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"Experiment failed: {exc}")
        return 1
    print(render(report))
    if os.name == "nt":
        os.startfile(txt)  # type: ignore[attr-defined]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
