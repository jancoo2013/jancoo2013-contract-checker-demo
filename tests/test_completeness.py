"""Tests for deterministic completeness audit."""

from __future__ import annotations

import unittest

from contract_checker.completeness import audit_completeness
from contract_checker.evidence_blocks import build_evidence_blocks


NO_REFERENCES_TEXT = """
הסכם שכירות בלתי מוגנת

המשכיר משכיר לשוכר דירה למטרת מגורים בלבד.

דמי שכירות יהיו 3,500 ש"ח לחודש וישולמו בכל חודש.

המשכיר יהיה אחראי לתיקונים שאינם נגרמו על ידי השוכר.
"""


REFERENCED_DOCUMENTS_TEXT = """
הסכם שכירות בלתי מוגנת

נספח א' להסכם יכלול תנאים מיוחדים.

השוכר ימסור שיק ביטחון ושיקים לתשלום דמי השכירות.

הצדדים יחתמו על שטר חוב ועל כתב ערבות.

רשימת ציוד ופרוטוקול מסירה יצורפו במעמד מסירת הדירה.

עמוד חתימות הצדדים מצורף בסוף ההסכם.
"""


BLANK_TEMPLATE_TEXT = """
הסכם שכירות בלתי מוגנת

שם המשכיר: _________
שם השוכר: _________
כתובת הדירה: _________

המשכיר משכיר לשוכר דירה למטרת מגורים בלבד.
תקופת השכירות תהיה מיום ______ ועד ליום ______.
דמי שכירות יהיו ______ ש"ח לחודש.
השוכר יפקיד פיקדון בסך ______ ש"ח להבטחת התחייבויותיו.
השוכר ישלם חשמל, מים, ארנונה ועד בית לפי צריכה.
המשכיר יהיה אחראי לתיקון ליקויים מהותיים שאינם נגרמו על ידי השוכר.
השוכר רשאי להציע שוכר חלופי בכפוף להסכמת המשכיר שלא תסורב מטעמים בלתי סבירים.
חתימת המשכיר: _________
חתימת השוכר: _________
"""


COMPLETENESS_DISCLAIMER = (
    "Это не означает, что комплект договора полный. "
    "Сервис проверяет только загруженный и распознанный текст."
)


class CompletenessAuditTests(unittest.TestCase):
    def test_no_referenced_documents_found(self) -> None:
        audit = audit_completeness(NO_REFERENCES_TEXT)

        self.assertEqual(audit.status, "no_referenced_documents_found")
        self.assertEqual(audit.findings, [])
        self.assertIn("не найдено явных ссылок", audit.summary_ru)

    def test_referenced_documents_are_grouped_by_type_with_evidence_ids(self) -> None:
        audit = audit_completeness(REFERENCED_DOCUMENTS_TEXT)
        findings_by_type = {finding.document_type: finding for finding in audit.findings}

        self.assertEqual(audit.status, "referenced_documents_need_check")
        self.assertIn("appendix", findings_by_type)
        self.assertIn("checks", findings_by_type)
        self.assertIn("promissory_note", findings_by_type)
        self.assertIn("guarantee", findings_by_type)
        self.assertIn("inventory", findings_by_type)
        self.assertIn("handover_protocol", findings_by_type)
        self.assertIn("signature_pages", findings_by_type)
        self.assertEqual(findings_by_type["promissory_note"].severity, "red")
        self.assertEqual(findings_by_type["appendix"].evidence_block_ids, ["P1-B02"])
        self.assertEqual(findings_by_type["checks"].evidence_block_ids, ["P1-B03"])
        self.assertIn("P1-B04", findings_by_type["guarantee"].evidence_block_ids)

    def test_accepts_prebuilt_evidence_blocks(self) -> None:
        blocks = build_evidence_blocks(REFERENCED_DOCUMENTS_TEXT)
        audit = audit_completeness(REFERENCED_DOCUMENTS_TEXT, blocks=blocks)

        self.assertTrue(audit.findings)
        self.assertTrue(all(finding.evidence_block_ids for finding in audit.findings))

    def test_text_unusable_status(self) -> None:
        audit = audit_completeness("abc", text_usable=False)

        self.assertEqual(audit.status, "text_unusable")
        self.assertEqual(audit.findings, [])

    def test_blank_template_is_not_text_unusable_for_completeness(self) -> None:
        audit = audit_completeness(BLANK_TEMPLATE_TEXT, text_usable=True)

        self.assertNotEqual(audit.status, "text_unusable")

    def test_summaries_always_include_completeness_disclaimer(self) -> None:
        audits = [
            audit_completeness(NO_REFERENCES_TEXT),
            audit_completeness(REFERENCED_DOCUMENTS_TEXT),
            audit_completeness("abc", text_usable=False),
        ]

        for audit in audits:
            self.assertIn(COMPLETENESS_DISCLAIMER, audit.summary_ru)

    def test_findings_do_not_store_source_text(self) -> None:
        audit = audit_completeness(REFERENCED_DOCUMENTS_TEXT)
        report_text = repr(audit)

        self.assertNotIn("נספח א' להסכם יכלול תנאים מיוחדים", report_text)
        self.assertNotIn("הצדדים יחתמו על שטר חוב ועל כתב ערבות", report_text)
        self.assertNotIn("רשימת ציוד ופרוטוקול מסירה יצורפו", report_text)
        self.assertIn("P1-B02", report_text)

    def test_cautious_language_has_no_verdict_or_signing_instruction(self) -> None:
        audit = audit_completeness(REFERENCED_DOCUMENTS_TEXT)
        text = " ".join(
            [audit.summary_ru]
            + [
                f"{finding.explanation_ru} {finding.question_ru}"
                for finding in audit.findings
            ]
        ).lower()

        forbidden = (
            "документ точно отсутствует",
            "договор недействителен",
            "нельзя подписывать",
            "можно подписывать",
        )
        for phrase in forbidden:
            self.assertNotIn(phrase, text)
        self.assertIn("проверьте", text)


if __name__ == "__main__":
    unittest.main()
