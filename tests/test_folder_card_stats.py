import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "app/src/main/java/dev/xarkon/link"


class FolderCardStatsTests(unittest.TestCase):
    def test_folder_card_summaries(self):
        harness = """package dev.xarkon.link;
import java.util.*;
public final class FolderCardStatsCheck {
    public static void main(String[] args) {
        Map<String,Long> files = new LinkedHashMap<>();
        files.put("file:/a", 2048L);
        files.put("file:/b", 1024L);
        BrowserFolderCardStats ok = BrowserFolderCardStats.summarize(files, true);
        if(!ok.complete || !ok.bytesKnown || ok.fileCount!=2 || ok.bytes!=3072L)
            throw new AssertionError("Exact recursive totals");
        files.put("file:/c", -1L);
        BrowserFolderCardStats missing = BrowserFolderCardStats.summarize(files, true);
        if(!missing.complete || missing.bytesKnown || missing.fileCount!=3)
            throw new AssertionError("Unknown file size must not hide exact count");
        BrowserFolderCardStats failed = BrowserFolderCardStats.summarize(files, false);
        if(failed.complete || failed.bytesKnown)
            throw new AssertionError("Incomplete scans cannot claim exact totals");
        files.clear();
        files.put("file:/huge", Long.MAX_VALUE);
        files.put("file:/extra", 1L);
        if(BrowserFolderCardStats.summarize(files,true).bytesKnown)
            throw new AssertionError("Overflow must not wrap to a fake size");
        if(!BrowserFolderCardStats.summarize(Collections.emptyMap(),true).bytesKnown)
            throw new AssertionError("Empty folder is exactly zero bytes");
    }
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "FolderCardStatsCheck.java"
            source.write_text(harness, encoding="utf-8")
            subprocess.run(["javac", "-d", tmp, str(JAVA/"BrowserFolderCardStats.java"),
                            str(source)], check=True, capture_output=True)
            subprocess.run(["java", "-cp", tmp, "dev.xarkon.link.FolderCardStatsCheck"],
                           check=True, capture_output=True)

    def test_browser_uses_nonblocking_cached_metadata(self):
        source = (JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
        self.assertIn("folderStatsIo=Executors.newFixedThreadPool(2)", source)
        self.assertIn("folderMetaViews.put(e.key(),meta);", source)
        self.assertIn("requestFolderSize(e);", source)
        self.assertIn("folderCardStats.put(key,stats);", source)
        self.assertIn("if(selected.containsKey(key))", source)
        self.assertIn("folderStatsIo.shutdownNow()", source)


if __name__ == "__main__":
    unittest.main()
