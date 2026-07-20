# CTC Text Order Contract v0

Status: binding framework-independent recognizer boundary.

Read with `DATASET_CONTRACT_V0.md`. Dataset labels and final predictions remain
logical Unicode. This contract defines the separate monotonic character order used
by a left-to-right CTC recognizer over the source pixels.

## Orders

1. **Logical order** is the canonical Unicode text stored in datasets and used for
   CER.
2. **CTC alignment order** is the character sequence encountered while scanning a
   rendered line from the left edge of the image to the right edge.
3. CTC repeat collapse and blank removal operate in alignment order.
4. Only after collapse is alignment order converted to logical order.

The conversion must never reverse padded time steps or treat bidi controls as data.

## Supported RTL v0 grammar

The bounded transform supports:

- Hebrew tokens, including Hebrew quote marks and attached punctuation;
- pure ASCII digit tokens and decimal/clause forms such as `2.1`;
- pure Latin tokens and internal punctuation such as `AS-IS`;
- whitespace-separated Hebrew, digit, and Latin tokens on one RTL line;
- standalone neutral punctuation tokens;
- mirrored bracket pairs `()`, `[]`, `{}`, and `<>`;
- pure LTR lines as identity.

For supported RTL lines the same deterministic transform converts logical order to
CTC alignment order and converts alignment order back to logical order. Focused
tests require that round trip to be exact.

## Fail-closed boundary

This is not a complete inverse Unicode Bidirectional Algorithm. A token containing
both Hebrew and LTR strong characters without an ASCII-space boundary is rejected.
Examples such as `אA` or `Aא` must not be guessed.

If real contract data shows that such tokens are common, the contract must be
extended with explicit fixtures before training or evaluation accepts them. The
decoder must not silently reorder an unsupported token into plausible text.

## Decoder output

`greedy_decode` returns:

- `text` in canonical logical order;
- `class_ids` matching that logical text;
- the original valid `input_length`.

This component does not perform page reading order, language correction, OCR
confidence repair, layout reconstruction, or Unicode normalization.
