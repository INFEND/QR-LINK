from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
HARNESS=r'''package dev.xarkon.link;
public final class BrowserPathRulesCheck {
  public static void main(String[] args){
    if(!BrowserPathRules.isSameOrDescendant("DCIM/A/sub","DCIM/A"))throw new AssertionError();
    if(!BrowserPathRules.isSameOrDescendant("DCIM/A","DCIM/A"))throw new AssertionError();
    if(BrowserPathRules.isSameOrDescendant("DCIM/AB","DCIM/A"))throw new AssertionError();
    if(BrowserPathRules.isSameOrDescendant("DCIM/A2/sub","DCIM/A"))throw new AssertionError();
    if(!BrowserPathRules.isSameOrDescendant("DCIM",""))throw new AssertionError();
    if(BrowserPathRules.isSameOrDescendant(null,"DCIM"))throw new AssertionError();
  }
}
'''
class QueueIntegrityTests(unittest.TestCase):
    def test_segment_aware_folder_collapse(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"BrowserPathRulesCheck.java"
            source.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,str(JAVA/"BrowserPathRules.java"),
                str(source)],check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.BrowserPathRulesCheck"],
                check=True,capture_output=True,text=True)

    def test_atomic_deduplicated_queue(self):
        code=(JAVA/"FileCatalog.java").read_text(encoding="utf-8")
        self.assertIn("if(!seen.add(item.uri))continue;",code)
        self.assertIn("if(all.size()>=MAX_FOLDER_FILES)",code)
        self.assertIn("save(c,all);",code)

    def test_folder_selection_does_not_erase_existing_choices(self):
        code=(JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
        block=code.split("private void selectCurrentFolder(){",1)[1].split("private void clearSelection()",1)[0]
        self.assertNotIn("selected.clear()",block)
        self.assertIn("selected.put(folder.key(),folder)",block)

    def test_unreadable_entries_fail_closed_and_scan_is_cancelable(self):
        code=(JAVA/"FileCatalog.java").read_text(encoding="utf-8")
        self.assertIn("Thread.currentThread().isInterrupted()",code)
        self.assertIn("Папка содержит символическую ссылку",code)
        self.assertIn("Не удалось прочитать элемент папки",code)
        self.assertIn("Папка содержит элемент без идентификатора",code)

if __name__=="__main__":unittest.main()
