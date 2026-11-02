"""Regression: folder cards stream intermediate counts without claiming final sizes."""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"

class FolderProgressTests(unittest.TestCase):
    def test_streaming_local_and_saf_progress(self):
        harness=r"""package dev.xarkon.link;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;
public final class FolderProgressCheck {
    static void yes(boolean x){if(!x)throw new AssertionError("Folder progress");}
    public static void main(String[] args)throws Exception{
        Path root=Files.createTempDirectory("qr-progress-");
        try{
            Path nested=Files.createDirectory(root.resolve("nested"));
            for(int i=0;i<1025;i++)
                Files.write(nested.resolve("f"+i),new byte[]{1,2});
            List<Integer> counts=new ArrayList<>();
            BrowserFolderCardStats stats=BrowserFolderCardStats.scanLocal(root,root,
                (count,bytes)->{
                    counts.add(count);
                    yes(bytes==count*2L);
                });
            yes(stats.complete&&stats.bytesKnown&&stats.fileCount==1025&&stats.bytes==2050);
            yes(counts.equals(Arrays.asList(512,1024)));
            List<Integer> safCounts=new ArrayList<>();
            BrowserFolderCardStats.DocumentChildReader reader=(parent,visitor)->{
                if(parent.equals("root"))visitor.accept("nested",true,0);
                else for(int i=0;i<1025;i++)visitor.accept("id"+i,false,2);
            };
            BrowserFolderCardStats saf=BrowserFolderCardStats.scanDocuments("root",reader,
                (count,bytes)->{
                    safCounts.add(count);
                    yes(bytes==count*2L);
                });
            yes(saf.fileCount==1025&&saf.bytes==2050&&saf.complete);
            yes(safCounts.equals(Arrays.asList(512,1024)));
        }finally{
            try(Stream<Path> walk=Files.walk(root)){
                walk.sorted(Comparator.reverseOrder()).forEach(p->{
                    try{Files.deleteIfExists(p);}catch(Exception ex){throw new RuntimeException(ex);}
                });
            }
        }
    }
}
"""
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"FolderProgressCheck.java"
            source.write_text(harness,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",temp,
                str(JAVA/"BrowserFolderCardStats.java"),
                str(JAVA/"BrowserFolderAccess.java"),str(source)],
                check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",temp,"dev.xarkon.link.FolderProgressCheck"],
                check=True,capture_output=True,text=True)

    def test_ui_progress_is_async_and_cleared(self):
        source=(JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
        self.assertIn('return "Файлов: "+scanned+"+ | Размер: подсчёт…";',source)
        self.assertIn("folderProgressCounts.put(key,files);",source)
        self.assertIn("folderProgressCounts.remove(key);",source)
        self.assertIn("if(epoch!=folderStatsEpoch||!folderSizePending.contains(key)",source)
        self.assertIn("scanSafFolder(folder,progress)",source)
        self.assertIn("getCanonicalFile().toPath(),progress,",source)
        self.assertIn("Build.VERSION.SDK_INT);",source)

if __name__=="__main__":
    unittest.main()
