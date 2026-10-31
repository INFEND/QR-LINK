"""Category filter executable JVM tests and source-level root/selection guardrails."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "app/src/main/java/dev/xarkon/link"
BROWSER = PACKAGE / "FileBrowserActivity.java"

HARNESS = """package dev.xarkon.link;
public final class BrowserCategoryFilterCheck {
  private static void check(boolean result){if(!result)throw new AssertionError("Category filter regression");}
  public static void main(String[] args){
    check(BrowserCategoryFilter.accepts(0,"IMG.HEIC",null));
    check(BrowserCategoryFilter.accepts(0,"unknown","image/avif"));
    check(!BrowserCategoryFilter.accepts(0,"video.mp4","video/mp4"));
    check(BrowserCategoryFilter.accepts(1,"clip.MKV",null));
    check(!BrowserCategoryFilter.accepts(1,"music.flac","audio/flac"));
    check(BrowserCategoryFilter.accepts(2,"song.OPUS",null));
    check(BrowserCategoryFilter.accepts(3,"App.APK",null));
    check(BrowserCategoryFilter.accepts(3,"App.apks",null));
    check(!BrowserCategoryFilter.accepts(3,"notes.txt",null));
    check(BrowserCategoryFilter.accepts(4,"anything",null));
    check(BrowserCategoryFilter.accepts(-1,"anything",null));
  }
}
"""

class BrowserCategoryRootTests(unittest.TestCase):
    def test_java_filter_behavior(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "BrowserCategoryFilterCheck.java"
            source.write_text(HARNESS, encoding="utf-8")
            subprocess.run(["javac", "-encoding", "UTF-8", "-d", tmp,
                            str(PACKAGE / "BrowserCategoryFilter.java"), str(source)],
                           check=True, capture_output=True, text=True)
            subprocess.run(["java", "-cp", tmp, "dev.xarkon.link.BrowserCategoryFilterCheck"],
                           check=True, capture_output=True, text=True)

    def test_all_categories_have_permission_gated_shared_root(self):
        src = BROWSER.read_text(encoding="utf-8")
        self.assertIn("queryLocal(Environment.getExternalStorageDirectory(),signal,cat)", src)
        self.assertIn("queryLocal(Environment.getExternalStorageDirectory(),cancellation,3)", src)
        self.assertIn("BrowserCategoryFilter.accepts(category,file.getName(),e.mime)", src)
        self.assertIn("queryLocal(e.localFile,signal,category)", src)
        self.assertIn("if(isMedia()&&!hasMediaAccess()&&!hasLocalStorageAccess())", src)

    def test_full_folder_selection_not_silently_reduced_to_media_only(self):
        src = BROWSER.read_text(encoding="utf-8")
        self.assertIn("if(e.mediaFolder)", src)
        self.assertIn("if(!hasLocalStorageAccess())throw new SecurityException(", src)
        self.assertIn("FileCatalog.fromLocalFolder(this,new File(storage,e.path),e.path)", src)
        self.assertNotIn("for(Entry child:media.get(e.key()))", src)

if __name__ == "__main__":
    unittest.main()
