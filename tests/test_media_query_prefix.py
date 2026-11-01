"""MediaStore folder names with SQL wildcards and similarly named directories."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
BROWSER=(JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
HARNESS=r'''package dev.xarkon.link;
public class MediaQueryCheck {
  static void check(boolean value){if(!value)throw new AssertionError("Media prefix error");}
  public static void main(String[] args){
    check(BrowserMediaQuery.likeArgument("DCIM/Camera").equals("DCIM/Camera/%"));
    check(BrowserMediaQuery.likeArgument("DCIM/a_b%").equals("DCIM/a\\_b\\%/%"));
    check(BrowserMediaQuery.likeArgument("A\\B").equals("A/B/%"));
    check(BrowserMediaQuery.likeSelection("relative_path").equals("relative_path LIKE ? ESCAPE '\\'"));
    check(BrowserMediaQuery.matches("DCIM/Camera/sub/","DCIM/Camera"));
    check(!BrowserMediaQuery.matches("DCIM/CameraExtra/","DCIM/Camera"));
    check(!BrowserMediaQuery.matches("DCIM/aXb/","DCIM/a_b"));
    check(BrowserMediaQuery.matches("DCIM/a_b/","DCIM/a_b"));
    check(BrowserMediaQuery.matches("Music/",""));
    check(!BrowserMediaQuery.matches("../DCIM/Camera/","DCIM"));
    check(!BrowserMediaQuery.matches("DCIM/../Camera/","DCIM"));
    check(!BrowserMediaQuery.matches("DCIM/./Camera/","DCIM"));
    check(!BrowserMediaQuery.matches("/DCIM/Camera/","DCIM"));
    check(!BrowserMediaQuery.matches("DCIM/Camera/","../DCIM"));
    check(!BrowserMediaFolders.validRelativePath("C:/DCIM/Camera/"));
    check(BrowserMediaFolders.validRelativePath("DCIM/Camera/"));
    try{BrowserMediaQuery.likeArgument("../DCIM");throw new AssertionError("Unsafe path accepted");}
    catch(IllegalArgumentException expected){};
  }
}
'''
class MediaPrefixTests(unittest.TestCase):
    def test_escaped_like_and_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            harness=Path(temp)/"MediaQueryCheck.java"
            harness.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",temp,
                str(JAVA/"BrowserMediaFolders.java"),str(JAVA/"BrowserMediaQuery.java"),
                str(harness)],check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",temp,"dev.xarkon.link.MediaQueryCheck"],
                check=True,capture_output=True,text=True)
    def test_provider_results_filtered_before_scan_budget(self):
        self.assertIn("BrowserMediaQuery.likeSelection(MediaStore.MediaColumns.RELATIVE_PATH)",BROWSER)
        self.assertIn("BrowserMediaQuery.likeArgument(normalizedPrefix)",BROWSER)
        self.assertLess(BROWSER.index("if(!BrowserMediaQuery.matches(path,normalizedPrefix))continue;"),
            BROWSER.index("if(!complete&&++scanned>MAX_MEDIA_SCAN)"))
    def test_corrupt_provider_rows_do_not_hide_valid_media(self):
        media=BROWSER.split("private ArrayList<Entry> queryMedia(",1)[1].split(
            "private static final class MediaGrouping",1)[0]
        self.assertIn("catch(RuntimeException malformedId){continue;}",media)
        self.assertLess(media.index("BrowserCategoryFilter.accepts(cat,name,mime)"),
            media.index("if(!seenMediaIds.add(mediaId))continue;"))
        self.assertLess(media.index("hiddenPath(path)"),
            media.index("if(!seenMediaIds.add(mediaId))continue;"))

    def test_invalid_saf_documents_do_not_consume_listing_budget(self):
        saf=BROWSER.split("private ArrayList<Entry> queryDocuments(",1)[1].split(
            "private Entry focusedFolder()",1)[0]
        self.assertLess(saf.index("DocumentsContract.buildDocumentUriUsingTree(rootTree,e.docId)"),
            saf.index("if(!seenDocumentIds.add(documentId))continue;"))
        self.assertLess(saf.index("if(!seenDocumentIds.add(documentId))continue;"),
            saf.index("if(++scanned>MAX_SAF_SCAN)"))

if __name__=="__main__":unittest.main()
