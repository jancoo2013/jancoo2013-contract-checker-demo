from __future__ import annotations

import json
import os
from pathlib import Path


CHANGE = "evidence-based-pii-detector-contract-v0"
NEXT_STEP = "pii-candidate-evidence-schema-v0"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"{label} anchor count: {text.count(old)}")
    return text.replace(old, new, 1)


def update_architecture() -> None:
    path = Path("docs/ARCHITECTURE.md")
    text = path.read_text(encoding="utf-8")
    old = (
        "Do not blindly redact a full page only because one PII-like label appears on it. "
        "Prefer row/zone-level masking with conservative expansion around the sensitive value.\n\n"
        "The annotation and verification target is a PII region or mask, not an exact full-line transcript."
    )
    new = (
        "Do not blindly redact a full page only because one PII-like label appears on it. "
        "Prefer row/zone-level masking with conservative expansion around the sensitive value.\n\n"
        "### Evidence rule for automatic masks\n\n"
        "Page position, page number, first/last-page status, right alignment, short-line geometry, "
        "or digit presence are weak context only. None of them may create an automatic mask by itself. "
        "An automatic mask requires direct value evidence, marker-to-value/field relation, or validated "
        "handwriting/signature/stamp evidence. Zone-only findings may be routed to local review but must "
        "not be exported as production masks. The binding decision and evaluation contract is "
        "`docs/PII_EVIDENCE_DETECTOR_V1.md`.\n\n"
        "Detector evaluation must be grouped by whole contract. Pages or lines from one contract must "
        "not be split between development and held-out evaluation, and contract-specific coordinates "
        "or one-off exceptions are forbidden.\n\n"
        "The annotation and verification target is a PII region or mask, not an exact full-line transcript."
    )
    text = replace_once(text, old, new, "architecture evidence rule")
    path.write_text(text, encoding="utf-8")


def update_pipeline() -> None:
    path = Path("docs/CUSTOM_OCR_PIPELINE.md")
    text = path.read_text(encoding="utf-8")
    old = (
        "The local privacy layer may use layout, known page zones, Hebrew field markers, digit patterns, "
        "signatures, handwriting cues, and conservative region expansion. It must not depend on exact "
        "full-page transcription to decide whether a region is sensitive.\n\n"
        "An external service is downstream of the privacy boundary only."
    )
    new = (
        "The local privacy layer may use layout, known page zones, Hebrew field markers, digit patterns, "
        "signatures, handwriting cues, and conservative region expansion. It must not depend on exact "
        "full-page transcription to decide whether a region is sensitive.\n\n"
        "Known page zones are weak context only. A line's vertical position or page role must never be "
        "the sole reason for an automatic mask. `marker_layout_baseline_v0` is retained only as a "
        "diagnostic comparator; production candidates must carry explicit evidence under "
        "`docs/PII_EVIDENCE_DETECTOR_V1.md`.\n\n"
        "An external service is downstream of the privacy boundary only."
    )
    text = replace_once(text, old, new, "pipeline zone rule")

    old = (
        "- page-level privacy pass rate: pages with no missed or partially exposed PII.\n\n"
        "A visually plausible mask or a correct detection of the label `ת.ז.` is not enough"
    )
    new = (
        "- page-level privacy pass rate: pages with no missed or partially exposed PII.\n\n"
        "Evaluation splits are made by whole contract, not by page or line. All pages from one contract "
        "remain in one split; known template families should also remain grouped where feasible. A new "
        "contract is a held-out generalization test, not permission to add contract-specific thresholds, "
        "coordinates, or exceptions. Metrics must be reported per contract as well as in aggregate.\n\n"
        "A visually plausible mask or a correct detection of the label `ת.ז.` is not enough"
    )
    text = replace_once(text, old, new, "pipeline evaluation split")
    path.write_text(text, encoding="utf-8")


def update_state(pr_number: int) -> None:
    path = Path("docs/OCR_PROJECT_STATE.md")
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "Последнее обновление: 2026-08-02, PR #162, `line-segmentation-giant-band-guard-v0`.",
        f"Последнее обновление: 2026-08-02, PR #{pr_number}, `{CHANGE}`.",
        "state header",
    )
    text = replace_once(
        text,
        "Единственный следующий шаг: `controlled-pii-reviewer-pilot-v0`.",
        f"Единственный следующий шаг: `{NEXT_STEP}`.",
        "state next step header",
    )
    old = "## 0. Изменение PR #162\n"
    new = f"""## 0. Изменение PR #{pr_number}

- Владелец продукта остановил подгонку fixed page-zone thresholds под один трёхстраничный договор: такой путь не обобщается на другие шаблоны, рукописные поля и расположение реквизитов.
- Добавлен binding contract `docs/PII_EVIDENCE_DETECTOR_V1.md`: положение строки, номер страницы и first/last-page role являются только weak context и никогда не достаточны для `auto_mask`.
- `marker_layout_baseline_v0` заморожен как diagnostic comparator и не считается production detector policy.
- Production candidate должен нести явное evidence: direct value pattern, marker-to-value/field relation либо validated handwriting/signature/stamp signal; zone-only candidate может быть только `local_review` или `preserve`.
- Evaluation делится по целым договорам: страницы одного договора не смешиваются между development и held-out split; известные template families группируются по возможности; contract-specific coordinates и one-off exceptions запрещены.
- Controlled Android reviewer и repository-external pilot не удаляются, но откладываются до появления evidence-bearing candidates: измерять human metrics на заведомо непригодной zone-only policy нецелесообразно.
- Единственный следующий шаг изменён на `{NEXT_STEP}`: строгая candidate/evidence schema и validation, которая технически запрещает zone-only `auto_mask`.
- Runtime, renderer, Android APK, маски существующего pack, зависимости, OCR, внешние API и privacy boundary не меняются.

### Зафиксированный PR #162
"""
    text = replace_once(text, old, new, "state PR section")

    old = (
        "Единственный product blocker перед metrics, улучшением detector или Android-port — отсутствие "
        "controlled human pilot и измеримых ошибок текущего Python baseline:\n\n"
        "- `missed_pii`;\n"
        "- `incomplete_mask`;\n"
        "- `over_redaction`.\n\n"
        "До pilot нельзя утверждать, что current candidates корректны, маски полностью закрывают PII "
        "или сохраняют достаточно юридического текста."
    )
    new = (
        "Текущий product blocker — candidate policy не переносится между договорами: "
        "`marker_layout_baseline_v0` создаёт broad-zone findings по фиксированным вертикальным зонам "
        "каждой страницы и поэтому не годится для production metrics или Android automasking.\n\n"
        "Human pilot остаётся обязательным позже для `missed_pii`, `incomplete_mask` и `over_redaction`, "
        "но сначала candidates должны нести проверяемое evidence и запрещать zone-only `auto_mask`."
    )
    text = replace_once(text, old, new, "state blocker")

    old = (
        "PR #162 добавляет bounded sparse-row expansion и fail-closed giant-band guard. "
        "Старый `2_review_pack` остаётся immutable; следующий operational check — собрать новый pack "
        "в новый output directory и повторить diagnostic до изменения detector zone rules."
    )
    new = (
        f"PR #162 добавил bounded sparse-row expansion и fail-closed giant-band guard. PR #{pr_number} "
        "фиксирует более глубокую причину: fixed page zones применяются ко всем страницам и ведут к "
        "переобучению на одном шаблоне. Старый `2_review_pack` остаётся immutable; новый pack не "
        "собирается до evidence-bearing candidate schema и следующего detector implementation slice."
    )
    text = replace_once(text, old, new, "state pilot paragraph")

    start = text.index("## 11. Единственный следующий шаг\n")
    end = text.index("\n## 12. Правила работы и восстановления новой сессии", start)
    section = f"""## 11. Единственный следующий шаг

**`{NEXT_STEP}`: определить строгую schema для evidence-bearing PII candidates и validation, которая не позволяет page-zone context самостоятельно создать `auto_mask`.**

Граница шага:

1. Добавить отдельный schema/validator component для candidate geometry, PII class, disposition и evidence records.
2. Поддержать dispositions `auto_mask`, `local_review` и `preserve`.
3. Поддержать evidence families: direct value, marker, visual sensitive-region, relation и weak layout context.
4. Валидатор обязан отклонять `auto_mask`, если единственное evidence — page position, page role, alignment, short-line geometry или generic digit presence.
5. Использовать только synthetic/non-identifying fixtures; реальные contract text, images и PII не коммитить.
6. Не менять в этом PR текущий detector output, renderer, Android reviewer, APK, внешние API или production runtime.
7. Следующий implementation slice после schema — deterministic direct-pattern evidence, а не новая настройка процентов страницы.
8. Controlled human pilot возобновляется после появления evidence-based candidates и нового repository-external pack.
"""
    text = text[:start] + section + text[end:]
    path.write_text(text, encoding="utf-8")

    json_path = Path("docs/OCR_PROJECT_STATE.json")
    state = json.loads(json_path.read_text(encoding="utf-8"))
    state.update(
        {
            "state_version": "privacy-ocr-2026-08-02-17",
            "next_step_id": NEXT_STEP,
            "next_step_summary": (
                "Define and validate an evidence-bearing PII candidate schema with auto_mask, "
                "local_review, and preserve dispositions; page-zone context alone must never "
                "validate auto_mask."
            ),
            "last_recorded_pr": pr_number,
            "last_recorded_change": CHANGE,
            "updated_on": "2026-08-02",
        }
    )
    json_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    pr_number = int(os.environ["PR_NUMBER"])
    update_architecture()
    update_pipeline()
    update_state(pr_number)
    Path(__file__).unlink()


if __name__ == "__main__":
    main()
