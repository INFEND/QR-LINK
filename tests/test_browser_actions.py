"""Executable breadcrumb checks and UI state regression guardrails."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
HARNESS=r'''package dev.xarkon.link;
public final class BrowserBreadcrumbsCheck {
  private static void eq(String actual,String expected){if(!actual.equals(expected))throw new AssertionError(actual+" != "+expected);}
  public static void main(String[] args){
    eq(BrowserBreadcrumbs.format(null),"Устройство");
    eq(BrowserBreadcrumbs.format("/storage/emulated/0"),"Устройство");
    eq(BrowserBreadcrumbs.format("/storage/emulated/0/DCIM/Camera/"),"Устройство › DCIM › Camera");
    eq(BrowserBreadcrumbs.format("Download/Photos/2026"),"Устройство › Download › Photos › 2026");
    eq(BrowserBreadcrumbs.format("/0/Pictures"),"Устройство › Pictures");
    eq(BrowserBreadcrumbs.format("Documents/../Pictures"),"Устройство › Documents › Pictures");
  }
}
'''

class BrowserActionsTests(unittest.TestCase):
    def test_breadcrumbs_java(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"BrowserBreadcrumbsCheck.java"
            source.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,str(JAVA/"BrowserBreadcrumbs.java"),str(source)],check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.BrowserBreadcrumbsCheck"],check=True,capture_output=True,text=True)

    def test_folder_selection_is_recursive_not_page_bound(self):
        src=(JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
        self.assertIn('ВЫБРАТЬ ПАПКУ',src)
        self.assertIn('selectPage.setOnClickListener(v->selectCurrentFolder())',src)
        self.assertIn('selected.put(folder.key(),folder)',src)
        self.assertIn('FileCatalog.fromLocalFolder(this,e.localFile,e.path)',src)
        self.assertIn('FileCatalog.fromDocumentFolder(this,e.tree,e.docId,e.name)',src)
        self.assertNotIn('selectVisiblePage()',src)
        self.assertNotIn('Корень внутренней памяти /0. Нажмите',src)
        self.assertIn('subtitle.setText(breadcrumb())',src)
        self.assertIn('!directory.equals(base)',(JAVA/"FileCatalog.java").read_text(encoding="utf-8"))

    def test_send_stop_buttons_are_exclusive_and_accented(self):
        main=(JAVA/"MainActivity.java").read_text(encoding="utf-8")
        service=(JAVA/"TransferService.java").read_text(encoding="utf-8")
        icon=(JAVA/"UiIcon.java").read_text(encoding="utf-8")
        self.assertIn('button(queue,"file","ВЫБРАТЬ ФАЙЛЫ"',main)
        self.assertIn('button(queue,"close","ОСТАНОВИТЬ ПЕРЕДАЧУ",true',main)
        self.assertIn('startSendButton.setVisibility(sending?View.GONE:View.VISIBLE)',main)
        self.assertIn('stopSendButton.setVisibility(sending?View.VISIBLE:View.GONE)',main)
        self.assertIn('isSending=sending',service)
        self.assertIn('finally{isSending=false;',service)
        self.assertIn('case "close":',icon)

    def test_icon_only_mode_centers_tabs_and_file_icons(self):
        src=(JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
        self.assertIn('horizontal.setFillViewport(true)',src)
        self.assertIn('new LinearLayout.LayoutParams(0,-2,1)',src)
        self.assertIn('FrameLayout.LayoutParams(dp(40),dp(40),Gravity.CENTER)',src)
        self.assertIn('if(style==1){',src)

if __name__=="__main__":unittest.main()
