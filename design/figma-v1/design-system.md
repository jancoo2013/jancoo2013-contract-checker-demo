# Design System v1

This document records the exact design decisions used in the Figma review file. The selected direction is **Calm Product**: a restrained reading tool with a warm neutral background, strong typography, and minimal interface chrome.

## Color system

| Token | HEX | Purpose |
| --- | --- | --- |
| Background | `#F9F8F2` | Main application and reading background |
| Primary text | `#1A1F1C` | Titles, headings, and primary body text |
| Secondary text | `#59605B` | Supporting copy and metadata |
| Divider | `#D1D1C5` | Quiet separators and control outlines |
| Primary action | `#1B4F40` | Primary buttons and progress indicator |
| Primary pressed | `#133C31` | Pressed primary-action state |
| Disabled | `#B3B5AD` | Disabled controls and low-emphasis states |
| Warning | `#B83329` | Important contract risk marker only |
| Warning text | `#70241F` | Text inside the risk treatment |
| Warning tint | `#FCF0EC` | Subtle risk-treatment background |
| Surface | `#FFFFFF` | Navigation and quoted-text surfaces |

The warning color is intentionally not part of a red/yellow/green severity scale. It is reserved for genuinely important contract content.

## Typography

Primary family: **Noto Sans**. It was selected after testing Cyrillic, Hebrew, numbers, and the shekel sign together. It provides compatible visual weight across Russian and Hebrew and remains comfortable in long paragraphs.

| Style | Size | Weight | Line height |
| --- | ---: | --- | ---: |
| Screen title | 32 px | SemiBold (600) | 40 px |
| Section heading | 20 px | SemiBold (600) | 28 px |
| Body | 17 px | Regular (400) | 27 px |
| Emphasized body | 17 px | SemiBold (600) | 27 px |
| Supporting text | 14 px | Regular (400) | 21 px |
| Button text | 17 px | SemiBold (600) | 24 px |

Some screen mockups use a 28 px title to preserve hierarchy inside the 360 px Android frame. Long-form body copy remains 16-17 px with approximately 1.5-1.6 line-height.

## Spacing

The system uses an 8 px base rhythm:

- `8 px`: tight internal separation;
- `16 px`: paragraph and related-content spacing;
- `24 px`: standard screen side margins;
- `32 px`: separation between logical sections;
- `48 px`: major section separation.

Android touch targets should remain at least 48 px high.

## Corner radii

- Controls and buttons: `12 px`.
- Reading/quotation treatments: `4 px` or visually square.
- Design-system presentation surfaces: `8 px`.

Text content should not be wrapped in rounded cards unless the surface has a clear functional purpose.

## Component dimensions

All production mockups use a `360 px` Android frame with `24 px` side margins and a `312 px` content width.

| Component | Dimensions |
| --- | --- |
| Primary button | `312 x 56 px` in screens; library master `320 x 56 px` |
| Secondary button | `312 x 56 px` in screens; library master `320 x 56 px` |
| File upload action | `320 x 80 px` library master |
| Top navigation/back control | `312 x 48 px` in screens; library master `320 x 48 px` |
| Collapsed accordion row | `312 px` screen width; `64 px` minimum height |
| Divider | `1 px` height |
| Contract quote block | `312 px` screen width; content-driven height; `16 px` leading inset |
| Inline risk treatment | `312 px` screen width; content-driven height; `3 px` warning side marker |
| Progress/loading state | `320 x 48 px` library master |

## Warning and risk treatment

Risk content remains inside the reading flow. It uses:

- a `3 px` left-side marker in `#B83329`;
- a very light `#FCF0EC` background;
- `#70241F` emphasized text;
- `12 px` vertical padding and `16 px` leading padding;
- no icon, badge, severity label, or oversized alert container.

The treatment must still read as part of the explanation rather than a system alert.

## RTL and Hebrew

- Hebrew contract excerpts use explicit right-to-left paragraph direction and right alignment.
- Quotation blocks preserve punctuation and numeric order, including dates and `₪` values.
- Mixed Hebrew/Russian content should not be assembled as a single manually reordered string.
- Hebrew excerpts use the same Noto Sans family as the Russian UI to keep weight and texture consistent.
- Real contract samples should be checked on Android for punctuation placement, wrapping, bidi behavior, and copied text.

