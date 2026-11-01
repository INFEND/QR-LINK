"""User policy: from v0.3.85 one evidenced product change can ship OTA."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import make_manifest
import check_release_changes as gate


class NoMinimumReleaseSizeTests(unittest.TestCase):
    NOTE="[=] Исправлена ошибка выбора файла"
    PATH="app/src/main/java/dev/xarkon/link/FileBrowserActivity.java"
    ANCHOR="public void handleCompleteSingleUserFix() { return; }"

    def test_historical_minimum_unchanged(self):
        self.assertTrue(make_manifest.requires_ten_changes("0.3.78"))
        self.assertTrue(make_manifest.requires_ten_changes("0.3.84"))
        self.assertEqual(gate.minimum_for_version("0.3.84"),10)

    def test_minimum_is_removed_after_084(self):
        for version in ("0.3.85","0.3.86","0.4.0","1.0.0"):
            self.assertFalse(make_manifest.requires_ten_changes(version))
            self.assertEqual(gate.minimum_for_version(version),1)

    def test_single_user_visible_change_requires_no_special_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            old=os.getcwd()
            try:
                os.chdir(tmp)
                Path("release_notes").mkdir()
                Path("release_notes/v0.3.85.txt").write_text(
                    "QR LINK 0.3.85\n\n"+self.NOTE+"\n",encoding="utf-8")
                self.assertIn(self.NOTE,make_manifest.load_release_notes("0.3.85"))
            finally:
                os.chdir(old)
        evidence={"entries":[{"note":self.NOTE,"path":self.PATH,"changed_line":self.ANCHOR}]}
        self.assertEqual(gate.validate_evidence([self.NOTE],evidence,
            lambda path:{self.ANCHOR},
            minimum_changes=gate.minimum_for_version("0.3.85")),1)

    def test_empty_notes_still_rejected(self):
        evidence={"entries":[]}
        with self.assertRaises(ValueError):
            gate.validate_evidence([],evidence,lambda path:set(),minimum_changes=1)

    def test_missing_or_fake_source_evidence_still_rejected(self):
        evidence={"entries":[{"note":self.NOTE,"path":self.PATH,"changed_line":self.ANCHOR}]}
        with self.assertRaisesRegex(ValueError,"не найдено"):
            gate.validate_evidence([self.NOTE],evidence,lambda path:set(),minimum_changes=1)
        evidence["entries"][0]["path"]="docs/QA_CHECKLIST_RU.md"
        with self.assertRaisesRegex(ValueError,"Недопустимое"):
            gate.validate_evidence([self.NOTE],evidence,lambda path:{self.ANCHOR},minimum_changes=1)

    def test_duplicate_notes_still_rejected_by_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            old=os.getcwd()
            try:
                os.chdir(tmp)
                Path("release_notes").mkdir()
                Path("release_notes/v0.3.85.txt").write_text(
                    "QR LINK 0.3.85\n"+self.NOTE+"\n"+self.NOTE,encoding="utf-8")
                with self.assertRaises(SystemExit):
                    make_manifest.load_release_notes("0.3.85")
            finally:
                os.chdir(old)


if __name__=="__main__":
    unittest.main()
