"""Focused tests for the Question Engine analysis-completeness gate."""

from __future__ import annotations

from pathlib import Path
import unittest

from contract_checker.question_engine.analysis_completeness import (
    AnalysisReadiness,
    DocumentGateStatus,
    audit_analysis_completeness,
)


_LEASE_BASE = """
הסכם שכירות בלתי מוגנת
בין המשכיר מצד אחד לבין השוכר מצד שני.
הואיל והמשכיר משכיר לשוכר דירה למגורים.
לפיכך הוסכם בין הצדדים כי השוכר ישלם דמי שכירות בכל חודש.
"""


class AnalysisCompletenessTests(unittest.TestCase):
    def test_unrelated_document_blocks_analysis(self) -> None:
        text = """
חשבונית מס עבור שירותי מחשוב ותחזוקה.
המסמך מפרט שעות עבודה, ציוד, תשלום ופרטי שירות שונים.
אין במסמך זה הסכם בין משכיר לשוכר ואין תיאור של דירה מושכרת.
"""

        result = audit_analysis_completeness(text)

        self.assertEqual(
            result.document_gate,
            DocumentGateStatus.DOCUMENT_TYPE_UNCONFIRMED,
        )
        self.assertEqual(result.readiness, AnalysisReadiness.BLOCKED)
        self.assertEqual(result.dependencies, ())

    def test_text_unusable_blocks_analysis(self) -> None:
        result = audit_analysis_completeness("abc", text_usable=True)

        self.assertEqual(result.document_gate, DocumentGateStatus.TEXT_UNUSABLE)
        self.assertEqual(result.readiness, AnalysisReadiness.BLOCKED)

    def test_unconfirmed_document_does_not_emit_dependency_findings(self) -> None:
        text = """
מדריך לקריאת הסכם שכירות מסביר מה המשכיר ומה השוכר צריכים לבדוק.
המאמר דן גם בשטר חוב ובכתב ערבות ובהבדלים בין בטוחות נפוצות.
זהו מידע כללי לציבור ולא נוסח הסכם בין צדדים מסוימים.
"""

        result = audit_analysis_completeness(text)

        self.assertEqual(
            result.document_gate,
            DocumentGateStatus.DOCUMENT_TYPE_UNCONFIRMED,
        )
        self.assertEqual(result.dependencies, ())

    def test_plain_rent_cheques_do_not_require_security_cheque_face(self) -> None:
        text = _LEASE_BASE + "\nהשוכר ישלם את דמי השכירות ב-12 צקים חודשיים."

        result = audit_analysis_completeness(text)

        self.assertEqual(
            result.document_gate,
            DocumentGateStatus.RENTAL_DOCUMENT_CONFIRMED,
        )
        self.assertEqual(result.readiness, AnalysisReadiness.READY)
        self.assertEqual(result.dependencies, ())

    def test_security_cheque_missing_makes_only_security_analysis_partial(self) -> None:
        text = _LEASE_BASE + "\nהשוכר ימסור למשכיר שיק ביטחון להבטחת התחייבויותיו."

        result = audit_analysis_completeness(text)

        self.assertEqual(result.readiness, AnalysisReadiness.PARTIAL)
        self.assertEqual(result.missing_dependency_ids, ("security_cheque",))
        self.assertEqual(result.dependencies[0].affected_domains, ("security",))

    def test_provided_security_cheque_restores_ready_state(self) -> None:
        text = _LEASE_BASE + "\nהשוכר ימסור למשכיר שיק ביטחון להבטחת התחייבויותיו."

        result = audit_analysis_completeness(
            text,
            provided_dependency_ids=("security_cheque",),
        )

        self.assertEqual(result.readiness, AnalysisReadiness.READY)
        self.assertEqual(result.missing_dependency_ids, ())

    def test_unlabeled_appendix_is_not_misread_as_hebrew_label(self) -> None:
        text = _LEASE_BASE + "\nמצב הדירה מפורט בנספח להסכם זה."

        result = audit_analysis_completeness(text)

        self.assertEqual(result.missing_dependency_ids, ("appendix",))

    def test_golden_contract_requires_only_detected_analysis_dependencies(self) -> None:
        root = Path(__file__).resolve().parents[1]
        fixture = (
            root
            / "research"
            / "question_engine"
            / "golden_contracts"
            / "contract_001_he.txt"
        ).read_text(encoding="utf-8")

        result = audit_analysis_completeness(fixture)

        self.assertEqual(
            result.document_gate,
            DocumentGateStatus.RENTAL_DOCUMENT_CONFIRMED,
        )
        self.assertEqual(result.readiness, AnalysisReadiness.PARTIAL)
        self.assertIn("appendix:ב", result.missing_dependency_ids)
        self.assertIn("security_cheque", result.missing_dependency_ids)

        complete = audit_analysis_completeness(
            fixture,
            provided_dependency_ids=("appendix:ב", "security_cheque"),
        )
        self.assertEqual(complete.readiness, AnalysisReadiness.READY)


if __name__ == "__main__":
    unittest.main()
