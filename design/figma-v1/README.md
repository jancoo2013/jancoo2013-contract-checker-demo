# Figma v1 design review exports

This directory contains the review and implementation handoff exports for the Israeli rental-contract parser. The editable source is the Figma file; these repository artifacts allow review without a Figma account.

## Selected direction

**Calm Product** was selected because it offers the best balance of long-form readability, low cognitive load, trust, and accessibility for non-technical users. It uses a warm neutral reading surface, strong typographic hierarchy, restrained dark-green actions, and a single warning accent. The interface intentionally avoids dashboards, card grids, badges, severity systems, decorative imagery, and unnecessary icons.

## Figma source

[Israeli Rental Contract Parser - UI UX Design v1](https://www.figma.com/design/EJvTC0s3RPv29BFXlM1AwA)

## Files

- `overview.pdf` - combined ten-page review document in presentation order: three welcome explorations, Design System v1, four MVP screens, and two long-content variants.
- `design-system.md` - exact human-readable color, typography, spacing, radius, dimension, risk-treatment, and RTL guidance.
- `design-tokens.json` - machine-readable core tokens for later translation into React Native styles.
- `screens/00-welcome-editorial.png` - Editorial Minimal exploration.
- `screens/00-welcome-calm-product.png` - selected Calm Product exploration.
- `screens/00-welcome-precise-utility.png` - Precise Utility exploration.
- `screens/01-welcome-final.png` - final welcome screen.
- `screens/02-add-contract.png` - contract input choices.
- `screens/03-analysis.png` - standard contract-analysis reading view.
- `screens/03-analysis-long.png` - long-content analysis behavior with wrapped Hebrew excerpts.
- `screens/04-questions.png` - standard questions/disclosure screen.
- `screens/04-questions-long.png` - long accordion-list behavior.

All PNG files were exported at 3x resolution.

## Remaining human-review decisions

- Replace `SLOGAN PLACEHOLDER` with approved product language.
- Confirm the final product name and whether it appears on the welcome screen.
- Validate Hebrew punctuation, wrapping, bidi behavior, dates, numbers, and `₪` using representative production contract text on physical Android devices.
- Confirm the warning accent remains sufficiently noticeable without feeling alarming across common Android displays.
- Decide whether expanded questions should allow multiple rows open simultaneously.
- Validate large-text accessibility and translations longer than the current Russian examples before implementation.

No production application code is included or changed by this design export package.
