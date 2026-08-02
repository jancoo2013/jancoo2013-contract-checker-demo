from pathlib import Path
import json


md_path = Path("docs/OCR_PROJECT_STATE.md")
text = md_path.read_text(encoding="utf-8")

old_header = "Последнее обновление: 2026-08-02, PR #161, `one-command-pii-mask-diagnostics-v0`."
new_header = "Последнее обновление: 2026-08-02, PR #162, `line-segmentation-giant-band-guard-v0`."
if text.count(old_header) != 1:
    raise SystemExit("state header anchor mismatch")
text = text.replace(old_header, new_header, 1)

old_section = "## 0. Изменение PR #161"
new_section = """## 0. Изменение PR #162

- Geometry-only diagnostic на repository-external трёхстраничном review pack измерил 46 mask candidates и `66.6%` фактически закрытой площади: `51.5%`, `70.4%` и `77.9%` по страницам.
- `38/46` candidates (`82.6%`) созданы broad-zone rules, а `30/46` содержат `segmentation_review`; diagnostic не содержал contract text, PII values, image IDs, hashes или изображений и не коммитился.
- Корневая причина крупных масок локализована в line segmentation: sparse foreground мог без ограничения расширять active band через сотни рядов и объединять несколько абзацев до PII classification.
- Sparse-row expansion теперь ограничен тремя рядами сверху и снизу. Одиночная тонкая вертикальная помеха остаётся отдельным rejected noise region и больше не расширяет соседние текстовые строки.
- Неразрешённый foreground band выше `max(180 px, 10% page height)` останавливает segmentation fail-closed с `unresolved oversized foreground band` вместо публикации гигантского candidate.
- Два новых synthetic tests проверяют разделение трёх строк при тонком вертикальном соединителе и fail-closed поведение при широком неразрешимом соединителе; полный line-segmenter suite прошёл `25/25`.
- GitHub Actions `OCR research runtime` run #62 прошёл: CPU training smoke и полный privacy/recognizer suite завершились успешно.
- Existing `2_review_pack` остаётся неизменным и не используется как доказательство исправления. После merge нужно собрать новый repository-external pack в новый output directory и повторить geometry-only diagnostic.
- Detector zone rules, mask expansion, renderer, Android reviewer, зависимости, внешние API, OCR, `active_track` и `next_step_id` не меняются.

### Зафиксированный PR #161"""
if text.count(old_section) != 1:
    raise SystemExit("PR 161 section anchor mismatch")
text = text.replace(old_section, new_section, 1)

old_row = "| Line segmentation | Python reference v0 | Детерминированные line regions, QA overlays, foreground accounting и fail-closed reasons | PII-классификация и general accuracy |"
new_row = "| Line segmentation | Python reference v0 + giant-band guard | Детерминированные line regions, QA overlays, foreground accounting; bounded sparse-row expansion и unresolved oversized-band fail-closed покрыты synthetic tests | Реальный rebuild нового review pack и повторная over-redaction диагностика |"
if text.count(old_row) != 1:
    raise SystemExit("line segmentation table anchor mismatch")
text = text.replace(old_row, new_row, 1)

old_blocker = "У владельца продукта есть repository-external трёхстраничный договор, в котором почти весь текст напечатан, а рукописными остаются только подписи. Из него уже собран exact review pack; hashes и размеры согласованы, а исправленный APK надёжно отображает все три страницы на Samsung A55. First-paint, индикатор загрузки, блокировка ложных касаний и локальное сохранение результата подтверждены. Визуально выявлено существенное over-redaction; PR #160 добавил безопасный geometry-only diagnostic, а PR #161 добавляет one-command runner без ручного переключения веток. Runner ещё нужно запустить на `2_review_pack` до изменения detector rules. Сам договор, normalized pages, manifests, derivatives, diagnostic output и review result не коммитятся в GitHub и не передаются внешним сервисам."
new_blocker = "У владельца продукта есть repository-external трёхстраничный договор, в котором почти весь текст напечатан, а рукописными остаются только подписи. Из него собран exact review pack; hashes и размеры согласованы, а APK надёжно отображает все три страницы на Samsung A55. Geometry-only diagnostic измерил 46 candidates и `66.6%` закрытой площади; `30/46` candidates содержат `segmentation_review`, что локализовало первичную причину excessive over-redaction в giant line bands. PR #162 добавляет bounded sparse-row expansion и fail-closed giant-band guard. Старый `2_review_pack` остаётся immutable; следующий operational check — собрать новый pack в новый output directory и повторить diagnostic до изменения detector zone rules. Сам договор, normalized pages, manifests, derivatives, diagnostic output и review result не коммитятся в GitHub и не передаются внешним сервисам."
if text.count(old_blocker) != 1:
    raise SystemExit("active blocker anchor mismatch")
text = text.replace(old_blocker, new_blocker, 1)
md_path.write_text(text, encoding="utf-8")

json_path = Path("docs/OCR_PROJECT_STATE.json")
state = json.loads(json_path.read_text(encoding="utf-8"))
expected = {
    "state_version": "privacy-ocr-2026-08-02-15",
    "last_recorded_pr": 161,
    "last_recorded_change": "one-command-pii-mask-diagnostics-v0",
    "active_track": "local-pii-redaction",
    "next_step_id": "controlled-pii-reviewer-pilot-v0",
}
for key, value in expected.items():
    if state.get(key) != value:
        raise SystemExit(f"JSON state anchor mismatch: {key}")
state["state_version"] = "privacy-ocr-2026-08-02-16"
state["last_recorded_pr"] = 162
state["last_recorded_change"] = "line-segmentation-giant-band-guard-v0"
state["updated_on"] = "2026-08-02"
json_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

Path("tools/codex_state_pr162.py").unlink()
