"""Regression tests for the eleven-task early OTA release exception."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_release_changes as gate
from make_manifest import load_release_notes
from release_exceptions import (
    PRIORITY_TASK_IDS, declared_completions, qa_status, require_new_completion,
)


class PriorityReleaseExceptionTests(unittest.TestCase):
    BEFORE = "| U25 | Сообщения | Тематические окна | **Не готово** | Ожидает кода |\n"
    AFTER = "| U25 | Сообщения | Тематические окна | **Готово** | Реализация внесена |\n"
    NOTE = "[=] Все системные сообщения заменены тематическими"
    PATH = "app/src/main/java/dev/xarkon/link/UiNotices.java"
    LINE = "public void showThemedMessageAfterReplacingDialog() {"

    def evidence(self, ids=("U25",), entry_task="U25", path=None):
        return {
            "completed_tasks": list(ids),
            "entries": [{
                "note": self.NOTE, "path": path or self.PATH,
                "changed_line": self.LINE, "task_id": entry_task,
            }],
        }

    def verify(self, evidence, qa=None):
        return gate.validate_evidence(
            [self.NOTE], evidence,
            lambda p: {self.LINE},
            qa or (self.BEFORE, self.AFTER),
        )

    def test_exactly_eleven_allowed_tasks(self):
        self.assertEqual(PRIORITY_TASK_IDS, {
            "T07", "T08", "T15", "T16", "F17", "F18",
            "O14", "O17", "U02", "U06", "U25",
        })

    def test_verified_one_task_can_release_with_one_change(self):
        self.assertEqual(self.verify(self.evidence()), 1)

    def test_status_is_parsed_from_all_qa_table_shapes(self):
        self.assertEqual(qa_status(self.BEFORE, "U25"), "Не готово")
        self.assertEqual(qa_status(self.AFTER, "U25"), "Готово")
        self.assertEqual(
            qa_status("| T07 | Save block confirmations | **Не готово** | details |\n", "T07"),
            "Не готово",
        )

    def test_standard_short_release_is_blocked(self):
        evidence = self.evidence(ids=(), entry_task=None)
        del evidence["entries"][0]["task_id"]
        with self.assertRaisesRegex(ValueError, "минимум 10"):
            self.verify(evidence)

    def test_unfinished_priority_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "ещё не завершена"):
            self.verify(self.evidence(), (self.BEFORE, self.BEFORE))

    def test_already_completed_in_previous_tag_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "уже была готова"):
            self.verify(self.evidence(), (self.AFTER, self.AFTER))

    def test_missing_prior_tag_qa_is_blocked(self):
        with self.assertRaises(ValueError):
            gate.validate_evidence([self.NOTE], self.evidence(),
                                   lambda p: {self.LINE})

    def test_missing_task_link_is_blocked(self):
        evidence = self.evidence()
        del evidence["entries"][0]["task_id"]
        with self.assertRaisesRegex(ValueError, "Нет доказательства"):
            self.verify(evidence)

    def test_unrelated_task_claim_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "не применяется"):
            self.verify(self.evidence(ids=("F24",), entry_task="F24"))

    def test_two_claims_need_two_distinct_code_anchors(self):
        with self.assertRaisesRegex(ValueError, "Нет доказательства"):
            self.verify(self.evidence(ids=("U25", "T08")))

    def test_fake_diff_anchor_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "не найдено в diff"):
            gate.validate_evidence(
                [self.NOTE], self.evidence(), lambda p: set(),
                (self.BEFORE, self.AFTER),
            )

    def test_docs_or_tests_are_not_product_code(self):
        with self.assertRaisesRegex(ValueError, "Недопустимое доказательство"):
            self.verify(self.evidence(path="docs/QA_CHECKLIST_RU.md"))

    def test_duplicate_or_invalid_claims_are_blocked(self):
        with self.assertRaises(ValueError):
            declared_completions({"completed_tasks": ["U25", "U25"]})
        with self.assertRaises(ValueError):
            declared_completions({"completed_tasks": ["U25", "O01"]})
        with self.assertRaises(ValueError):
            declared_completions({"completed_tasks": "U25"})

    def test_manifest_rejects_short_release_without_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.getcwd()
            try:
                os.chdir(tmp)
                Path("release_notes").mkdir()
                Path("release_notes/v0.3.83.txt").write_text(
                    "QR LINK 0.3.83\n" + self.NOTE, encoding="utf-8")
                with self.assertRaises(SystemExit):
                    load_release_notes("0.3.83")
                Path("release_notes/v0.3.83.evidence.json").write_text(
                    json.dumps(self.evidence()), encoding="utf-8")
                self.assertIn(self.NOTE, load_release_notes("0.3.83"))
                Path("release_notes/v0.3.83.evidence.json").write_text(
                    json.dumps({"completed_tasks": ["U21"]}), encoding="utf-8")
                with self.assertRaises(SystemExit):
                    load_release_notes("0.3.83")
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
