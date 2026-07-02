"""Tests for local configuration helpers."""

from __future__ import annotations

import unittest

from contract_checker.config import (
    API_KEY_SOURCE_ENVIRONMENT,
    API_KEY_SOURCE_MISSING,
    API_KEY_SOURCE_STREAMLIT_SECRETS,
    GEMINI_API_KEY_NAME,
    api_key_source_label,
    load_gemini_api_key_from_local_config,
)


class ConfigTests(unittest.TestCase):
    def test_loads_key_from_streamlit_secrets_first(self) -> None:
        config = load_gemini_api_key_from_local_config(
            secrets={GEMINI_API_KEY_NAME: "secret-key"},
            environ={GEMINI_API_KEY_NAME: "env-key"},
        )

        self.assertTrue(config.found)
        self.assertEqual(config.value, "secret-key")
        self.assertEqual(config.source, API_KEY_SOURCE_STREAMLIT_SECRETS)

    def test_falls_back_to_environment(self) -> None:
        config = load_gemini_api_key_from_local_config(
            secrets={},
            environ={GEMINI_API_KEY_NAME: "env-key"},
        )

        self.assertTrue(config.found)
        self.assertEqual(config.value, "env-key")
        self.assertEqual(config.source, API_KEY_SOURCE_ENVIRONMENT)

    def test_missing_key_returns_empty_config(self) -> None:
        config = load_gemini_api_key_from_local_config(secrets={}, environ={})

        self.assertFalse(config.found)
        self.assertEqual(config.value, "")
        self.assertEqual(config.source, API_KEY_SOURCE_MISSING)

    def test_blank_values_are_ignored(self) -> None:
        config = load_gemini_api_key_from_local_config(
            secrets={GEMINI_API_KEY_NAME: "   "},
            environ={GEMINI_API_KEY_NAME: " env-key "},
        )

        self.assertEqual(config.value, "env-key")
        self.assertEqual(config.source, API_KEY_SOURCE_ENVIRONMENT)

    def test_source_label_does_not_include_key_value(self) -> None:
        label = api_key_source_label(API_KEY_SOURCE_STREAMLIT_SECRETS)

        self.assertIn("secrets.toml", label)
        self.assertNotIn("GEMINI_API_KEY=", label)


if __name__ == "__main__":
    unittest.main()
