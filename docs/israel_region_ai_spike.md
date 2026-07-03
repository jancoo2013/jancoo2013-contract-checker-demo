# Israel-region AI spike

This document defines a narrow feasibility spike for replacing part of the current privacy complexity with Israeli-region infrastructure.

The spike is not an architecture decision and not legal advice. It is a checklist for deciding whether the product can safely move from a heavily damaged-text flow toward a regional server-side AI flow.

## Motivation

The current privacy direction risks becoming over-engineered:

```text
OCR text -> aggressive Swiss-cheese PII filter -> damaged legal text -> external AI analysis
```

That path has known failure modes:

- regex and zoning can miss PII;
- regex and zoning can destroy legally important context;
- Hebrew OCR noise makes deterministic PII removal brittle;
- a user-facing manual masking flow is too fragile;
- every new PII heuristic adds edge cases.

The alternative to test is:

```text
Israeli-region application server
-> in-memory processing
-> Israeli-region or region-controlled OCR/LLM endpoint, if available and acceptable
-> no raw disk storage
-> no raw app logs
-> Russian report
```

If this path is viable, Swiss-cheese redaction can become a fallback or auxiliary safety layer instead of the core privacy architecture.

## Current factual baseline

As of this document, Google Cloud documentation shows:

- Gemini Enterprise Agent Platform exposes regional endpoints and a global endpoint.
- REST calls can target a regional endpoint such as:

```text
https://${GOOGLE_CLOUD_LOCATION}-aiplatform.googleapis.com/v1/projects/${GOOGLE_CLOUD_PROJECT}/locations/${GOOGLE_CLOUD_LOCATION}/publishers/google/models/${MODEL_ID}:generateContent
```

- The deployment locations page lists Tel Aviv / `me-west1` among Middle East locations and lists Gemini model entries for that region.
- The same locations page explicitly warns that endpoints do not by themselves guarantee data residency or in-region ML processing.
- Google says not to use the global endpoint when there are ML-processing-location requirements, because the customer cannot control or know which region receives the ML processing request.
- The data residency page says ML processing occurs within the region or multi-region where the request is made, but also says that regional endpoints not explicitly listed in the data-residency tables, including Middle East regions, have no guarantee that ML processing occurs at a specific location.
- Google states that it won't use customer data to train or fine-tune AI/ML models without prior permission or instruction.
- Request-response logging is disabled by default, but can be enabled per model/project and should remain disabled for this product.
- Grounding with Google Search or Google Maps can introduce additional storage and must remain disabled for this product.
- Published Gemini models use in-memory caching by default with a 24-hour TTL; this can be disabled at the project level.

Primary references to re-check before implementation:

- https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/locations
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/data-residency
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/zero-data-retention

## Critical distinction

A server or endpoint in Israel does not automatically prove that all sensitive processing stays in Israel.

We must distinguish:

```text
1. Application hosting region
2. OCR execution region
3. LLM inference region
4. Data-at-rest location
5. Vendor logging / abuse monitoring / cache behavior
6. Legal acceptability under the final product posture
```

A successful technical call to `me-west1` proves only that the endpoint is reachable and functional. It does not prove legal data residency or physical inference location.

## Spike question

Can the product use an Israel-region or region-controlled AI path that is simple enough for MVP and materially reduces the need for aggressive pre-AI PII destruction?

## Non-goals

This spike must not:

- rewrite the current app;
- replace the current Gemini engine;
- add a new production dependency;
- send real contracts or real PII;
- change OCR prompts;
- change analysis prompts;
- change schemas;
- change report generation;
- make legal/privacy claims in the UI;
- claim that `me-west1` alone proves data residency.

## Technical checks

### 1. Project and authentication

Verify that a Google Cloud project can call Gemini through an explicitly selected region.

Required variables:

```bash
PROJECT_ID="your-project-id"
LOCATION="me-west1"
MODEL_ID="gemini-2.5-flash"
```

The exact model may change based on the current Google model table. Use the smallest generally available Gemini model that supports the needed input type.

### 2. Regional REST endpoint test

Use a harmless Hebrew prompt. Do not use contract text.

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${MODEL_ID}:generateContent" \
  -d '{
    "contents": {
      "role": "user",
      "parts": {
        "text": "ענה בעברית במשפט אחד: האם אתה עובד?"
      }
    }
  }'
```

Record only:

```text
endpoint
location
model id
status code
latency
response length
error code, if any
```

Do not record prompt contents beyond this harmless fixed test string.

### 3. Hebrew legal text sanity test

Use a synthetic, non-personal Hebrew lease-like paragraph.

Pass condition:

- model responds in Russian or Hebrew as instructed;
- model can identify basic lease concepts such as rent, dates, deposit, exit clause, repair obligations, and utilities;
- no real contract data is used.

### 4. Image/PDF input test

Use a synthetic image or PDF containing non-personal Hebrew lease-like text.

Pass condition:

- the selected regional model accepts the input type;
- the model extracts or reasons over the Hebrew text with acceptable quality;
- the test does not require sending real contracts;
- the app does not need a separate global OCR service.

If image/PDF is not supported or poor, test a two-step regional path:

```text
regional OCR or document parser
-> regional LLM analysis
```

### 5. Migration complexity check

Compare the current direct Gemini API integration with a regional Vertex/Gemini Enterprise call.

Answer these questions:

- Can the current Gemini engine be wrapped behind a provider interface?
- Can the same prompt/schema be reused?
- Does the API support structured output well enough for the current report schema?
- Does the API require service-account credentials instead of API key?
- Can secrets remain server-side only?
- Can the MVP run locally for development without exposing credentials?

## Compliance and privacy checks

Technical testing is not enough. Before using real user contracts, verify the following:

### 1. Data residency / ML processing

Required answer:

```text
Does the selected model and endpoint provide a contractual or documented guarantee that ML processing for this request stays in Israel or an acceptable jurisdictional boundary?
```

Important current risk:

```text
Google's data-residency documentation warns that Middle East regional endpoints not explicitly listed in the data-residency tables do not guarantee ML processing at a specific location.
```

If this remains true for `me-west1`, the spike cannot conclude that all ML processing stays in Israel.

### 2. Logging and retention

Required answers:

- Is request-response logging disabled?
- Is prompt/response logging for abuse monitoring applicable to this account/model?
- Is an abuse-monitoring exception available or required?
- Is in-memory Gemini caching enabled?
- Can project-level caching be disabled?
- Are Google Search grounding and Google Maps grounding disabled?
- Are app-level logs free of raw document text and raw images?

### 3. Storage

Required answers:

- Are raw uploaded files written to disk?
- Are raw OCR outputs persisted?
- Are prompts/responses persisted?
- Are app crash logs or Streamlit logs likely to contain raw text?
- Are temporary files explicitly avoided or cleaned?

For MVP, desired posture remains:

```text
server-side in-memory processing
no raw disk storage
no database writes for raw files/OCR
no raw app logs
server-side credentials only
```

## Pass / fail matrix

### Green

Use regional AI path as the preferred architecture if all are true:

- `me-west1` or another acceptable regional endpoint works technically;
- Hebrew text quality is acceptable;
- image/PDF or regional OCR path is acceptable;
- logging and grounding risks are controlled;
- Google or the selected provider gives a sufficient data-residency / ML-processing answer for the intended use;
- migration complexity is moderate;
- no real PII is needed for the spike.

Architecture implication:

```text
Regional server-side AI becomes the preferred MVP direction.
Swiss-cheese redaction becomes auxiliary/fallback, not the main privacy wall.
Manual masking remains out of the main flow.
```

### Yellow

Use regional AI path only for limited testing if:

- the endpoint works;
- Hebrew quality is acceptable;
- but ML-processing/data-residency guarantees are incomplete.

Architecture implication:

```text
Do not send real user PII yet.
Keep Swiss-cheese redaction as the main pre-AI privacy layer.
Continue compliance investigation.
```

### Red

Do not pursue this path now if:

- the regional endpoint is unavailable;
- image/PDF or OCR quality is unacceptable;
- logging/retention cannot be controlled;
- the provider cannot give an acceptable ML-processing/data-residency posture;
- migration requires a broad rewrite before MVP validation.

Architecture implication:

```text
Stay with damaged-text / PII-redaction architecture for the MVP.
Keep the regional path as a later infrastructure track.
```

## Recommended next artifact

If this document is accepted, the next code artifact should be a non-production spike script, for example:

```text
scripts/spike_vertex_me_west1.py
```

Constraints for that script:

- not imported by `app.py`;
- not used in production flow;
- no real contracts;
- no raw PII;
- prints only metadata and pass/fail summaries;
- requires explicit environment variables;
- exits safely if credentials are missing.

## Decision rule

Do not continue expanding Swiss-cheese privacy complexity until this spike is resolved.

The product should not choose a complex redaction architecture merely because we failed to test whether a simpler regional infrastructure path is viable.
