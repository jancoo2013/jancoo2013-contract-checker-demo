from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Sequence

SUPPORTED_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


@dataclass(frozen=True)
class PageResult:
    model: str
    document_id: str
    source_name: str
    page_number: int
    text: str
    blocks: list[dict[str, Any]]
    metadata: dict[str, Any]


class _HTMLTextExtractor(HTMLParser):
    _BREAK_TAGS = {"br", "div", "li", "p", "table", "tr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.lower() in self._BREAK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._BREAK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def html_to_text(value: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(value or "")
    lines = [" ".join(line.split()) for line in "".join(parser.parts).splitlines()]
    return "\n".join(line for line in lines if line).strip()


def discover_images(input_dir: Path) -> list[Path]:
    if not input_dir.is_dir():
        raise ValueError(f"input directory does not exist: {input_dir}")
    paths = sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    if not paths:
        raise ValueError(f"no supported images found in {input_dir}")
    stems = [path.stem for path in paths]
    if len(stems) != len(set(stems)):
        raise ValueError("input image stems must be unique")
    return paths


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_surya_result_files(raw_dir: Path) -> list[Path]:
    result_files = sorted(raw_dir.rglob("results.json"))
    if not result_files:
        raise ValueError(f"Surya results.json not found under {raw_dir}")
    return result_files


def load_surya_results(raw_dir: Path, inputs: Sequence[Path]) -> list[PageResult]:
    merged: dict[str, Any] = {}
    for result_path in _find_surya_result_files(raw_dir):
        payload = _load_json(result_path)
        if not isinstance(payload, dict):
            raise ValueError(f"invalid Surya result payload: {result_path}")
        overlap = set(merged).intersection(payload)
        if overlap:
            raise ValueError(f"duplicate Surya document keys: {sorted(overlap)}")
        merged.update(payload)

    results: list[PageResult] = []
    for source_path in inputs:
        pages = merged.get(source_path.stem)
        if not isinstance(pages, list) or not pages:
            raise ValueError(f"missing Surya OCR result for {source_path.name}")
        for page_index, page in enumerate(pages, start=1):
            if not isinstance(page, dict):
                raise ValueError(f"invalid Surya page result for {source_path.name}")
            raw_blocks = page.get("blocks") or []
            blocks: list[dict[str, Any]] = []
            text_parts: list[str] = []
            for raw_block in raw_blocks:
                if not isinstance(raw_block, dict):
                    continue
                text = html_to_text(str(raw_block.get("html") or ""))
                if text:
                    text_parts.append(text)
                blocks.append(
                    {
                        "text": text,
                        "bbox": raw_block.get("bbox"),
                        "polygon": raw_block.get("polygon"),
                        "label": raw_block.get("label"),
                        "confidence": raw_block.get("confidence"),
                        "skipped": bool(raw_block.get("skipped", False)),
                        "error": bool(raw_block.get("error", False)),
                    }
                )
            results.append(
                PageResult(
                    model="surya2",
                    document_id=source_path.stem,
                    source_name=source_path.name,
                    page_number=page_index,
                    text="\n".join(text_parts).strip(),
                    blocks=blocks,
                    metadata={"image_bbox": page.get("image_bbox")},
                )
            )
    return results


def load_chandra_results(raw_dir: Path, inputs: Sequence[Path]) -> list[PageResult]:
    results: list[PageResult] = []
    for source_path in inputs:
        document_dir = raw_dir / source_path.stem
        markdown_path = document_dir / f"{source_path.stem}.md"
        metadata_path = document_dir / f"{source_path.stem}_metadata.json"
        if not markdown_path.is_file():
            raise ValueError(f"missing Chandra markdown result for {source_path.name}: {markdown_path}")
        if not metadata_path.is_file():
            raise ValueError(f"missing Chandra metadata for {source_path.name}: {metadata_path}")
        metadata = _load_json(metadata_path)
        if not isinstance(metadata, dict):
            raise ValueError(f"invalid Chandra metadata: {metadata_path}")
        num_pages = int(metadata.get("num_pages", 0))
        if num_pages != 1:
            raise ValueError(
                f"benchmark expects one image per input file; {source_path.name} produced {num_pages} pages"
            )
        page_metadata = (metadata.get("pages") or [{}])[0]
        results.append(
            PageResult(
                model="chandra2",
                document_id=source_path.stem,
                source_name=source_path.name,
                page_number=1,
                text=markdown_path.read_text(encoding="utf-8").strip(),
                blocks=[],
                metadata={
                    "page": page_metadata,
                    "token_count": metadata.get("total_token_count"),
                    "chunk_count": metadata.get("total_chunks"),
                },
            )
        )
    return results


def write_normalized(results: Iterable[PageResult], output_dir: Path) -> list[Path]:
    written: list[Path] = []
    for result in results:
        model_dir = output_dir / result.model
        model_dir.mkdir(parents=True, exist_ok=True)
        suffix = "" if result.page_number == 1 else f"__page_{result.page_number:03d}"
        base_name = f"{result.document_id}{suffix}"
        text_path = model_dir / f"{base_name}.txt"
        json_path = model_dir / f"{base_name}.json"
        text_path.write_text(result.text + ("\n" if result.text else ""), encoding="utf-8")
        payload = {
            "model": result.model,
            "document_id": result.document_id,
            "source_name": result.source_name,
            "page_number": result.page_number,
            "text": result.text,
            "blocks": result.blocks,
            "metadata": result.metadata,
        }
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        written.extend([text_path, json_path])
    return written


def summarize_model(results: Sequence[PageResult], runtime_seconds: float | None) -> dict[str, Any]:
    nonempty = sum(bool(result.text.strip()) for result in results)
    characters = sum(len(result.text) for result in results)
    block_count = sum(len(result.blocks) for result in results)
    return {
        "pages": len(results),
        "nonempty_pages": nonempty,
        "empty_pages": len(results) - nonempty,
        "nonempty_page_rate": nonempty / len(results) if results else 0.0,
        "characters": characters,
        "blocks": block_count,
        "runtime_seconds": runtime_seconds,
        "seconds_per_page": runtime_seconds / len(results) if runtime_seconds is not None and results else None,
    }


def run_command(command: Sequence[str]) -> float:
    started = time.perf_counter()
    subprocess.run(list(command), check=True)
    return time.perf_counter() - started


def build_surya_command(executable: str, input_dir: Path, raw_dir: Path, extra_args: Sequence[str]) -> list[str]:
    return [executable, str(input_dir), "--output_dir", str(raw_dir), *extra_args]


def build_chandra_command(
    executable: str,
    input_dir: Path,
    raw_dir: Path,
    method: str,
    extra_args: Sequence[str],
) -> list[str]:
    return [
        executable,
        str(input_dir),
        str(raw_dir),
        "--method",
        method,
        "--no-images",
        "--no-html",
        *extra_args,
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a research-only Surya 2 vs Chandra OCR 2 benchmark on local contract images."
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--surya-executable", default="surya_ocr")
    parser.add_argument("--chandra-executable", default="chandra")
    parser.add_argument("--chandra-method", choices=["hf", "vllm"], default="hf")
    parser.add_argument("--surya-extra-arg", action="append", default=[])
    parser.add_argument("--chandra-extra-arg", action="append", default=[])
    parser.add_argument(
        "--normalize-only",
        action="store_true",
        help="Do not invoke OCR CLIs; normalize existing raw outputs under output-dir/raw.",
    )
    args = parser.parse_args()

    inputs = discover_images(args.input_dir)
    raw_root = args.output_dir / "raw"
    normalized_root = args.output_dir / "normalized"
    raw_surya = raw_root / "surya2"
    raw_chandra = raw_root / "chandra2"
    raw_surya.mkdir(parents=True, exist_ok=True)
    raw_chandra.mkdir(parents=True, exist_ok=True)

    runtimes: dict[str, float | None] = {"surya2": None, "chandra2": None}
    if not args.normalize_only:
        runtimes["surya2"] = run_command(
            build_surya_command(
                args.surya_executable,
                args.input_dir,
                raw_surya,
                args.surya_extra_arg,
            )
        )
        runtimes["chandra2"] = run_command(
            build_chandra_command(
                args.chandra_executable,
                args.input_dir,
                raw_chandra,
                args.chandra_method,
                args.chandra_extra_arg,
            )
        )

    surya_results = load_surya_results(raw_surya, inputs)
    chandra_results = load_chandra_results(raw_chandra, inputs)
    write_normalized(surya_results, normalized_root)
    write_normalized(chandra_results, normalized_root)

    report = {
        "input_pages": len(inputs),
        "input_files": [path.name for path in inputs],
        "models": {
            "surya2": summarize_model(surya_results, runtimes["surya2"]),
            "chandra2": summarize_model(chandra_results, runtimes["chandra2"]),
        },
        "limitations": [
            "No OCR accuracy metric is claimed without a gold transcription.",
            "Runtime is comparable only when both models run on documented equivalent hardware and backend settings.",
            "Chandra CLI output is normalized from Markdown and does not expose block bounding boxes in this harness.",
            "Raw and normalized benchmark artifacts may contain PII and must remain outside version control.",
        ],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / "benchmark_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(report_path)


if __name__ == "__main__":
    main()
