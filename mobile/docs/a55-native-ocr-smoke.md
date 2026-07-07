# Samsung A55 Native OCR Smoke Test

## Environment

- Device: Samsung Galaxy A55 (`SM-A556E`).
- Build type: Expo development build.
- Android native build: passed.
- Installation on the physical device: passed.
- Expo dev client connection to Metro: passed.
- Local Tesseract OCR invocation on the device: passed.

This run was performed in a Metro-backed development session. The separate airplane-mode/offline checks documented in `mobile/README.md` were not run in this session and are not marked as passed here.

## Synthetic Results

These results were captured before the anchor-based proposal refactor. The `PII candidates`
and `id_like` / `phone_like` / `email_like` labels below describe the earlier value-regex
experiment, not the current anchor-based proposal path.

### Hebrew PII markers

- OCR state: `success`.
- Duration: `285 ms`.
- Text items: `37`.
- PII candidates: `0`.
- `id_like`: `0`.
- `phone_like`: `0`.
- `email_like`: `0`.

Observed result: the OCR output contained substantial corruption of digits and email-like text, so the deterministic PII candidate detector did not recover the synthetic ID, phone, or email markers.

### Hebrew layout

- OCR state: `success`.
- Duration: `248 ms`.
- Text items: `43`.
- PII candidates: `0`.

Observed result: the synthetic layout page produced partially readable Hebrew text and preserved some numeric content, but the output still contained clear Hebrew and numeric recognition errors.

## Conclusion

The physical-device native chain is proven for this spike:

`Android native build -> install on A55 -> Expo development build -> on-device Tesseract invocation -> OCR text items returned to React Native`

The current synthetic evidence is not sufficient to treat Tesseract output as reliable input for privacy decisions. In particular, the PII-marker test missed all synthetic ID/phone/email candidates after OCR corruption.

The next evidence-gathering step should be a controlled local-only test on representative lease-page images plus preprocessing variants. No production privacy decision should depend on this spike until recall is measured on representative data.
