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
            subprocess.run(["javac", "-d", tmp, str(JAVA/"BrowserFolderCardStats.java"),str(JAVA/"BrowserFolderAccess.java"),
                            str(source)], check=True, capture_output=True)
            subprocess.run(["java", "-cp", tmp, "dev.xarkon.link.FolderCardStatsCheck"],
                           check=True, capture_output=True)


    def test_streaming_local_folder_over_30000_files(self):
        harness = r"""package dev.xarkon.link;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;
public final class FolderCardLargeCheck {
    public static void main(String[] args) throws Exception {
        Path root=Files.createTempDirectory("qr-link-card-");
        try {
            Path child=Files.createDirectories(root.resolve("nested"));
            Files.write(child.resolve("one.bin"),new byte[]{1,2,3});
            for(int i=0;i<30001;i++)Files.createFile(root.resolve("f"+i));
            BrowserFolderCardStats stats=BrowserFolderCardStats.scanLocal(root,root);
            if(!stats.complete||!stats.bytesKnown||stats.fileCount!=30002||stats.bytes!=3)
                throw new AssertionError("Large local folder must be exact");
            boolean denied=false;
            try{BrowserFolderCardStats.scanLocal(root,child);}catch(java.io.IOException expected){denied=true;}
            if(!denied)throw new AssertionError("Shared-storage boundary");
            Path link=root.resolve("outside-link");
            try{
                Files.createSymbolicLink(link,child);
                denied=false;
                try{BrowserFolderCardStats.scanLocal(root,root);}
                catch(java.io.IOException expected){denied=true;}
                if(!denied)throw new AssertionError("Symbolic link must fail closed");
            }catch(UnsupportedOperationException|SecurityException ignored){}
        } finally {
            try(Stream<Path> paths=Files.walk(root)){
                paths.sorted(Comparator.reverseOrder()).forEach(p->{
                    try{Files.deleteIfExists(p);}catch(java.io.IOException e){
                        throw new RuntimeException(e);
                    }
                });
            }
        }
    }
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"FolderCardLargeCheck.java"
            source.write_text(harness,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,
                            str(JAVA/"BrowserFolderCardStats.java"),str(JAVA/"BrowserFolderAccess.java"),str(source)],
                           check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.FolderCardLargeCheck"],
                           check=True,capture_output=True,text=True)

    def test_protected_nested_directories_do_not_report_false_zero(self):
        harness = r"""package dev.xarkon.link;
import java.nio.file.*;
import java.nio.file.AccessDeniedException;
import java.util.Comparator;
import java.util.stream.Stream;
public final class NestedProtectedCardCheck {
    public static void main(String[] args) throws Exception {
        Path root=Files.createTempDirectory("qr-link-nested-card-");
        try {
            Path ordinary=Files.createDirectories(root.resolve("Download/data"));
            Files.write(ordinary.resolve("clip.mp4"),new byte[]{1,2,3});
            Path protectedData=Files.createDirectories(root.resolve("Android/data"));
            boolean denied=false;
            try{BrowserFolderCardStats.scanLocal(root,root,null,35);}
            catch(AccessDeniedException e){
                denied=true;
                if(!BrowserFolderAccess.message("Android",e).startsWith(
                    "Нет доступа к системной папке Android"))
                    throw new AssertionError("Nested denial must have Android explanation");
            }
            if(!denied)throw new AssertionError("Filtered nested Android/data reported as empty");
            Files.write(protectedData.resolve("visible.bin"),new byte[]{1});
            BrowserFolderCardStats visible=BrowserFolderCardStats.scanLocal(root,root,null,35);
            if(!visible.complete||!visible.bytesKnown||visible.fileCount!=2||visible.bytes!=4)
                throw new AssertionError("Visible protected data and ordinary data must count");
            Files.createDirectories(root.resolve("Android/obb"));
            denied=false;
            try{BrowserFolderCardStats.scanLocal(root,root,null,35);}
            catch(AccessDeniedException expected){denied=true;}
            if(!denied)throw new AssertionError("Filtered nested Android/obb reported as empty");
            BrowserFolderCardStats legacy=BrowserFolderCardStats.scanLocal(root,root,null,29);
            if(!legacy.complete||legacy.fileCount!=2)
                throw new AssertionError("Android 10 should not receive Android 11 restrictions");
            BrowserFolderCardStats ordinaryOnly=BrowserFolderCardStats.scanLocal(
                ordinary,root,null,35);
            if(!ordinaryOnly.complete||ordinaryOnly.fileCount!=1||ordinaryOnly.bytes!=3)
                throw new AssertionError("Ordinary data folder incorrectly blocked");
        } finally {
            try(Stream<Path> paths=Files.walk(root)){
                paths.sorted(Comparator.reverseOrder()).forEach(p->{
                    try{Files.deleteIfExists(p);}catch(Exception e){throw new RuntimeException(e);}
                });
            }
        }
    }
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"NestedProtectedCardCheck.java"
            source.write_text(harness,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,
                str(JAVA/"BrowserFolderCardStats.java"),
                str(JAVA/"BrowserFolderAccess.java"),str(source)],
                check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.NestedProtectedCardCheck"],
                check=True,capture_output=True,text=True)

    def test_browser_uses_nonblocking_cached_metadata(self):
        source = (JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
        self.assertIn("folderStatsIo=Executors.newFixedThreadPool(2)", source)
        self.assertIn("folderMetaViews.put(e.key(),meta);", source)
        self.assertIn("requestFolderSize(e);", source)
        self.assertIn("BrowserFolderCardStats.scanLocal(", source)
        self.assertIn("BrowserFolderCardStats.scanDocuments(", source)
        self.assertIn("direct=scanSafFolder(folder);", source)
        self.assertIn("getContentResolver().openFileDescriptor(document,\"r\")", source)
        self.assertIn("descriptor.getStatSize()", source)
        self.assertIn("folderPreviewBytes(e)", source)
        self.assertIn("if(snapshotRequested&&folder.localFile!=null)try{", source)
        self.assertIn("final boolean snapshotUnknown=!stats.bytesKnown;", source)
        self.assertIn("final long snapshotExactBytes=direct!=null&&stats.bytesKnown?stats.bytes:-1;", source)
        self.assertIn("lengths,snapshotUnknown,snapshotExactBytes", source)
        self.assertIn("folderCardStats.put(key,stats);", source)
        self.assertIn("if(selected.containsKey(key))", source)
        self.assertIn("folderStatsIo.shutdownNow()", source)


    def test_streaming_saf_folder_over_queue_limit_and_fail_closed(self):
        harness = r"""package dev.xarkon.link;
import java.io.*;
import java.util.*;
public final class SafFolderCardCheck {
    static final class Node {
        final String id;
        final boolean folder;
        final long size;
        Node(String id,boolean folder,long size){
            this.id=id;this.folder=folder;this.size=size;
        }
    }
    public static void main(String[] args)throws Exception{
        Map<String,List<Node>> tree=new HashMap<>();
        List<Node> many=new ArrayList<>();
        for(int i=0;i<30001;i++)many.add(new Node("f"+i,false,1));
        many.add(new Node("f0",false,1)); // repeated provider row
        many.add(new Node("child",true,0));
        tree.put("root",many);
        tree.put("child",Arrays.asList(new Node("last",false,4)));
        BrowserFolderCardStats.DocumentChildReader reader=(parent,visit)->{
            for(Node n:tree.getOrDefault(parent,Collections.emptyList()))
                visit.accept(n.id,n.folder,n.size);
        };
        BrowserFolderCardStats result=BrowserFolderCardStats.scanDocuments("root",reader);
        if(!result.complete||!result.bytesKnown||result.fileCount!=30002||result.bytes!=30005)
            throw new AssertionError("SAF folder totals over queue limit");
        tree.put("root",Arrays.asList(new Node("unknown",false,-1)));
        result=BrowserFolderCardStats.scanDocuments("root",reader);
        if(!result.complete||result.bytesKnown||result.fileCount!=1)
            throw new AssertionError("Unknown provider size must not become exact");
        // A SAF provider may omit COLUMN_SIZE while its descriptor exposes
        // a known length. Resolve after enumeration and only once per file ID.
        tree.put("root",Arrays.asList(new Node("unknown",false,-1),
            new Node("unknown",false,-1)));
        final int[] descriptorReads={0};
        result=BrowserFolderCardStats.scanDocuments("root",reader,id->{
            descriptorReads[0]++;
            return id.equals("unknown")?8192L:-1L;
        },null);
        if(!result.complete||!result.bytesKnown||result.fileCount!=1||
            result.bytes!=8192L||descriptorReads[0]!=1)
            throw new AssertionError("Descriptor fallback must recover exact SAF size");
        result=BrowserFolderCardStats.scanDocuments("root",reader,id->-1L,null);
        if(result.bytesKnown)throw new AssertionError("Unknown descriptor must remain unknown");
        boolean resolverDenied=false;
        try{BrowserFolderCardStats.scanDocuments("root",reader,id->{
            throw new IOException("Нет доступа");
        },null);}catch(IOException expected){resolverDenied=true;}
        if(!resolverDenied)throw new AssertionError("Permission failure must not be hidden");
        tree.put("root",Arrays.asList(new Node("root",true,0)));
        boolean failed=false;
        try{BrowserFolderCardStats.scanDocuments("root",reader);}
        catch(IOException expected){failed=true;}
        if(!failed)throw new AssertionError("Cyclic directory accepted");
        tree.put("root",Arrays.asList(new Node("same",false,1),new Node("same",false,2)));
        failed=false;
        try{BrowserFolderCardStats.scanDocuments("root",reader);}
        catch(IOException expected){failed=true;}
        if(!failed)throw new AssertionError("Inconsistent duplicate accepted");
        tree.put("root",Arrays.asList(new Node("a",false,Long.MAX_VALUE),
            new Node("b",false,1)));
        result=BrowserFolderCardStats.scanDocuments("root",reader);
        if(result.bytesKnown)throw new AssertionError("Overflow accepted");
        Thread.currentThread().interrupt();
        failed=false;
        try{BrowserFolderCardStats.scanDocuments("root",reader);}
        catch(IOException expected){failed=true;}
        Thread.interrupted();
        if(!failed)throw new AssertionError("Cancellation ignored");
    }
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"SafFolderCardCheck.java"
            source.write_text(harness,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,
                            str(JAVA/"BrowserFolderCardStats.java"),str(JAVA/"BrowserFolderAccess.java"),str(source)],
                           check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.SafFolderCardCheck"],
                           check=True,capture_output=True,text=True)


if __name__ == "__main__":
    unittest.main()
