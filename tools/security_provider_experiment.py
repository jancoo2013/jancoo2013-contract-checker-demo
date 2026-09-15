from __future__ import annotations
import json
import math
import os
from pathlib import Path
import re
import time
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "research/question_engine/smart_analysis_corpus_v1.json"
DEFAULT_MODEL = "gemini-3.6-flash"
FALLBACK_MODEL = "gemini-3.5-flash"
MODEL = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
if MODEL not in {DEFAULT_MODEL, FALLBACK_MODEL}:
    raise RuntimeError("Unsupported GEMINI_MODEL; use gemini-3.6-flash or gemini-3.5-flash")
MODEL_ROUTE = tuple(dict.fromkeys((MODEL, FALLBACK_MODEL)))
REQUEST_SPACING_SECONDS = 30
REQUEST_TIMEOUT_SECONDS = 120
MAX_ATTEMPTS_PER_MODEL = 2
MAX_TOTAL_ATTEMPTS = 4
MAX_ERROR_BODY_BYTES = 16384
MAX_RESPONSE_BODY_BYTES = 262144
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


class GlobalProviderError(RuntimeError):
    pass


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
        "properties": {key: {"type": "string", "enum": values}
                       for key, values in STATE_VALUES.items()},
        "required": list(STATE_VALUES),
        "additionalProperties": False,
    }
    value_schema = {"anyOf": [
        {"type": "string"}, {"type": "number"}, {"type": "boolean"},
        {"type": "array", "items": {"type": "string"}}, {"type": "null"},
    ]}
    assertion_schema = {
        "type": "object",
        "properties": {
            "question_id": {"type": "string"}, "mechanism_id": {"type": ["string", "null"]},
            "field": {"type": "string"}, "value": value_schema, "state": state_schema,
            "refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        },
        "required": ["question_id", "mechanism_id", "field", "value", "state", "refs"],
        "additionalProperties": False,
    }
    resolution_schema = {"anyOf": [
        {"type": "null"},
        {"type": "object", "properties": {
            "outcome": {"type": "string", "enum": ["CONFIRMED", "NARROWED", "CLEARED"]},
            "reviewed_refs": {"type": "array", "items": {"type": "string"}},
        }, "required": ["outcome", "reviewed_refs"], "additionalProperties": False},
    ]}
    return {
        "type": "object",
        "properties": {
            "assertions": {"type": "array", "items": assertion_schema,
                           "minItems": assertion_count, "maxItems": assertion_count},
            "resolution": resolution_schema,
        },
        "required": ["assertions", "resolution"], "additionalProperties": False,
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


def _reject_json_constant(value):
    raise ValueError(f"non-finite JSON constant: {value}")


def parse_provider_text(text):
    try:
        parsed = json.loads(text, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, ValueError):
        raise RuntimeError("invalid_json") from None
    if not isinstance(parsed, dict):
        raise RuntimeError("root_not_object")
    return parsed


def validate_provider_output(actual, assertion_count):
    if set(actual) != {"assertions", "resolution"}:
        raise RuntimeError("root_schema")
    assertions = actual["assertions"]
    if not isinstance(assertions, list) or len(assertions) != assertion_count:
        raise RuntimeError("assertion_count")
    required = {"question_id", "mechanism_id", "field", "value", "state", "refs"}
    for item in assertions:
        if not isinstance(item, dict) or set(item) != required:
            raise RuntimeError("assertion_schema")
        if not isinstance(item["question_id"], str) or not isinstance(item["field"], str):
            raise RuntimeError("assertion_identifiers")
        if item["mechanism_id"] is not None and not isinstance(item["mechanism_id"], str):
            raise RuntimeError("mechanism_id")
        state = item["state"]
        if not isinstance(state, dict) or set(state) != set(STATE_VALUES):
            raise RuntimeError("state_schema")
        if any(state[key] not in STATE_VALUES[key] for key in STATE_VALUES):
            raise RuntimeError("state_value")
        refs = item["refs"]
        if not isinstance(refs, list) or not refs or not all(isinstance(x, str) for x in refs):
            raise RuntimeError("refs_schema")
        value = item["value"]
        if isinstance(value, float) and not math.isfinite(value):
            raise RuntimeError("value_non_finite")
        if not (value is None or isinstance(value, (str, int, float, bool))
                or (isinstance(value, list) and all(isinstance(x, str) for x in value))):
            raise RuntimeError("value_schema")
    resolution = actual["resolution"]
    if resolution is not None:
        if not isinstance(resolution, dict) or set(resolution) != {"outcome", "reviewed_refs"}:
            raise RuntimeError("resolution_schema")
        outcome = resolution["outcome"]
        if not isinstance(outcome, str) or outcome not in {"CONFIRMED", "NARROWED", "CLEARED"}:
            raise RuntimeError("resolution_outcome")
        refs = resolution["reviewed_refs"]
        if not isinstance(refs, list) or not all(isinstance(x, str) for x in refs):
            raise RuntimeError("resolution_refs")
    return actual


def parse_error_payload(raw):
    text = raw.decode("utf-8", "replace")
    try:
        payload = json.loads(text, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, ValueError):
        payload = None
    return text, payload


def error_details(payload):
    if not isinstance(payload, dict):
        return []
    error_obj = payload.get("error")
    if not isinstance(error_obj, dict):
        return []
    details = error_obj.get("details")
    return details if isinstance(details, list) else []


def quota_violations(payload):
    violations = []
    for detail in error_details(payload):
        if not isinstance(detail, dict) or not str(detail.get("@type", "")).endswith("QuotaFailure"):
            continue
        values = detail.get("violations")
        if isinstance(values, list):
            violations.extend(x for x in values if isinstance(x, dict))
    return violations


def is_daily_quota_error(detail, payload=None):
    tokens = (
        "generaterequestsperdayperprojectpermodel",
        "requestsperdayperprojectpermodel",
        "generatetokensperdayperprojectpermodel",
        "tokensperdayperprojectpermodel",
    )
    markers = []
    for violation in quota_violations(payload):
        markers += [str(violation.get("quotaId", "")), str(violation.get("quotaMetric", ""))]
    if any(token in marker.lower().replace("_", "") for marker in markers for token in tokens):
        return True
    normalized = detail.lower().replace("_", "")
    return any(token in normalized for token in tokens)


def retry_info_seconds(payload):
    for detail in error_details(payload):
        if not isinstance(detail, dict) or not str(detail.get("@type", "")).endswith("RetryInfo"):
            continue
        match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)s", str(detail.get("retryDelay", "")))
        if match:
            value = float(match.group(1))
            if math.isfinite(value) and value >= 0:
                return value
    return None


def retry_wait_seconds(detail, headers, attempt, payload=None):
    hints = []
    retry_info = retry_info_seconds(payload)
    if retry_info is not None:
        hints.append(retry_info + 1.0)
    if headers:
        try:
            value = float(headers.get("Retry-After", ""))
            if math.isfinite(value) and value >= 0:
                hints.append(value)
        except (TypeError, ValueError):
            pass
    match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", detail, re.IGNORECASE)
    if match:
        value = float(match.group(1)) + 1.0
        if math.isfinite(value):
            hints.append(value)
    if hints:
        return min(max(max(hints), 1.0), 120.0)
    return min(15.0 * (2 ** (attempt - 1)), 60.0)


def is_timeout_error(exc):
    reason = getattr(exc, "reason", exc)
    return isinstance(reason, TimeoutError) or "timed out" in str(reason).lower()


def next_model(current_model, unavailable_models=()):
    try:
        index = MODEL_ROUTE.index(current_model)
    except ValueError:
        return None
    return next((model for model in MODEL_ROUTE[index + 1:] if model not in unavailable_models), None)


def request_for_model(model, key, body):
    return request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )


def read_provider_envelope(response):
    raw = response.read(MAX_RESPONSE_BODY_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BODY_BYTES:
        raise RuntimeError("provider_envelope_size")
    try:
        envelope = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise RuntimeError("provider_envelope_json") from None
    if not isinstance(envelope, dict):
        raise RuntimeError("provider_envelope_shape")
    return envelope


def extract_provider_text(envelope):
    try:
        candidates = envelope["candidates"]
        if not isinstance(candidates, list) or not candidates:
            raise TypeError
        content = candidates[0]["content"]
        parts = content["parts"]
        if not isinstance(parts, list) or not parts:
            raise TypeError
        texts = []
        for part in parts:
            if not isinstance(part, dict) or not isinstance(part.get("text"), str):
                raise TypeError
            texts.append(part["text"])
        text = "".join(texts)
        if not text:
            raise TypeError
        return text
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("provider_envelope_shape") from None


def record_attempt(attempts, case_id, model, attempt_no, status, started,
                   failure_class=None, http_code=None, wait_seconds=None):
    entry = {
        "case_id": case_id, "model": model, "attempt": attempt_no,
        "status": status, "duration_ms": round((time.monotonic() - started) * 1000),
    }
    if failure_class:
        entry["failure_class"] = failure_class
    if http_code is not None:
        entry["http_code"] = http_code
    if wait_seconds is not None:
        entry["wait_seconds"] = round(wait_seconds, 2)
    attempts.append(entry)
    return entry


def call_gemini(key, prompt, assertion_count, unavailable_models=None, attempts=None, case_id="unknown"):
    unavailable_models = unavailable_models if unavailable_models is not None else set()
    attempts = attempts if attempts is not None else []
    available = [model for model in MODEL_ROUTE if model not in unavailable_models]
    if not available:
        raise RuntimeError("no_available_models")
    body = request_body(prompt, assertion_count)
    current_model = available[0]
    per_model_attempts = {model: 0 for model in MODEL_ROUTE}
    total_attempts = 0

    while total_attempts < MAX_TOTAL_ATTEMPTS:
        if per_model_attempts[current_model] >= MAX_ATTEMPTS_PER_MODEL:
            alternate = next_model(current_model, unavailable_models)
            if not alternate:
                raise RuntimeError("attempt_budget_exhausted")
            current_model = alternate
            continue
        per_model_attempts[current_model] += 1
        total_attempts += 1
        attempt_no = total_attempts
        started = time.monotonic()
        req = request_for_model(current_model, key, body)
        try:
            with request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                try:
                    envelope = read_provider_envelope(response)
                    actual = validate_provider_output(
                        parse_provider_text(extract_provider_text(envelope)), assertion_count)
                except RuntimeError as exc:
                    code = str(exc)
                    failure = code if code.startswith("provider_") else f"model_output_{code}"
                    record_attempt(attempts, case_id, current_model, attempt_no, "ERROR", started, failure)
                    alternate = next_model(current_model, unavailable_models)
                    if alternate:
                        current_model = alternate
                        continue
                    if per_model_attempts[current_model] < MAX_ATTEMPTS_PER_MODEL:
                        continue
                    raise RuntimeError(code) from None
            record_attempt(attempts, case_id, current_model, attempt_no, "OK", started)
            return actual, current_model
        except error.HTTPError as exc:
            raw = exc.read(MAX_ERROR_BODY_BYTES)
            detail, payload = parse_error_payload(raw)
            detail = detail.replace(key, "[REDACTED]")
            alternate = next_model(current_model, unavailable_models)
            if exc.code in {400, 401, 403}:
                record_attempt(attempts, case_id, current_model, attempt_no, "ERROR", started,
                               "global_provider_error", exc.code)
                raise GlobalProviderError(f"Gemini global provider error HTTP {exc.code}") from None
            if exc.code == 429 and is_daily_quota_error(detail, payload):
                record_attempt(attempts, case_id, current_model, attempt_no, "ERROR", started,
                               "daily_quota", exc.code)
                unavailable_models.add(current_model)
                alternate = next_model(current_model, unavailable_models)
                if alternate:
                    print(f"Gemini daily quota exhausted on {current_model}; switching to {alternate}")
                    current_model = alternate
                    continue
                raise RuntimeError(f"daily_quota:{current_model}") from None
            if exc.code == 404:
                record_attempt(attempts, case_id, current_model, attempt_no, "ERROR", started,
                               "model_unavailable", exc.code)
                unavailable_models.add(current_model)
                alternate = next_model(current_model, unavailable_models)
                if alternate:
                    print(f"Gemini unavailable on {current_model}; switching to {alternate}")
                    current_model = alternate
                    continue
                raise RuntimeError(f"model_unavailable:{current_model}") from None
            if exc.code == 503:
                entry = record_attempt(attempts, case_id, current_model, attempt_no, "ERROR", started,
                                       "provider_overloaded", exc.code)
                if alternate:
                    print(f"Gemini HTTP 503 on {current_model}; switching to {alternate}")
                    current_model = alternate
                    continue
                if per_model_attempts[current_model] < MAX_ATTEMPTS_PER_MODEL:
                    wait = retry_wait_seconds(detail, exc.headers, per_model_attempts[current_model], payload)
                    entry["wait_seconds"] = round(wait, 2)
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"provider_overloaded:{current_model}") from None
            if exc.code == 429:
                wait = retry_wait_seconds(detail, exc.headers, per_model_attempts[current_model], payload)
                record_attempt(attempts, case_id, current_model, attempt_no, "ERROR", started,
                               "rate_limit", exc.code, wait)
                if per_model_attempts[current_model] < MAX_ATTEMPTS_PER_MODEL:
                    print(f"Gemini HTTP 429 on {current_model}; retrying in {wait:.0f}s")
                    time.sleep(wait)
                    continue
                if alternate:
                    current_model = alternate
                    continue
                raise RuntimeError(f"rate_limit:{current_model}") from None
            record_attempt(attempts, case_id, current_model, attempt_no, "ERROR", started,
                           "http_error", exc.code)
            raise RuntimeError(f"Gemini HTTP {exc.code} on {current_model}: {detail}") from None
        except error.URLError as exc:
            if not is_timeout_error(exc):
                record_attempt(attempts, case_id, current_model, attempt_no, "ERROR", started,
                               "network_error")
                raise RuntimeError(f"Gemini network error on {current_model}: {exc.reason}") from None
            record_attempt(attempts, case_id, current_model, attempt_no, "ERROR", started, "timeout")
            alternate = next_model(current_model, unavailable_models)
            if alternate:
                print(f"Gemini network timeout on {current_model}; switching to {alternate}")
                current_model = alternate
                continue
            if per_model_attempts[current_model] < MAX_ATTEMPTS_PER_MODEL:
                continue
            raise RuntimeError(f"timeout:{current_model}") from None
        except TimeoutError:
            record_attempt(attempts, case_id, current_model, attempt_no, "ERROR", started, "timeout")
            alternate = next_model(current_model, unavailable_models)
            if alternate:
                print(f"Gemini read timeout on {current_model}; switching to {alternate}")
                current_model = alternate
                continue
            if per_model_attempts[current_model] < MAX_ATTEMPTS_PER_MODEL:
                continue
            raise RuntimeError(f"timeout:{current_model}") from None
    raise RuntimeError("global_attempt_cap")

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


def build_summary(results, by_id, attempts):
    scored = [x["score"] for x in results if x["status"] == "OK"]
    resolution_results = [x for x in results if x["status"] == "OK" and by_id[x["case_id"]].get("resolution")]
    attempts_by_model = {model: sum(x["model"] == model for x in attempts) for model in MODEL_ROUTE}
    successes_by_model = {model: sum(x.get("model_used") == model for x in results) for model in MODEL_ROUTE}
    failure_classes = {}
    for item in attempts:
        if item.get("failure_class"):
            failure_classes[item["failure_class"]] = failure_classes.get(item["failure_class"], 0) + 1
    return {
        "cases_requested": len(CASES), "cases_completed": len(scored),
        "assertions_requested_total": sum(len(by_id[x]["assertions"]) for x in CASES),
        "fallback_cases": sum(x.get("model_used") not in (None, MODEL) for x in results),
        "attempts_total": len(attempts), "attempts_by_model": attempts_by_model,
        "successes_by_model": successes_by_model, "failure_classes": failure_classes,
        "assertions_exact": sum(x["assertions_exact"] for x in scored),
        "assertions_total": sum(x["assertions_total"] for x in scored),
        "value_matches": sum(x["value_matches"] for x in scored),
        "state_matches": sum(x["state_matches"] for x in scored),
        "refs_matches": sum(x["refs_matches"] for x in scored),
        "resolution_matches": sum(bool(x["score"]["resolution_ok"]) for x in resolution_results),
        "resolution_cases": len(resolution_results),
        "hard_failures": sum(len(x["hard_failures"]) for x in scored),
    }


def redact_secrets(value, secrets):
    secrets = tuple(x for x in secrets if x)
    if isinstance(value, dict):
        return {k: redact_secrets(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_secrets(v, secrets) for v in value]
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, "[REDACTED]")
    return value


def render(report):
    s = report["summary"]
    route = " → ".join(report["model_route"])
    lines = [
        "Gemini security provider experiment", f"Model route: {route}",
        f"Run status: {report['status']}", f"Unavailable models: {report['unavailable_models']}",
        f"Provider attempts: {s['attempts_total']} {s['attempts_by_model']}",
        f"Successful cases by model: {s['successes_by_model']}",
        f"Provider failure classes: {s['failure_classes']}",
        f"Cases: {s['cases_completed']}/{s['cases_requested']}",
        f"Assertion coverage: {s['assertions_total']}/{s['assertions_requested_total']}",
        f"Exact assertions: {s['assertions_exact']}/{s['assertions_total']}",
        f"Values: {s['value_matches']}/{s['assertions_total']}",
        f"States: {s['state_matches']}/{s['assertions_total']}",
        f"Evidence refs: {s['refs_matches']}/{s['assertions_total']}",
        f"Resolutions: {s['resolution_matches']}/{s['resolution_cases']}",
        f"Hard failures: {s['hard_failures']}", "", "Per case:",
    ]
    for item in report["results"]:
        if item["status"] == "ERROR":
            lines.append(f"- {item['case_id']}: ERROR — {item['error']}; attempts={len(item.get('attempts', []))}")
        else:
            x = item["score"]
            lines.append(f"- {item['case_id']}: {x['assertions_exact']}/{x['assertions_total']} exact; "
                         f"model={item['model_used']}; attempts={len(item.get('attempts', []))}; "
                         f"resolution={'OK' if x['resolution_ok'] else 'FAIL'}; hard={len(x['hard_failures'])}")
    return "\n".join(lines) + "\n"


def make_report(results, by_id, unavailable_models, attempts, started, status):
    return {
        "experiment": "question-engine-security-provider-experiment-v1",
        "model": MODEL, "model_route": list(MODEL_ROUTE),
        "fallback_model": MODEL_ROUTE[1] if len(MODEL_ROUTE) > 1 else None,
        "status": status, "duration_seconds": round(time.time() - started, 2),
        "unavailable_models": sorted(unavailable_models),
        "summary": build_summary(results, by_id, attempts),
        "attempts": list(attempts), "results": results,
    }


def persist_report(json_path, results, by_id, unavailable_models, attempts, started, status, key):
    report = redact_secrets(
        make_report(results, by_id, unavailable_models, attempts, started, status), (key,))
    json_text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    txt = json_path.with_suffix(".txt")
    txt_text = render(report)
    json_tmp = json_path.with_suffix(json_path.suffix + ".tmp")
    txt_tmp = txt.with_suffix(txt.suffix + ".tmp")
    json_tmp.write_text(json_text, encoding="utf-8")
    txt_tmp.write_text(txt_text, encoding="utf-8")
    txt_tmp.replace(txt)
    json_tmp.replace(json_path)
    return report, txt


def run():
    key, key_path = load_key()
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    by_id = {x["case_id"]: x for x in corpus["cases"]}
    missing = [x for x in CASES if x not in by_id or by_id[x].get("domain") != "security"]
    if missing:
        raise RuntimeError(f"Corpus selection invalid: {', '.join(missing)}")
    folders = desktop_dirs()
    out = key_path.parent if key_path else (folders[0] if folders else ROOT)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"security_provider_experiment_{time.strftime('%Y%m%d_%H%M%S')}.json"
    results, attempts, unavailable_models, started = [], [], set(), time.time()
    persist_report(json_path, results, by_id, unavailable_models, attempts, started, "IN_PROGRESS", key)
    status = "COMPLETED"

    for n, case_id in enumerate(CASES, 1):
        if not any(model not in unavailable_models for model in MODEL_ROUTE):
            status = "ABORTED_ROUTE_EXHAUSTED"
            break
        if n > 1:
            time.sleep(REQUEST_SPACING_SECONDS)
        case = by_id[case_id]
        print(f"[{n}/{len(CASES)}] {case_id}")
        before = len(attempts)
        try:
            actual, model_used = call_gemini(
                key, build_prompt(case), len(case["assertions"]), unavailable_models, attempts, case_id)
            results.append({"case_id": case_id, "status": "OK", "model_used": model_used,
                            "attempts": attempts[before:], "score": score_case(case, actual), "actual": actual})
        except GlobalProviderError as exc:
            results.append({"case_id": case_id, "status": "ERROR", "attempts": attempts[before:],
                            "error": str(exc)})
            status = "ABORTED_GLOBAL_PROVIDER_ERROR"
            persist_report(json_path, results, by_id, unavailable_models, attempts, started, status, key)
            raise
        except RuntimeError as exc:
            results.append({"case_id": case_id, "status": "ERROR", "attempts": attempts[before:],
                            "error": str(exc).replace(key, "[REDACTED]")})
        except Exception as exc:
            results.append({"case_id": case_id, "status": "ERROR", "attempts": attempts[before:],
                            "error": f"internal_error:{type(exc).__name__}"})
            status = "ABORTED_INTERNAL_ERROR"
            persist_report(json_path, results, by_id, unavailable_models, attempts, started, status, key)
            break
        persist_report(json_path, results, by_id, unavailable_models, attempts, started, "IN_PROGRESS", key)

    return persist_report(json_path, results, by_id, unavailable_models, attempts, started, status, key)


def main():
    try:
        report, txt = run()
    except (RuntimeError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"Experiment failed before report initialization: {type(exc).__name__}")
        return 1
    print(render(report))
    if os.name == "nt":
        os.startfile(txt)  # type: ignore[attr-defined]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
