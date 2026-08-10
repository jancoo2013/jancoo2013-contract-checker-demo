# Document Geometry Freeze Criteria v1

Status: binding component-level code-freeze contract for the current document geometry normalization block.

This document defines when the geometry block is good enough to stop changing at code level. It is intentionally finite. It does not claim perfect pixel preservation, real-photo validation, production readiness, OCR readiness, or Android readiness.

Frozen geometry code baseline after PR #209:

`7fe4bc88df2427ea90442f7b074c3cfe4e0de33a`

## 1. Scope of this freeze

The frozen block is:

```text
source PIL image
→ bounded source size/mode/resource validation
→ EXIF orientation handling
→ bounded grayscale preview
→ local-contrast text/ink mask
→ bounded text-angle estimate
→ bounded content-region estimate
→ meaningful disconnected-content and deskew edge-loss guards
→ accepted-stage structural validation
→ full-resolution deskew + conservative crop only when fully trusted
→ otherwise full-frame fallback
→ DocumentGeometryNormalizationResult
```

Included implementation files:

- `research/hebrew_contract_ocr/geometry_resource_budget.py`
- `research/hebrew_contract_ocr/text_ink_mask.py`
- `research/hebrew_contract_ocr/text_angle_estimator.py`
- `research/hebrew_contract_ocr/content_region_bounds.py`
- `research/hebrew_contract_ocr/content_region_deskew_crop.py`
- `research/hebrew_contract_ocr/document_geometry_normalizer.py`

The freeze does not include illumination/shadow normalization, glare/blur checks, perspective correction, Android camera/runtime integration, OCR, PII processing, encryption/upload, provider/serverless runtime, Gemini/LLM, reports, or persistent storage.

## 2. Code-level freeze decision

The geometry block is considered **code-level frozen at the PR #209 merge baseline** when the criteria in this document are satisfied.

The purpose of the freeze is to prevent an endless adversarial loop in which each successful fix is followed only by a smaller synthetic object or a producer-impossible internal state and the stopping threshold moves again.

Code-level frozen does not mean immutable forever. The block may be reopened only under the explicit reopen conditions in section 8.

## 3. Minimum meaningful-content contract

The geometry layer is conservative, but it is not required to treat every foreground pixel as legally meaningful document content.

A crop-safety blocker is required when the current bounded geometry evidence recognizes plausible page content through one of these classes:

1. **Line-like disconnected content** detected by the existing outside line-band logic.
2. **Compact disconnected content** meeting the current compact-foreground evidence rules, including the existing row-occupancy, minimum-pixel, area and long-vertical-artifact rules.
3. **Deskew source-edge loss** where bounded `expand=False` preview rotation loses at least the current meaningful-loss threshold used by the source-edge guard.
4. Any larger or clearer content pattern already covered by the finite regression set in section 6.

The current compact/source-edge threshold constants are implementation policy for this frozen version. Changing those thresholds is a new product/engineering decision and reopens the component contract; an auditor does not lower them implicitly by presenting a smaller synthetic mark.

### Explicit non-blocking boundary

Sub-threshold isolated or fragmented marks that do not satisfy the current meaningful-content evidence contract are not code-freeze blockers by themselves.

Examples from the third audit such as `1×8`, `2×8`, `2×9`, `3×6`, `4×4`, or similarly tiny disconnected synthetic marks do not automatically require another corrective PR.

This does **not** assert that such pixels can never be meaningful in a real document. It means only that code-level freeze is not conditioned on preserving arbitrarily small undifferentiated foreground. If real-photo/product validation later shows that a currently sub-threshold class systematically represents meaningful contract content, that is new evidence and may reopen the block under section 8.

## 4. Producer/consumer trust boundary

`TextAngleEstimate` and `ContentRegionBounds` are internal in-process stage contracts produced by the geometry block. They are not currently an external serialized API or an untrusted network boundary.

The physical transform consumer must fail closed on structural contradictions that can affect mutation or coordinates. The current freeze baseline therefore requires validation of the structural invariants already enforced by the implementation, including as applicable:

- accepted/rejected decision semantics;
- finite and bounded deskew rotation;
- accepted confidence/rejection-state consistency;
- angle/deskew sign consistency;
- preview dimensions and coordinate space;
- valid candidate and safe boxes;
- safe box containing the candidate;
- accepted line-evidence minimum, boundedness, distinctness and candidate-union consistency;
- rotation agreement between accepted stage contracts.

The consumer is **not required to re-run or duplicate the producer's semantic scoring algorithm** merely to defend against manually forged internal objects that the real producer cannot emit.

Accordingly, producer-only diagnostic metrics that do not directly drive physical coordinates or mutation, such as forged combinations of `foreground_ratio`, `projection_gain`, or `peak_margin`, are not a separate freeze blocker when:

1. the normal producer cannot emit the contradictory accepted state from valid input; and
2. the transform already validates the structural fields it actually relies on.

If these dataclasses later become externally deserialized, persisted, IPC-visible, plugin-provided, or otherwise untrusted inputs, this trust decision expires and the validation boundary must be reviewed before that integration ships.

## 5. Fail-safe contract

The frozen geometry block must preserve these invariants:

1. Uncertain or rejected geometry does not authorize a crop.
2. `rotation_only` produces the existing full-frame physical fallback; it does not perform a partial rotation-only mutation.
3. Meaningful disconnected content outside a proposed crop blocks crop acceptance.
4. Meaningful source-edge content that would be clipped by bounded deskew blocks the physical transform.
5. Preview analysis may be lower-resolution, but accepted physical transforms operate on the oriented full-resolution source.
6. Preview-to-source crop mapping remains conservative: floor left/top and ceil right/bottom with independent source/preview axis scaling.
7. Supported source mode, dimensions, pixel count and accounted geometry memory remain bounded before geometry-triggered expensive full-resolution operations.
8. Unsupported modes fail closed before EXIF/conversion/physical transform.
9. The block performs no network access, document persistence, OCR, PII processing, logging of page content, or external-service call.

## 6. Finite regression set for freeze

The code-level freeze is based on this finite regression surface. Audits may verify these cases, but may not silently replace them with an ever-shrinking threshold.

### Normal operation

- horizontal single-column document can be accepted and cropped;
- ordinary central positive/negative skew inside the estimator acceptance range can be deskewed and cropped;
- zero/near-zero skew remains stable;
- analysis preview remains bounded while physical transform uses full resolution.

### Full-frame fail-safe

- blank/rejected angle;
- two-column layout where dominant crop would remove another column;
- disconnected header/footer/edge line meeting the meaningful-content contract;
- compact/fragmented disconnected content meeting the meaningful-content contract;
- source-edge meaningful content that would be clipped by deskew;
- content touching the frame or an otherwise unsafe crop decision.

### Structural contracts

- accepted search-limit `±12°` and out-of-range rotations fail closed;
- malformed/non-finite rotation fails closed;
- contradictory confidence/rejection/sign state covered by current accepted-stage tests fails closed;
- insufficient, invalid, duplicate-only, out-of-preview, or candidate-inconsistent accepted line evidence fails closed;
- invalid safe/candidate containment fails closed.

### Coordinates and EXIF

- EXIF orientation is interpreted consistently across preview and transform;
- mirrored/oriented variants have recorded audit evidence for orientations 1–8;
- odd dimensions, portrait/landscape and rounded preview dimensions preserve conservative coordinate mapping;
- preview-to-source mapping uses independent X/Y dimensions rather than the informational scalar alone.

### Resource and mode contract

- source long side, total pixels and accounted memory are bounded;
- preview working-set accounting and full-resolution transform accounting remain explicit;
- every admitted PIL mode completes the current path without a late mode-conversion failure;
- unsupported `LAB` and unknown modes fail closed at the initial resource guard.

The repository's focused geometry tests plus the recorded bounded synthetic audit probes constitute the evidence baseline. A future modification to any frozen implementation file must re-run the relevant current geometry regression suite and re-evaluate any invariant it changes.

## 7. What does not block this code freeze

The following are not sufficient by themselves to reopen or prevent the code-level freeze:

- making a synthetic disconnected mark smaller than the explicit meaningful-content contract until a threshold is crossed;
- manually constructing producer-impossible semantic metric combinations in internal dataclasses when no valid producer path can emit them and they do not bypass structural mutation checks;
- demanding exact process RSS when the current requirement is a conservative bounded accounting contract;
- memory already spent by an external decoder before an existing `PIL.Image` enters this API;
- missing future preprocessing features that are outside this block;
- lack of real-photo/product validation by itself;
- stylistic refactors, alternative heuristics, or theoretical improvements without a reproduced in-contract defect.

These may be observations, backlog ideas, or reasons for later empirical validation, but they are not automatic corrective PRs.

## 8. Reopen criteria

The frozen geometry block may be reopened when at least one of these is demonstrated:

1. A reproducible valid-input case loses content that satisfies the meaningful-content contract in section 3.
2. A state produced by the real current geometry producers can authorize an unsafe transform despite the structural validation contract.
3. A supported source mode or valid bounded input can violate the resource contract, fail after admission, or trigger unbounded geometry work.
4. EXIF/coordinate/rotation behavior can reproducibly crop or transform meaningful content incorrectly within the supported contract.
5. Real-photo/product validation produces concrete evidence that the current meaningful-content threshold systematically discards a class of actual contract content.
6. A frozen implementation file, relevant dependency behavior, PIL contract, or trust boundary changes materially.
7. The internal stage dataclasses become externally supplied or deserialized, invalidating the producer/consumer trust assumption.

A reopen must name the concrete violated invariant and the smallest bounded corrective. It must not be justified only by “find more edge cases”.

## 9. Audit policy after freeze

Future periodic Codex audits may verify the frozen contract and detect regressions across later work, but geometry-specific audit prompts must be finite and contract-based.

Do not use an open-ended geometry prompt whose success criterion is simply to keep inventing smaller foreground marks or impossible internal states until something fails.

A new geometry finding is actionable only when it satisfies the reopen criteria above.

## 10. Freeze conclusion and next product step

Existing evidence at the PR #209 code baseline includes:

- the focused geometry suite reported PASS, `65/65`, after the source-edge corrective;
- the third focused audit independently reported the phase-aware resource accounting as `FIXED`;
- the same audit independently reported admitted PIL mode alignment as `FIXED`;
- prior focused audits and corrective PRs established regression coverage for wide/disconnected content, compact meaningful content, accepted-stage structural contradictions, EXIF/coordinate behavior and resource limits;
- PR #209 added the concrete source-edge deskew-loss fail-safe identified as product-relevant in the third audit.

Under the finite criteria in this document, the remaining third-audit sub-threshold micro-content examples and producer-impossible forged semantic metric combinations do not require another implementation corrective before code-level freeze.

Therefore, after this contract is merged, the document geometry normalization block is **code-level frozen at `7fe4bc88df2427ea90442f7b074c3cfe4e0de33a`**.

The next product implementation step is the previously approved bounded gate:

`serverless-gpu-ocr-viability-benchmark-v1`

Real-photo/product validation of the frozen geometry block remains required later and may reopen the block only through the explicit criteria in section 8.
