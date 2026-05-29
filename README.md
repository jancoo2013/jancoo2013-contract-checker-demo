# Contract Checker Streamlit Demo

This repository contains a public-safe Streamlit demo for deterministic contract text checks.

## What this demo does

- Accepts pasted Hebrew/English contract text.
- Optionally accepts JPG/PNG uploads and runs experimental server-side OCR with Tesseract.
- Lets the user edit OCR text before analysis.
- Checks for common contract topics such as parties, payment terms, duration, termination, governing law, and signatures.
- Flags a small set of caution patterns with simple keyword matching.
- Exports a Markdown summary report.

## Image upload OCR

Image upload OCR is experimental and is intended only for clear printed contract pages. Printed Hebrew OCR may work when the Tesseract Hebrew language data is available, but handwritten Hebrew is **not** treated as verified fact and should remain manual-review / untrusted.

The public Streamlit Community Cloud deployment uses `packages.txt` to install system Tesseract packages:

- `tesseract-ocr`
- `tesseract-ocr-heb`
- `tesseract-ocr-eng`

The Python dependency `pytesseract` calls that server-side Tesseract binary. Hebrew OCR requires the Hebrew language data package (`tesseract-ocr-heb`). If OCR is unavailable in a deployment, text paste mode remains the fallback.

## Public-safety boundaries

This demo intentionally does **not** include:

- Real contract photos or private repository files.
- Paid APIs.
- LLM calls.
- Secrets or API keys.
- Any claim that handwritten Hebrew is reliably recognized.

This prototype does not replace a lawyer. OCR mistakes are possible. Handwritten Hebrew is not treated as verified fact.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

For local OCR, your machine also needs the Tesseract binary and Hebrew/English language data installed. If local OCR is not available, use the paste-text tab.

## Streamlit Community Cloud settings

- Repository: `jancoo2013/contract-checker-demo`
- Branch: `main`
- Main file path: `app.py`
- System packages: configured by `packages.txt`

When the connected branch is updated, Streamlit Community Cloud should redeploy the app automatically.
