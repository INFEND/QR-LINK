"""Prevent cumulative OTA notes from collapsing to only the newest release."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "app/src/main/java/dev/xarkon/link"
sys.path.insert(0, str(ROOT / "scripts"))
from ota_history import build_history, clean_notes

HARNESS = r'''package dev.xarkon.link;
import java.util.*;
public final class OtaSkippedVersionsCheck {
    static void yes(boolean ok) { if (!ok) throw new AssertionError("Incomplete cumulative OTA notes"); }
    static OtaHistory.Entry entry(int v) {
        return new OtaHistory.Entry(v + 5, "0.3." + v, "[=] Изменение 0.3." + v);
    }
    public static void main(String[] args) {
        List<OtaHistory.Entry> entries = new ArrayList<>();
        for (int v = 85; v <= 120; v++) entries.add(entry(v));
        String five = OtaHistory.merge(entries, 120, 125, "[=] Изменение 0.3.120");
        String[] lines = five.split("\\n");
        yes(lines.length == 5);
        for (int i = 0; i < 5; i++)
            yes(lines[i].equals("[=] Изменение 0.3." + (116+i)));
        // Corrupt notes from a version already installed must not erase relevant entries.
        entries.set(0, new OtaHistory.Entry(90, "0.3.85", "[=] JVM тесты"));
        yes(OtaHistory.merge(entries, 120, 125, "[=] Изменение 0.3.120").split("\\n").length == 5);
        // One skipped version also works, with no duplicate.
        List<OtaHistory.Entry> upto116 = new ArrayList<>(entries.subList(0,32));
        yes(OtaHistory.merge(upto116,120,121,"[=] Изменение 0.3.116").equals("[=] Изменение 0.3.116"));
        // Large history has no fixed 500-entry cut-off.
        List<OtaHistory.Entry> many = new ArrayList<>();
        for (int v = 1; v <= 1200; v++)
            many.add(new OtaHistory.Entry(v, "1.0."+v, "[+] Выпуск "+v));
        yes(OtaHistory.merge(many, 1, 1200, "[+] Выпуск 1200").split("\\n").length == 1199);
        // Missing release is not silently reported as a complete sequence.
        entries.remove(34); // 0.3.119
        yes(OtaHistory.merge(entries,120,125,"[=] Изменение 0.3.120")
            .equals("[=] Изменение 0.3.120"));
    }
}
'''

class MissedOtaReleasesTests(unittest.TestCase):
    def test_background_caches_the_same_complete_history_as_manual_check(self):
        background=(JAVA/"BackgroundUpdateJob.java").read_text(encoding="utf-8")
        main=(JAVA/"MainActivity.java").read_text(encoding="utf-8")
        updater=(JAVA/"UpdateManager.java").read_text(encoding="utf-8")
        self.assertIn('putString("ota_available_notes",release.notesFor(installed))',background)
        self.assertNotIn('putString("ota_available_notes",release.notes)',background)
        self.assertIn('putLong("ota_available_notes_base_code",installed)',background)
        self.assertIn('putLong("ota_available_notes_base_code",installedOtaCode())',main)
        self.assertIn('if(prefs().getLong("ota_available_notes_base_code",-1L)!=installed)',main)
        self.assertIn('ui.offer(r.versionName,r.notesFor(installedOtaCode())',main)
        self.assertNotIn('versions.length()<=500',updater)

    def test_merge_from_115_to_120_and_over_500_intermediate_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness=Path(tmp)/"OtaSkippedVersionsCheck.java"
            harness.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,
                str(JAVA/"ReleaseNotes.java"),str(JAVA/"OtaHistory.java"),
                str(harness)],check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.OtaSkippedVersionsCheck"],
                check=True,capture_output=True,text=True)

    def test_generator_preserves_real_116_to_120_notes(self):
        # The exact releases in the user report must all exist in the repository.
        for v in range(116,121):
            notes=clean_notes((ROOT/f"release_notes/v0.3.{v}.txt").read_text(encoding="utf-8"))
            self.assertTrue(notes.startswith(("[-] ","[=] ","[+] ","[–] ")),v)
        with tempfile.TemporaryDirectory() as tmp:
            old=os.getcwd()
            try:
                os.chdir(tmp)
                Path("release_notes").mkdir()
                tags=[f"v0.3.{v}" for v in range(85,120)]
                for v in range(85,120):
                    Path(f"release_notes/v0.3.{v}.txt").write_text(
                        f"QR LINK 0.3.{v}\n[=] Выпуск {v}\n",encoding="utf-8")
                def fake_run(command,**kwargs):
                    if command[:3] == ["git","tag","--list"]:
                        return SimpleNamespace(returncode=0,stdout="\n".join(tags))
                    if command[:2] == ["git","show"]:
                        v=int(command[2].split(":")[0].split(".")[-1])
                        return SimpleNamespace(returncode=0,stdout=f"versionCode = {v+5}\n")
                    raise AssertionError(command)
                with patch("ota_history.subprocess.run",side_effect=fake_run):
                    history=build_history("0.3.120",125,"[=] Выпуск 120")
                selected=[item["versionName"] for item in history if item["versionCode"]>120]
                self.assertEqual(selected,[f"0.3.{v}" for v in range(116,121)])
            finally:
                os.chdir(old)

if __name__ == "__main__":
    unittest.main()
