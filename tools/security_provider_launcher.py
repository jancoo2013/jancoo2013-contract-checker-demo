from __future__ import annotations

from tools import security_provider_experiment as experiment

MODEL_CHOICES = {
    "1": "gemini-3.6-flash",
    "2": "gemini-3.7-flash",
    "3": "gemini-3.5-flash",
}
DEFAULT_CHOICE = "1"


def choose_model(input_fn=input, output_fn=print):
    output_fn("Choose Gemini primary model:")
    output_fn("  1) gemini-3.6-flash")
    output_fn("  2) gemini-3.7-flash")
    output_fn("  3) gemini-3.5-flash")
    while True:
        choice = input_fn("Model [1]: ").strip() or DEFAULT_CHOICE
        model = MODEL_CHOICES.get(choice)
        if model:
            return model
        output_fn("Invalid choice. Enter 1, 2, or 3.")


def configure_model(model):
    if model not in MODEL_CHOICES.values():
        raise ValueError(f"Unsupported model: {model}")
    experiment.MODEL = model
    experiment.MODEL_ROUTE = tuple(dict.fromkeys((model, experiment.FALLBACK_MODEL)))


def main():
    model = choose_model()
    configure_model(model)
    return experiment.main()


if __name__ == "__main__":
    raise SystemExit(main())
