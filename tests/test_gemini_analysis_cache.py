"""Tests for session-scoped Gemini analysis cache helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from contract_checker import gemini_engine


class GeminiAnalysisCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        gemini_engine._ANALYSIS_RAW_TEXT_CACHE.clear()

    def test_analysis_cache_is_scoped_by_streamlit_session(self) -> None:
        with patch.object(gemini_engine, "_streamlit_session_id", return_value="session-a"):
            gemini_engine._analysis_cache_set("cache-key", "raw-response-a")
            self.assertEqual(gemini_engine._analysis_cache_get("cache-key"), "raw-response-a")

        with patch.object(gemini_engine, "_streamlit_session_id", return_value="session-b"):
            self.assertIsNone(gemini_engine._analysis_cache_get("cache-key"))

    def test_analysis_cache_is_disabled_without_streamlit_session(self) -> None:
        with patch.object(gemini_engine, "_streamlit_session_id", return_value=None):
            gemini_engine._analysis_cache_set("cache-key", "raw-response-a")
            self.assertIsNone(gemini_engine._analysis_cache_get("cache-key"))

        self.assertEqual(gemini_engine._ANALYSIS_RAW_TEXT_CACHE, {})


if __name__ == "__main__":
    unittest.main()
