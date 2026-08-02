from pathlib import Path

path = Path("docs/OCR_PROJECT_STATE.md")
text = path.read_text(encoding="utf-8")
old = "Standalone launch, открытие реального трёхстраничного pack, first-paint, loading/touch gate и локальное сохранение результата на Samsung A55 подтверждены. Следующий operational gate — копирование review JSONL на компьютер, проверка exact hashes и controlled human pilot."
new = "Standalone launch, открытие реального трёхстраничного pack, first-paint, loading/touch gate и локальное сохранение результата на Samsung A55 подтверждены. Копирование review JSONL, exact-hash readback и controlled human pilot остаются недоказанными, но после PR #163 отложены до появления evidence-based candidates и нового review pack."
if text.count(old) != 1:
    raise SystemExit(f"state gate anchor count: {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
Path(__file__).unlink()
