# Design System v2

V2 is a refinement of the approved **Calm Product** direction from Figma v1. It preserves the same typography-led reading experience, 360 px Android frame, restrained component set, and warm neutral background. The changes are limited to the accent system, warning treatment, compact navigation, content prioritization, and missing states.

## Colors

| Token | HEX | Usage |
| --- | --- | --- |
| Background | `#F8F8F4` | Main reading surface |
| Surface | `#FFFFFF` | Compact top bars and quoted text |
| Primary text | `#18242B` | Titles and body copy |
| Secondary text | `#5E6B73` | Supporting text and explanations |
| Divider | `#D6DCE0` | Quiet separators and control structure |
| Sky blue | `#4DA3D9` | Interactive markers, outlines, progress, and priority indicators |
| Filled action | `#2F7EA8` | Accessible filled-button background |
| Pressed / blue text | `#246487` | Pressed controls and blue text on light backgrounds |
| Soft blue | `#EAF4FA` | Reserved subtle state surface; not used as decorative card fill |
| Disabled fill | `#C8DFEB` | Disabled controls |
| Disabled text | `#6B8796` | Disabled labels |
| Warning bar | `#C64035` | Risk marker only |
| Warning heading | `#91342D` | Optional small risk heading |

White text on `#2F7EA8` has approximately 4.5:1 contrast. Normal blue text uses the darker `#246487`; the lighter `#4DA3D9` is reserved for non-text indicators and borders.

## Typography

Primary family: **Noto Sans**.

| Style | Size | Weight | Line height |
| --- | ---: | ---: | ---: |
| Screen title | 32 px | 600 | 40 px |
| Compact screen title | 28 px | 600 | 36 px |
| Section heading | 20 px | 600 | 28 px |
| Body | 17 px | 400 | 27 px |
| Emphasized body | 17 px | 600 | 27 px |
| Supporting | 14 px | 400 | 21 px |
| Button | 17 px | 600 | 24 px |

The same family is used for Cyrillic, Hebrew, numbers, dates, and `₪` values.

## Spacing and dimensions

- Base rhythm: `8 px`.
- Screen width: `360 px`.
- Screen side margins: `24 px`.
- Content width: `312 px`.
- Related-content gap: `12-16 px`.
- Section gap: `24-32 px`.
- Major separation: `48 px`.
- Minimum Android touch target: `48 px`.
- Primary and secondary button height: `56 px`.
- Compact top bar height: `40 px` (reduced from 48 px in v1).
- Control radius: `12 px`.
- Presentation-surface radius: `8 px`.
- Reading treatments: square or `4 px` maximum.

## Accent behavior

- Filled primary buttons use `#2F7EA8` with white text.
- Secondary buttons use a `#4DA3D9` outline with `#246487` text.
- Progress tracks use `#DDE7EC`; progress values use `#4DA3D9`.
- Priority accordion items use only a `2 px` sky-blue leading line.
- Summary bullets use small sky-blue dots.
- No blue decorative cards, badges, chips, or gradients.

## Warning and risk treatment

The v1 red-tinted background has been removed. The v2 treatment uses:

- the normal page background;
- a `5 px` vertical `#C64035` bar on the left;
- `15 px` leading padding;
- optional `Особенно важно:` heading in `#91342D`;
- normal primary text for the explanation;
- no icon, badge, colored container, or severity label.

This treatment is meant to remain visible inside long-form reading without creating repeated alarm surfaces.

## Components and states

The compact v1 component set remains in use: primary and secondary buttons, upload action, accordion, divider, contract quote, risk marker, progress state, and top navigation.

V2 adds screen-level patterns for:

- file preparation/loading;
- OCR and analysis progress;
- bad scan or unreadable text;
- upload failure;
- uncertain document classification.

Error states use clear recovery actions and explanatory text instead of illustrations or large warning panels.

## RTL and Hebrew

- Hebrew contract excerpts use actual RTL direction, right alignment, and `unicode-bidi: plaintext` behavior in exports.
- Dates, numbers, punctuation, and `₪` must be checked with real production excerpts on Android.
- Hebrew quotations remain separate from Russian explanations to avoid manual bidi reordering.
- Multi-line quotes retain the same Noto Sans family and comparable optical weight.

