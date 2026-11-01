import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import sys

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
sys.path.insert(0,str(ROOT/"scripts"))
from make_manifest import load_release_notes

HARNESS=r'''package dev.xarkon.link;
public final class ReleaseNotesCheck {
  static void yes(boolean v){if(!v)throw new AssertionError("Release notes filtering failed");}
  public static void main(String[] args){
    String legacy="QR LINK 0.3.62 · Проводник\n\n[+] Добавлены папки\n[=] Улучшена передача\n[+] Добавлены JVM-проверки\n\nРеальная работа с Android scoped storage, OTA со старой установленной версии и передача на Samsung S24 Ultra и iQOO требуют аппаратных испытаний. Лимит 30000 файлов на операцию сохраняется.";
    String visible=ReleaseNotes.visible(legacy);
    yes(visible.contains("[+] Добавлены папки"));
    yes(visible.contains("[=] Улучшена передача"));
    yes(!visible.contains("JVM"));
    yes(!visible.contains("scoped storage"));
    yes(!visible.contains("30000"));
    yes(!visible.contains("Samsung"));
    yes(ReleaseNotes.visible("Только внутренний отчёт").isEmpty());
    StringBuilder longNotes=new StringBuilder();
    for(int i=0;i<90;i++)longNotes.append("[=] Исправление "+i+" для всех экранов и длинных описаний передачи файлов номер "+i+"\\n");
    yes(longNotes.length()>6000);
    yes(ReleaseNotes.visible(longNotes.toString()).contains("Исправление 89"));
  }
}
'''

class ReleaseNotesPolicyTests(unittest.TestCase):
    def check(self,body,valid):
        with tempfile.TemporaryDirectory() as tmp:
            previous=os.getcwd()
            try:
                os.chdir(tmp)
                Path("release_notes").mkdir()
                Path("release_notes/v0.3.63.txt").write_text(body,encoding="utf-8")
                if valid:
                    self.assertIn("[+] ",load_release_notes("0.3.63"))
                else:
                    with self.assertRaises(SystemExit):
                        load_release_notes("0.3.63")
            finally:
                os.chdir(previous)

    def test_new_release_requires_ten_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous=os.getcwd()
            try:
                os.chdir(tmp)
                Path("release_notes").mkdir()
                path=Path("release_notes/v0.3.79.txt")
                def body(count):
                    return "QR LINK 0.3.79\\n" + "\\n".join(
                        f"[=] Исправлена самостоятельная функция номер {i}" for i in range(count))
                path.write_text(body(9),encoding="utf-8")
                with self.assertRaises(SystemExit):
                    load_release_notes("0.3.79")
                path.write_text(body(10),encoding="utf-8")
                self.assertEqual(load_release_notes("0.3.79").count("[=]"),10)
            finally:
                os.chdir(previous)

    def test_valid_user_facing_notes(self):
        self.check("QR LINK 0.3.63 · Улучшения\n\n[+] Новая функция\n[=] Исправлена очередь",True)

    def test_legacy_technical_tail_is_rejected(self):
        self.check("[+] Исправлен проводник\n\nРеальная работа с Android scoped storage требует аппаратных испытаний.",False)

    def test_marked_internal_qa_is_rejected(self):
        self.check("[+] Добавлены JVM-проверки",False)

    def test_duplicate_notes_are_rejected(self):
        self.check("[+] Исправлена очередь\n[+] Исправлена очередь",False)

    def test_wrong_version_heading_is_rejected(self):
        self.check("QR LINK 0.3.62 · Ошибка\n[+] Новая функция",False)

    def test_legacy_notes_filtered_by_android_java(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"ReleaseNotesCheck.java"
            source.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,
                str(JAVA/"ReleaseNotes.java"),str(source)],check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.ReleaseNotesCheck"],
                check=True,capture_output=True,text=True)

if __name__=="__main__":unittest.main()
