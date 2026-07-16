# Gold Set v0 review instructions

This package is a candidate set, not gold data yet.

## Reviewer requirements

The reviewer must be able to read printed Hebrew confidently. Legal expertise is not required.

## Review procedure

1. Open `review.html` locally in Chrome, Edge, or Firefox. No server and no internet connection are required.
2. Enter a reviewer name or initials.
3. Compare the editable transcription with the target crop and the red-outlined line in the page context.
4. Choose:
   - `Correct / נכון` when every printed character and punctuation mark is already exact;
   - `Save correction / שמור תיקון` after correcting the text;
   - `Exclude / לא קריא` when any character is genuinely ambiguous, cropped, obscured, merged with another line, or unreadable.
5. Do not improve grammar, spelling, spacing, punctuation, or legal wording. Transcribe what is printed.
6. Download `gold_accepted_v0.jsonl` after all rows have been reviewed.

The browser saves progress locally. `Download full review JSONL` creates a backup that can later be imported into the interface.

## Privacy

Keep the entire package local. Do not upload the HTML, images, page context, or exported JSONL to a public service. The collector filters obvious PII-field rows and placeholders, but that is not a guarantee that every context image is free of identifying information.

Only rows exported with `review_status` equal to `approved` or `corrected` qualify for the Gold Set v0 evaluation manifest. Excluded and pending rows are not gold.
