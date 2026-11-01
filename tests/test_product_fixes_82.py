"""Regression guards for browser hardening in QR LINK 0.3.82."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
BROWSER=(ROOT/"app/src/main/java/dev/xarkon/link/FileBrowserActivity.java").read_text(encoding="utf-8")
class Browser82(unittest.TestCase):
 def test_nameless_media_not_deduplicated(self):
  code=BROWSER.split("private ArrayList<Entry> queryMedia(int cat,String prefix,boolean complete,CancellationSignal cancellation)",1)[1].split("private static final class MediaGrouping",1)[0]
  self.assertIn("if(rawMediaName==null||rawMediaName.trim().isEmpty())continue;",code)
  self.assertLess(code.index("rawMediaName.trim().isEmpty()"),code.index("seenMediaIds.add(mediaId)"))
 def test_invalid_media_size_does_not_hide_valid_id(self):
  code=BROWSER.split("private ArrayList<Entry> queryMedia(int cat,String prefix,boolean complete,CancellationSignal cancellation)",1)[1].split("private static final class MediaGrouping",1)[0]
  self.assertIn("catch(RuntimeException invalidMediaMetadata)",code)
  self.assertLess(code.index("invalidMediaMetadata"),code.index("seenMediaIds.add(mediaId)"))
 def test_corrupt_saf_row_does_not_hide_other_files(self):
  code=BROWSER.split("private ArrayList<Entry> queryDocuments(",1)[1].split("private Entry focusedFolder()",1)[0]
  self.assertIn("catch(RuntimeException invalidRow)",code)
  self.assertIn("if(!seenDocumentIds.add(documentId))continue;",code)
 def test_search_coalesced_with_transition(self):
  self.assertIn("list.postOnAnimation(searchRefresh);",BROWSER)
  self.assertIn("list.setAlpha(0.88f);",BROWSER)
  self.assertIn("list.animate().alpha(1f).setDuration(140).start();",BROWSER)
 def test_browser_notices_have_theme_and_lifecycle(self):
  self.assertIn("private void showBanner(String message,boolean failure)",BROWSER)
  self.assertIn("new PopupWindow(panel",BROWSER)
  self.assertIn("if(activeBanner!=null){activeBanner.dismiss();activeBanner=null;}",BROWSER)
  self.assertNotIn("Toast.makeText(",BROWSER)
if __name__=="__main__":unittest.main()
