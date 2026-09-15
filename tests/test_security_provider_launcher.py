import unittest
from unittest.mock import patch

from tools import security_provider_experiment as experiment
from tools import security_provider_launcher as launcher


class SecurityProviderLauncherTests(unittest.TestCase):
    def test_menu_offers_36_37_and_35(self):
        self.assertEqual(launcher.MODEL_CHOICES, {
            "1": "gemini-3.6-flash",
            "2": "gemini-3.7-flash",
            "3": "gemini-3.5-flash",
        })

    def test_default_choice_is_36(self):
        output = []
        model = launcher.choose_model(input_fn=lambda _prompt: "", output_fn=output.append)
        self.assertEqual(model, "gemini-3.6-flash")

    def test_invalid_choice_reprompts_then_selects_37(self):
        answers = iter(["9", "2"])
        output = []
        model = launcher.choose_model(input_fn=lambda _prompt: next(answers), output_fn=output.append)
        self.assertEqual(model, "gemini-3.7-flash")
        self.assertIn("Invalid choice. Enter 1, 2, or 3.", output)

    def test_37_primary_keeps_only_35_fallback(self):
        with patch.object(experiment, "MODEL", experiment.DEFAULT_MODEL), \
             patch.object(experiment, "MODEL_ROUTE", (experiment.DEFAULT_MODEL, experiment.FALLBACK_MODEL)):
            launcher.configure_model("gemini-3.7-flash")
            self.assertEqual(experiment.MODEL, "gemini-3.7-flash")
            self.assertEqual(experiment.MODEL_ROUTE, ("gemini-3.7-flash", "gemini-3.5-flash"))

    def test_35_primary_has_no_duplicate_fallback(self):
        with patch.object(experiment, "MODEL", experiment.DEFAULT_MODEL), \
             patch.object(experiment, "MODEL_ROUTE", (experiment.DEFAULT_MODEL, experiment.FALLBACK_MODEL)):
            launcher.configure_model("gemini-3.5-flash")
            self.assertEqual(experiment.MODEL_ROUTE, ("gemini-3.5-flash",))

    def test_unknown_model_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported model"):
            launcher.configure_model("gemini-3.8-flash")


if __name__ == "__main__":
    unittest.main()
