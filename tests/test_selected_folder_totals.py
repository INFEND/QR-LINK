"""JVM regression: selected folder + files must show a real total."""
from pathlib import Path
import subprocess
import tempfile
import unittest

JAVA = Path(__file__).resolve().parents[1] / "app/src/main/java/dev/xarkon/link"
BROWSER = JAVA / "FileBrowserActivity.java"

HARNESS = r'''
package dev.xarkon.link;
import java.util.*;
public final class SelectionTotalsCheck {
    static void yes(boolean b){if(!b)throw new AssertionError("Selection accounting regression");}
    static BrowserSelectionTotals.Selection folder(String k,String uri,String path,long preview){
        return new BrowserSelectionTotals.Selection(k,uri,path,true,-1,preview);
    }
    static BrowserSelectionTotals.Selection file(String k,String uri,String path,long size){
        return new BrowserSelectionTotals.Selection(k,uri,path,false,size,-1);
    }
    static BrowserSelectionTotals.Result sum(
        java.util.Map<String,BrowserSelectionTotals.FolderStats> snapshots,
        BrowserSelectionTotals.Selection... entries){
        return BrowserSelectionTotals.sum(Arrays.asList(entries),snapshots);
    }
    public static void main(String[] args){
        Map<String,BrowserSelectionTotals.FolderStats> cache=new HashMap<>();
        BrowserSelectionTotals.Selection main=folder("f1","content://media/external/images/33","_Archive",22544384L);
        BrowserSelectionTotals.Selection img=file("i1","content://media/external/images/34","_Archive",215756L);
        BrowserSelectionTotals.Selection other=file("i2","content://media/external/images/35","Other",2048L);
        BrowserSelectionTotals.Result r=sum(cache,main);
        yes(r.pending&&r.provisional&&r.bytes==22544384L&&!r.unknown);
        r=sum(cache,main,img);
        yes(r.bytes==22544384L); // Selected media belongs to folder, not counted again.
        r=sum(cache,main,img,other);
        yes(r.bytes==22544384L+2048L); // Outside selected folder counts once.
        Map<String,Long> exact=new LinkedHashMap<>();
        exact.put("file:///storage/emulated/0/_Archive/picture.jpg",215756L);
        exact.put("file:///storage/emulated/0/_Archive/video.mp4",4048L);
        cache.put("f1",new BrowserSelectionTotals.FolderStats(exact,false));
        r=sum(cache,main,img,other);
        yes(!r.pending&&!r.provisional&&!r.unknown&&r.bytes==215756L+4048L+2048L);
        BrowserSelectionTotals.Selection duplicate=folder("f2","file:///storage/emulated/0/_Archive","_Archive",0);
        cache.put("f2",new BrowserSelectionTotals.FolderStats(exact,false));
        r=sum(cache,main,duplicate,img,other);
        yes(r.bytes==215756L+4048L+2048L);
        // Parent + nested child is one folder, even while both sizes are pending.
        BrowserSelectionTotals.Selection nested=folder("nested",
            "file:///storage/emulated/0/_Archive/Sub","_Archive/Sub",4096);
        r=sum(Collections.emptyMap(),main,nested);
        yes(r.pending&&r.provisional&&r.bytes==22544384L+4096L);
        r=sum(cache,main,nested);
        yes(!r.pending&&!r.provisional&&r.bytes==215756L+4048L);
        // Parent media previews contain direct files only. The nested AyyGram
        // folder adds its own 12.1 MB to the existing 14.3 MB until an
        // exact recursive parent snapshot is available.
        BrowserSelectionTotals.Selection pictures=folder("pictures",
            "content://media/external/images/81","Pictures",14300000L);
        BrowserSelectionTotals.Selection ayy=folder("ayy",
            "content://media/external/images/82","Pictures/AyyGram",12100000L);
        r=sum(Collections.emptyMap(),pictures,ayy);
        yes(r.pending&&r.provisional&&r.bytes==26400000L);
        Map<String,Long> recursive=new LinkedHashMap<>();
        recursive.put("file:///storage/emulated/0/Pictures/pic.jpg",14300000L);
        recursive.put("file:///storage/emulated/0/Pictures/AyyGram/pic.jpg",12100000L);
        cache.put("pictures",new BrowserSelectionTotals.FolderStats(recursive,false));
        r=sum(cache,pictures,ayy);
        yes(r.bytes==26400000L&&!r.unknown);
        // A lexical prefix is not ancestry: Pictures/../Other is outside.
        BrowserSelectionTotals.Selection escaped=file("escaped",
            "content://media/external/images/900","Pictures/../Other",700L);
        r=sum(cache,pictures,escaped);
        yes(r.bytes==26400700L&&!r.unknown);
        // Dot segments inside the selected folder must still deduplicate.
        BrowserSelectionTotals.Selection dotted=file("dotted",
            "content://media/external/images/901","Pictures/./AyyGram",700L);
        r=sum(cache,pictures,dotted);
        yes(r.bytes==26400000L);
        // A selected shared-storage root cannot hide an escaped path.
        BrowserSelectionTotals.Selection root=folder("root",
            "file:///storage/emulated/0","",0L);
        Map<String,BrowserSelectionTotals.FolderStats> rootCache=new HashMap<>();
        rootCache.put("root",new BrowserSelectionTotals.FolderStats(
            Collections.emptyMap(),false,1000L));
        BrowserSelectionTotals.Selection escapedRoot=file("escapedRoot",
            "file:///storage/emulated/0/../outside.bin","../outside.bin",700L);
        r=sum(rootCache,root,escapedRoot);
        yes(r.bytes==1700L&&!r.unknown);
        BrowserSelectionTotals.Selection duplicatePending=folder("dp",
            pictures.uri,pictures.path,14300000L);
        r=sum(Collections.emptyMap(),pictures,duplicatePending);
        yes(r.bytes==14300000L);
        // Same selected file URI from two categories must not inflate the total.
        BrowserSelectionTotals.Selection repeated=file("repeated",img.uri,img.path,img.bytes);
        r=sum(Collections.emptyMap(),img,repeated,other);
        yes(r.bytes==215756L+2048L);
        BrowserSelectionTotals.Selection missing=folder("missing","file:///storage/emulated/0/Unknown","Unknown",-1);
        r=sum(cache,missing);
        yes(r.pending&&!r.provisional);
        cache.put("missing",new BrowserSelectionTotals.FolderStats(Collections.emptyMap(),true));
        r=sum(cache,missing);
        yes(!r.pending&&r.unknown);
        // A readable MediaStore estimate survives provider permission failure.
        cache.put("f1",new BrowserSelectionTotals.FolderStats(Collections.emptyMap(),true));
        r=sum(cache,main,img);
        yes(!r.pending&&r.provisional&&!r.unknown&&r.bytes==22544384L);
        // A transfer scan stopped by its queue limit may contain partial files.
        // A verified folder-card total must win over that incomplete snapshot.
        cache.put("f1",new BrowserSelectionTotals.FolderStats(exact,true));
        r=sum(cache,main,img,other);
        yes(r.provisional&&!r.unknown&&r.bytes==22544384L+2048L);
        cache.put("f1",new BrowserSelectionTotals.FolderStats(exact,false));
        BrowserSelectionTotals.Selection saf=folder("saf","content://documents/tree/root","_Archive",6000);
        r=sum(cache,saf,img); // Same path, different provider: must count separate sources.
        yes(r.bytes==6000+215756L);
        // Regression: a queue-limited 30001-file folder is fully counted by
        // the streaming card scan, without materializing its file URI list.
        BrowserSelectionTotals.Selection huge=folder("huge",
            "file:///storage/emulated/0/Download/Large","Download/Large",-1);
        BrowserSelectionTotals.Selection inside=file("inside",
            "file:///storage/emulated/0/Download/Large/one.bin","Download/Large",100);
        BrowserSelectionTotals.Selection outside=file("outside",
            "file:///storage/emulated/0/Download/Other.bin","Download",700);
        cache.put("huge",new BrowserSelectionTotals.FolderStats(
            Collections.emptyMap(),false,30005000L));
        r=sum(cache,huge,inside,outside);
        yes(!r.pending&&!r.unknown&&!r.provisional&&r.bytes==30005700L);
        BrowserSelectionTotals.Selection hugeChild=folder("hugeChild",
            "file:///storage/emulated/0/Download/Large/Sub","Download/Large/Sub",500);
        cache.put("hugeChild",new BrowserSelectionTotals.FolderStats(
            Collections.emptyMap(),false,500L));
        r=sum(cache,huge,hugeChild,inside,outside);
        yes(r.bytes==30005700L); // Nested selection must not inflate the exact total.
        // A previously completed local folder-card scan is an exact recursive
        // aggregate even while a separate selected-folder URI scan is pending.
        Map<String,BrowserSelectionTotals.FolderStats> cardCache=new HashMap<>();
        cardCache.put("huge",new BrowserSelectionTotals.FolderStats(
            Collections.emptyMap(),false,30005000L));
        r=sum(cardCache,huge,hugeChild,inside,outside);
        yes(r.bytes==30005700L&&!r.unknown&&!r.provisional&&!r.pending);
        cache.put("huge",new BrowserSelectionTotals.FolderStats(
            Collections.emptyMap(),true,30005000L));
        r=sum(cache,huge);
        yes(r.unknown&&!r.provisional); // Incomplete scans cannot claim exact size.
        r=sum(cache,file("verybig","file:///big","",Long.MAX_VALUE-1),
                    file("small","file:///small","",100));
        yes(r.bytes==Long.MAX_VALUE);
    }
}
'''


class SelectionTotalsTests(unittest.TestCase):
    def test_pure_java_size_calculation(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness=Path(tmp)/"SelectionTotalsCheck.java"
            harness.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,
                           str(JAVA/"BrowserSelectionTotals.java"),str(harness)],
                           check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.SelectionTotalsCheck"],
                           check=True,capture_output=True,text=True)

    def test_ui_queues_folder_scan_and_never_forces_unknown_size(self):
        source=BROWSER.read_text(encoding="utf-8")
        self.assertIn("if(e.folder&&selected.containsKey(key))requestFolderSize(e)",source)
        self.assertIn("BrowserSelectionTotals.sum(entries,effectiveSnapshots)",source)
        self.assertIn("effectiveSnapshots.put(folder.key(),new BrowserSelectionTotals.FolderStats(",source)
        self.assertIn("!folder.folder||folder.mediaFolder||folder.localFile==null",source)
        self.assertIn("FileCatalog.fromLocalFolder(this,new File(root,folder.path),folder.path)",source)
        self.assertIn("FileCatalog.fromDocumentFolder(this,folder.tree,folder.docId,folder.name)",source)
        self.assertNotIn('folders>0||unknown>0?"неизвестен"',source)
        totals=(JAVA/"BrowserSelectionTotals.java").read_text(encoding="utf-8")
        self.assertIn("coveredByAnotherFolder(entry,all,i,snapshots)",totals)
        self.assertIn("!countedFiles.add(entry.uri)",totals)
        self.assertIn("if(stats.exactBytes>=0)",totals)


if __name__=="__main__":
    unittest.main()
