"""Cumulative OTA history: real Java merge, historical Python generator and UI contract."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
sys.path.insert(0,str(ROOT/"scripts"))
from ota_history import build_history, clean_notes

HARNESS=r'''package dev.xarkon.link;
import java.util.*;
public final class CumulativeNotesCheck {
    static void eq(String expected,String actual){
        if(!expected.equals(actual))throw new AssertionError("Expected "+expected+" got "+actual);
    }
    static void yes(boolean value){if(!value)throw new AssertionError("Invalid cumulative notes");}
    static OtaHistory.Entry e(long code,String name,String text){
        return new OtaHistory.Entry(code,name,text);
    }
    public static void main(String[] args){
        List<OtaHistory.Entry> entries=new ArrayList<>();
        for(int v=100;v<=108;v++)
            entries.add(e(v+5,"0.3."+v,"[=] Исправлена версия "+v));
        String combined=OtaHistory.merge(entries,104,113,"[=] Исправлена версия 108");
        yes(combined.startsWith("[=] Исправлена версия 100"));
        yes(combined.endsWith("[=] Исправлена версия 108"));
        yes(combined.split("\n").length==9);
        eq("[=] Исправлена версия 108",
            OtaHistory.merge(entries,112,113,"[=] Исправлена версия 108"));
        eq("[=] Исправлена версия 108",
            OtaHistory.merge(Collections.emptyList(),104,113,"[=] Исправлена версия 108"));
        entries.add(e(113,"0.3.108","[=] duplicate"));
        eq("[=] Исправлена версия 108",
            OtaHistory.merge(entries,104,113,"[=] Исправлена версия 108"));
        entries.remove(entries.size()-1);
        entries.remove(2); // Missing versionCode 107 -> no misleading partial history
        eq("[=] Исправлена версия 108",
            OtaHistory.merge(entries,106,113,"[=] Исправлена версия 108"));
        eq("[=] Исправлена версия 108",
            OtaHistory.merge(entries,104,113,"[=] Исправлена версия 108"));
        yes(ReleaseNotes.visible("[–] Удалена кнопка").contains("[–]"));
        yes(ReleaseNotes.visible("[=] **Важная** правка").contains("**Важная**"));
    }
}
'''

class CumulativeOtaTests(unittest.TestCase):
    def test_java_merge_real_javac(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness=Path(tmp)/"CumulativeNotesCheck.java"
            harness.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,
                            str(JAVA/"ReleaseNotes.java"),str(JAVA/"OtaHistory.java"),
                            str(harness)],check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.CumulativeNotesCheck"],
                           check=True,capture_output=True,text=True)

    def test_historical_filter_excludes_technical_text(self):
        source="[+] **Новая** функция\n[=] JVM-тесты\nТехническая информация\n[–] Удалена кнопка"
        self.assertEqual(clean_notes(source),
                         "[+] **Новая** функция\n[–] Удалена кнопка")

    def test_generator_version_codes_and_complete_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            import os
            old=os.getcwd()
            try:
                os.chdir(tmp)
                Path("release_notes").mkdir()
                tags=[f"v0.3.{v}" for v in range(85,111)]
                for v in range(85,111):
                    Path(f"release_notes/v0.3.{v}.txt").write_text(
                        f"QR LINK 0.3.{v}\n[=] Исправлена версия {v}\n",encoding="utf-8")
                def fake_run(cmd,**kwargs):
                    if cmd[:3]==["git","tag","--list"]:
                        return SimpleNamespace(returncode=0,stdout="\n".join(tags))
                    if cmd[:2]==["git","show"]:
                        version=int(cmd[2].split(":")[0].split(".")[-1])
                        return SimpleNamespace(returncode=0,stdout=f"versionCode = {version+5}\n")
                    raise AssertionError(cmd)
                with patch("ota_history.subprocess.run",side_effect=fake_run):
                    history=build_history("0.3.111",116,"[+] Новое окно обновления")
                self.assertEqual(len(history),27)
                self.assertEqual(history[0]["versionCode"],90)
                self.assertEqual(history[-1]["versionCode"],116)
                self.assertEqual(history[-1]["versionName"],"0.3.111")
                Path("release_notes/v0.3.99.txt").unlink()
                with patch("ota_history.subprocess.run",side_effect=fake_run):
                    with self.assertRaisesRegex(ValueError,"Missing historical"):
                        build_history("0.3.111",116,"[+] Новое окно")
            finally:
                os.chdir(old)

    def test_ui_contract(self):
        ui=(JAVA/"OtaProgressDialog.java").read_text(encoding="utf-8")
        main=(JAVA/"MainActivity.java").read_text(encoding="utf-8")
        manifest=(ROOT/"scripts/make_manifest.py").read_text(encoding="utf-8")
        self.assertIn("0xffffaa4d",ui)  # [=] is orange, independent of theme accent
        self.assertIn("0xff4dd69c",ui)
        self.assertIn("0xfff07878",ui)
        self.assertIn("startStrong",ui)
        # The old unconditional first-word bold made prepositions like «Для» bold.
        self.assertNotIn("actionStart",ui)
        self.assertNotIn("actionEnd",ui)
        self.assertIn("for(int[] span:strong)",ui)
        self.assertIn("notesFor(installedOtaCode())",main)
        self.assertIn('"history": build_history',manifest)

if __name__=="__main__":
    unittest.main()
