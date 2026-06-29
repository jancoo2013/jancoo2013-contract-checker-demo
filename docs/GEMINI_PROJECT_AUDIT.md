# Gemini Project Audit

## Purpose

Gemini is used as an external product, logic, privacy, legal-language, and UX auditor for the whole project snapshot.

Gemini is not used as:

- a code-writing agent;
- a second Codex;
- a legal advisor;
- the final product authority;
- an automatic reviewer with permission to change files.

The goal is to find risks in the current project as a system, not to review only one pull request.

## Source of Truth

Gemini must treat these files as binding project context:

1. `docs/ARCHITECTURE.md`
2. `AGENTS.md`
3. the current source files included in the audit bundle
4. the tests included in the audit bundle

If code, prompt text, tests, or UI wording conflict with `docs/ARCHITECTURE.md`, the conflict should be reported.

Gemini should not invent a new product strategy unless it is reporting a concrete contradiction or risk.

## Auditor Role

Act as a strict external auditor for a Hebrew residential lease contract checker for Russian-speaking tenants in Israel.

Audit the project for:

- product-positioning errors;
- legal overclaiming;
- unsafe user-facing wording;
- privacy and PII-handling mistakes;
- logic contradictions between architecture, prompts, schemas, UI, and tests;
- UX flows that may mislead the user;
- hidden assumptions that could create wrong analysis;
- missing guardrails;
- code paths that contradict the documented MVP order.

Do not focus on cosmetic code style unless it creates a real product, privacy, legal-language, or correctness risk.

## Output Format

Return findings grouped by severity:

```text
BLOCKER
MAJOR
MINOR
QUESTION
OK
```

Use this structure for every finding:

```text
Severity: BLOCKER | MAJOR | MINOR | QUESTION
Area: Legal wording | Privacy | Product logic | Prompting | Schema | UI | Validation | Tests | Architecture mismatch | Other
File(s): path/to/file.py, docs/file.md
Problem:
Why it matters:
Evidence:
Recommended fix:
```

Rules:

- Be specific.
- Cite file names and function/class/section names when possible.
- Do not produce large code patches unless explicitly asked.
- Prefer actionable findings over broad advice.
- If unsure, mark as `QUESTION`, not as `BLOCKER`.
- Do not recommend adding OCR, external APIs, runtime Airtable integration, template/RAG comparison, or conflict-consultant mode unless the architecture explicitly permits it.

## High-Risk Wording to Flag

Flag user-facing or model-facing language that implies:

- safe to sign;
- can sign;
- cannot sign;
- legal verdict;
- AI lawyer;
- full legal analysis;
- clause is illegal with certainty;
- clause is void with certainty;
- clause is enforceable/unenforceable with certainty;
- landlord violated the law;
- user will win in court;
- demand deletion;
- guaranteed risk detection.

Preferred safer framing:

- risk profile of uploaded materials;
- may create increased risk;
- appears to;
- worth clarifying before signing;
- consider discussing with landlord, agent, or licensed lawyer;
- no obvious critical risk found in uploaded/analyzed materials;
- not a guarantee that the contract is safe.

## Privacy and PII Checks

Flag any architecture, code, prompt, or UI flow that sends or stores raw PII in unsafe places.

Raw PII must not be sent to:

- Gemini;
- Google Vision;
- external OCR;
- cloud image processing;
- runtime Airtable tables;
- logs or exported debug files.

PII includes at least:

- names;
- Israeli ID / ת.ז.;
- phone numbers;
- email addresses;
- full addresses;
- signatures;
- bank account details;
- check numbers;
- landlord, tenant, agent, or guarantor identifying details.

Monetary amounts are not PII by default and should usually be preserved for risk analysis.

Important distinction:

- Do not require a mask on every page.
- Many middle pages of a lease may contain no personal data.
- Future privacy logic should detect likely PII rows/zones by Hebrew field labels and layout.
- Risk-relevant rows and monetary amounts should not be blindly deleted.

## Architecture Checks

Flag contradictions with the target order:

```text
structured text audit
→ evidence blocks
→ Python validation
→ completeness audit
→ three-card report + Разбор по пунктам
→ future privacy-safe image/OCR pipeline
```

Flag if code or prompts implement future features too early, especially:

- OCR before privacy-safe preprocessing;
- runtime Airtable API integration before local JSON/YAML configuration is stable;
- template/reference comparison as MVP;
- conflict-consultant mode as MVP;
- LLM-generated Hebrew quotes as source of truth.

## Report Model Checks

The target user report is:

1. global completeness status;
2. three risk cards:
   - Money;
   - Terms and eviction;
   - Obligations;
3. detailed mode called `Разбор по пунктам`.

Card statuses:

- Red;
- Yellow;
- Green;
- Incomplete.

Green must not mean the contract is safe or that the user can sign. It means only that no obvious critical risk was found in that domain in the uploaded/analyzed materials.

## Evidence Checks

The model should not be the source of truth for exact Hebrew quotes.

Target direction:

```text
source text/images after preprocessing
→ numbered evidence blocks
→ LLM returns evidence_block_ids
→ Python validates IDs
→ Python retrieves original source if needed
```

Flag if prompts or schemas depend on LLM-generated exact quotes as primary evidence after the evidence-block migration is supposed to be in place.

If the current code has not yet migrated to evidence blocks, distinguish between:

- a known transitional limitation;
- a new regression or contradiction.

## Final Summary

End the audit with:

```text
Overall status: OK | Needs fixes | Unsafe to proceed
Top 3 risks:
1.
2.
3.
Recommended next Codex tasks:
1.
2.
3.
```
