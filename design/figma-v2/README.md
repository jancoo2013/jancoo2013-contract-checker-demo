# Figma v2 refinement exports

This directory contains the second visual refinement pass for the Israeli rental-contract parser. It is based directly on the approved Calm Product direction and the merged `design/figma-v1/` artifacts. It does not modify production application code.

## What changed

- Replaced the dark-green accent with a restrained sky-blue family.
- Added an accessible darker blue for filled buttons and blue text.
- Removed red-tinted risk backgrounds; risk emphasis now uses only a thicker red vertical bar and an optional muted-red heading.
- Reduced inner-screen top bars from 48 px to 40 px.
- Added a four-item `Главное` summary to the long analysis screen.
- Kept accordions and gave the most important questions subtle blue leading markers; the first two are expanded.
- Added loading, OCR progress, bad scan, upload error, and uncertain-document screens.
- Preserved the minimalist welcome screen and avoided new decorative content.

## Source design

[Israeli Rental Contract Parser - UI UX Design v1](https://www.figma.com/design/EJvTC0s3RPv29BFXlM1AwA)

The connected Figma Starter-plan MCP limit was reached before v2 canvas writes could begin. The v2 review exports were therefore produced from the existing Figma v1 frames and merged handoff tokens without changing the editable Figma file. The artifacts below are ready for review; synchronizing them into new Figma v2 pages remains a human/Figma follow-up once tool access is available.

## Exported files

- `overview.pdf` - combined 12-page presentation-order review PDF.
- `design-system.md` - exact v2 colors, typography, spacing, dimensions, risk treatment, and RTL notes.
- `design-tokens.json` - machine-readable v2 tokens for future React Native translation.
- `screens/00-design-system-v2.png` - complete v2 design-system overview.
- `screens/01-welcome-final.png` - preserved minimalist welcome screen.
- `screens/02-add-contract.png` - blue-accent contract input screen.
- `screens/03-analysis.png` - standard analysis with quiet risk marker.
- `screens/03-analysis-long.png` - long analysis with `Главное` summary.
- `screens/04-questions.png` - prioritized accordion view.
- `screens/04-questions-long.png` - long accordion-list behavior.
- `screens/05-loading-processing.png` - file preparation/loading state.
- `screens/06-ocr-analysis-progress.png` - OCR and analysis progress state.
- `screens/07-bad-scan.png` - unreadable scan recovery state.
- `screens/08-upload-error.png` - upload failure state.
- `screens/09-uncertain-document.png` - possibly-not-a-rental-contract state.

All PNG exports are rendered at 3x resolution.

## Remaining human-review decisions

- Approve the exact product headline that will replace `SLOGAN PLACEHOLDER`.
- Confirm the sky-blue family on representative physical Android displays.
- Validate the long Hebrew excerpts with real contracts for punctuation and bidi edge cases.
- Decide whether prioritized accordion items should default open in production or only in the first session.
- Confirm whether processing screens need cancellation when actual pipeline behavior is finalized.
- Sync the reviewed v2 frames into the editable Figma file after MCP write access is restored.
