"""Executable tests for filtered, expanded media groups and application-only results."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
BROWSER=JAVA/"FileBrowserActivity.java"

HARNESS=r'''package dev.xarkon.link;
import java.util.*;
public final class BrowserMediaFoldersCheck {
    private static void check(boolean result) {
        if(!result)throw new AssertionError("Media tab grouping failed");
    }
    public static void main(String[] args) {
        check(BrowserMediaFolders.normalize("DCIM\\\\Camera//").equals("DCIM/Camera/"));
        check(BrowserMediaFolders.label("DCIM/Camera/").equals("Camera"));
        check(BrowserMediaFolders.label("").equals("Устройство"));
        List<String> locations=List.of("DCIM/Camera/","Movies/","DCIM/Camera/","Music/");
        var grouped=BrowserMediaFolders.group(locations,s->s);
        check(grouped.size()==3);
        check(grouped.get("DCIM/Camera/").size()==2);
        check(grouped.get("Movies/").size()==1);
        check(!grouped.containsKey("._$Trash$/"));
        check(BrowserCategoryFilter.accepts(0,"cover.heic","image/heic"));
        check(!BrowserCategoryFilter.accepts(0,"clip.mp4","video/mp4"));
        check(BrowserCategoryFilter.accepts(1,"clip.mp4","video/mp4"));
        check(!BrowserCategoryFilter.accepts(1,"track.mp3","audio/mpeg"));
        check(BrowserCategoryFilter.accepts(2,"track.flac","audio/flac"));
        check(!BrowserCategoryFilter.accepts(2,"cover.jpg","image/jpeg"));
    }
}
'''

class MediaTabsTests(unittest.TestCase):
    def test_media_groups_and_extension_filter(self):
        with tempfile.TemporaryDirectory() as work:
            test=Path(work)/"BrowserMediaFoldersCheck.java"
            test.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",work,
                str(JAVA/"BrowserMediaFolders.java"),
                str(JAVA/"BrowserCategoryFilter.java"),str(test)],
                check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",work,"dev.xarkon.link.BrowserMediaFoldersCheck"],
                check=True,capture_output=True,text=True)

    def test_media_root_is_preexpanded_with_only_matching_content(self):
        src=BROWSER.read_text(encoding="utf-8")
        self.assertIn("BrowserMediaFolders.group(media,entry->entry.path)",src)
        self.assertIn("expandedFolders.add(first.key())",src)
        self.assertIn("expandedChildren.put(key,grouped.children.get(key))",src)
        self.assertIn("folder.uri=item.getValue().get(0).uri",src)
        self.assertIn("if(!e.folder&&(tab==0||tab==1||tab==2||tab==3))addPreview(row,e,icon,tab)",src)
        self.assertIn("BrowserCategoryFilter.accepts(cat,name,mime)",src)
        self.assertIn('"Файлов: "+(e.mediaFolder&&!mediaTruncated?',src)
        self.assertIn('folder.mediaBytes=unknown?-1:bytes',src)
        self.assertIn("row.setContentDescription(e.folder?",src)
        self.assertIn("previewFrame(e,centered,tab)",src)
        self.assertIn("return frame;",src)
        helper=(JAVA/"BrowserMediaFolders.java").read_text(encoding="utf-8")
        self.assertNotIn("isBlank()",helper)
        self.assertIn("path.trim().isEmpty()",helper)

    def test_apps_only_installed_packages_and_files_unmodified(self):
        src=BROWSER.read_text(encoding="utf-8")
        apps=src.split("private ArrayList<Entry> queryApps(",1)[1].split(
            "private ArrayList<Entry> queryLocal(",1)[0]
        self.assertIn("queryIntentActivities(launch,0)",apps)
        self.assertNotIn("queryLocal(",apps)
        self.assertIn("queryDocuments(rootTree,doc,displayPath,signal)",src)
        self.assertIn("result.addAll(directories);result.addAll(files);",src)

if __name__=="__main__":
    unittest.main()
