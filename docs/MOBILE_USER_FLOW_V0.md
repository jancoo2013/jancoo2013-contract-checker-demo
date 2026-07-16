# Mobile User Flow v0

Status: approved initial product contract until the first user tests.

This document fixes the initial mobile application flow. It is a product and UX decision, not a claim that every underlying OCR, privacy, or legal-analysis component is already implemented.

Changes to the decisions below require an explicit product decision and an update to this file.

## 1. Core product rule

The user is responsible for only two things:

1. photographing every page clearly enough;
2. confirming that all pages and attachments have been photographed.

The user is not responsible for:

- sorting pages;
- identifying document types;
- viewing or editing privacy masks;
- deciding what counts as personal data;
- correcting OCR text;
- correcting extracted legal facts;
- reconstructing clauses or document structure.

Those are system responsibilities.

## 2. First application launch

On the first launch, the application automatically shows a short, minimal animation explaining how to photograph a contract.

The animation should demonstrate:

- the phone held parallel to the page;
- the whole page inside the frame;
- sufficient and even lighting;
- avoidance of shadows from the phone or hands;
- avoidance of glare;
- readable text size and focus;
- one complete page per photograph.

The animation is shown automatically only once. The application stores a local onboarding-completed flag after the user finishes or skips it.

After the first launch, the same animation remains available from:

```text
Menu → Help / Tips → How to photograph a contract
```

It must not interrupt later application launches.

## 3. Main screen

After onboarding, the primary action on the main screen is to start photographing a contract.

The main screen may also provide access to:

- previously saved reports;
- the help and tips menu;
- privacy and product limitations;
- application settings.

The main screen does not repeat the full photography preparation flow.

## 4. Photographing pages

Pages may be photographed in any order.

The application must not require the user to:

- start from page one;
- follow printed page numbering;
- drag pages into order;
- manually label pages;
- restart because the capture order was wrong.

During capture, the application should give only simple, actionable quality guidance, for example:

- move the phone higher;
- hold the phone parallel to the page;
- add more light;
- remove the shadow;
- avoid glare;
- keep the full page inside the frame;
- hold still while the image is captured.

The preferred future behavior is automatic capture when page geometry and image quality are acceptable.

## 5. Completeness confirmation

The important user check is completeness, not page order.

Before processing starts, the application asks the user to confirm that every page and attachment has been photographed.

The application may show captured thumbnails and a total image count, but it must not ask the user to sort them.

If the system later cannot establish that the document package is complete, it should report uncertainty rather than ask the user to reconstruct the contract manually.

Example user-facing message:

> We could not confirm that the complete contract was photographed. Check that no pages or attachments are missing.

## 6. Hidden local preprocessing and privacy handling

Image enhancement and personal-data handling run automatically and locally.

The user must not see, approve, draw, remove, or correct privacy masks in the normal product flow.

The system is responsible for detecting and suppressing personal data, including relevant names, Israeli ID numbers, phone numbers, email addresses, addresses, signatures, bank details, account identifiers, and other identifying fields covered by the privacy design.

The privacy layer must preserve legal and financial content needed for analysis whenever possible.

If privacy handling is uncertain, the system must fail closed. It must not send questionable material to an external service merely because the user cannot see the masks.

Possible internal outcomes include:

- safe for the next processing stage;
- restricted to on-device processing;
- rejected and requiring a new photograph.

The normal user interface shows only a simple processing status, not technical mask geometry.

## 7. Default supported document type

The default MVP target is a clean, printed Hebrew rental-contract form.

The product is designed first for:

- printed contract pages;
- printed clauses and standard attachments;
- no handwriting or only insignificant handwriting outside the analyzed text.

Handwritten additions are not a supported OCR target in the initial MVP.

If significant handwriting is detected, the application must not pretend that it was reliably analyzed. It should explain that handwritten content may be excluded and that conclusions depending on it may be incomplete.

## 8. OCR and document reconstruction

OCR runs without user correction.

The user must not edit:

- recognized Hebrew text;
- dates;
- monetary amounts;
- clause numbers;
- names of document types;
- extracted obligations or risks.

Manual correction would mix the source contract with the user's interpretation and would weaken traceability of later legal findings.

After OCR, the system reconstructs the document package automatically. Capture order is only an optional fallback signal, not a required ordering rule.

The reconstruction stage may use:

- printed page numbers;
- clause numbering;
- headings and document titles;
- paragraph continuity;
- page-level OCR coordinates;
- opening and closing text fragments;
- attachment markers;
- signatures and final-page layout;
- Gemini-based contract structure analysis after privacy-safe OCR output is available.

If reconstruction confidence is low, the system records and reports uncertainty. It does not ask the user to manually assemble the legal document.

## 9. Analysis and report

The privacy-safe reconstructed document is passed to the contract structure and legal-risk analysis stages.

The report should distinguish:

- critical risks;
- conditions requiring attention;
- ordinary conditions;
- important missing or unconfirmed conditions;
- limitations caused by unreadable, missing, handwritten, or structurally uncertain material.

A finding should remain traceable to a source page and evidence block. The application must not state that a contract is safe or provide a definitive instruction to sign it.

## 10. Approved initial flow

```text
first launch
→ automatic photography tutorial
→ main screen
→ photograph all pages in any order
→ user confirms that all pages and attachments were photographed
→ hidden on-device image preprocessing
→ hidden automatic privacy handling
→ on-device OCR without user corrections
→ automatic document reconstruction and structure analysis
→ legal-risk analysis
→ report with evidence and uncertainty states
```

On later launches:

```text
main screen
→ photograph contract
```

The photography tutorial remains available only through the help and tips menu unless the user explicitly opens it.

## 11. Revision trigger

This flow is frozen as the initial UX contract until real usability tests produce evidence that it should change.

The first tests should specifically measure:

- whether users understand that pages may be photographed in any order;
- whether users reliably photograph every page and attachment;
- whether the first-launch animation improves image quality;
- whether quality prompts are understandable without technical language;
- whether the absence of visible masks causes confusion or increases trust;
- whether users understand handwriting limitations;
- whether the system can recover document structure without manual sorting.
