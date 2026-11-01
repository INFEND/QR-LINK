"""Regression guards for the 0.3.81 media, SAF, preview and OTA fixes."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
BROWSER=(JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
UPDATER=(JAVA/"UpdateManager.java").read_text(encoding="utf-8")

class ProductFixes81(unittest.TestCase):
    def test_media_first_folder_is_alphabetically_first(self):
        self.assertLess(BROWSER.index("Collections.sort(grouped.folders"),
                        BROWSER.index("current.addAll(grouped.folders)"))
        self.assertLess(BROWSER.index("current.addAll(grouped.folders)"),
                        BROWSER.index("Entry first=grouped.folders.get(0)"))

    def test_media_scan_ignores_nonmatching_entries(self):
        query=BROWSER.split("private ArrayList<Entry> queryMedia(int cat,String prefix,boolean complete,CancellationSignal cancellation)",1)[1].split("private static final class MediaGrouping",1)[0]
        self.assertLess(query.index("BrowserCategoryFilter.accepts(cat,name,mime)"),
                        query.index("++scanned>MAX_MEDIA_SCAN"))
        self.assertLess(query.index("hiddenPath(path)"),query.index("++scanned>MAX_MEDIA_SCAN"))

    def test_search_finds_files_in_collapsed_media_folders(self):
        self.assertIn("boolean searchClosedMedia=!filter.isEmpty()&&isMedia();",BROWSER)
        self.assertIn("!(searchClosedMedia&&entry.mediaFolder)",BROWSER)
        self.assertIn("BrowserSearchTree.filter(rows,",BROWSER)

    def test_bad_saf_rows_do_not_abort_catalogue(self):
        self.assertIn("documentId==null||documentId.trim().isEmpty()",BROWSER)
        self.assertIn("documentName==null||documentName.trim().isEmpty()",BROWSER)
        self.assertIn("catch(IllegalArgumentException invalidDocument){continue;}",BROWSER)

    def test_duplicate_saf_rows_are_skipped(self):
        self.assertIn("HashSet<String> seenDocumentIds=new HashSet<>();",BROWSER)
        self.assertIn("if(!seenDocumentIds.add(documentId))continue;",BROWSER)
        saf=BROWSER.split("private ArrayList<Entry> queryDocuments(",1)[1]
        self.assertLess(saf.index("if(!seenDocumentIds.add(documentId))continue;"),
                        saf.index("if(++scanned>MAX_SAF_SCAN)"))

    def test_preview_guesses_missing_mime(self):
        self.assertIn("preview.setDataAndType(uri,previewMime(e));",BROWSER)
        self.assertIn("getMimeTypeFromExtension(extension)",BROWSER)

    def test_thumbnail_failures_are_bounded_and_reset_on_permission(self):
        self.assertIn("return size()>512;",BROWSER)
        self.assertIn("if(failedPreviews.containsKey(key))return frame;",BROWSER)
        self.assertIn("else failedPreviews.put(key,Boolean.TRUE);",BROWSER)
        self.assertIn("failedPreviews.clear();load();",BROWSER)

    def test_pinned_apk_fallback_and_version(self):
        self.assertIn("openApk(r.apkUrl,r.versionName)",UPDATER)
        self.assertIn("OtaUrlPolicy.canonicalApkFallback(url,version)",UPDATER)
        harness='''package dev.xarkon.link;
public class OtaFallbackCheck {
 public static void main(String[] args) {
  String old="https://github.com/ANTIFERMENT/QR-LINK/releases/download/v0.3.81/QR-LINK.apk";
  String current="https://github.com/INFEND/QR-LINK/releases/download/v0.3.81/QR-LINK.apk";
  if(!current.equals(OtaUrlPolicy.canonicalApkFallback(old,"0.3.81")))throw new AssertionError();
  if(OtaUrlPolicy.canonicalApkFallback(current,"0.3.81")!=null)throw new AssertionError();
  if(OtaUrlPolicy.canonicalApkFallback(old,"0.3.82")!=null)throw new AssertionError();
  if(OtaUrlPolicy.canonicalApkFallback("https://github.com/evil/QR-LINK/releases/download/v0.3.81/QR-LINK.apk","0.3.81")!=null)throw new AssertionError();
 }
}'''
        with tempfile.TemporaryDirectory() as tmp:
            check=Path(tmp)/"OtaFallbackCheck.java"
            check.write_text(harness,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,
                            str(JAVA/"OtaUrlPolicy.java"),str(check)],check=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.OtaFallbackCheck"],check=True)
