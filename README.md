# Contract Checker Streamlit Demo

This repository contains a public-safe Streamlit demo for deterministic contract text checks.

## What this demo does

- Accepts pasted contract text.
- Checks for common contract topics such as parties, payment terms, duration, termination, governing law, and signatures.
- Flags a small set of caution patterns with simple keyword matching.
- Exports a Markdown summary report.

## Public-safety boundaries

This demo intentionally does **not** include:

- Real contract photos or private repository files.
- OCR or Tesseract dependencies.
- Paid APIs.
- LLM calls.
- Secrets or API keys.

The app is for demonstration only and is not legal advice.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud settings

- Repository: `jancoo2013/contract-checker-demo`
- Branch: `main`
- Main file path: `app.py`
