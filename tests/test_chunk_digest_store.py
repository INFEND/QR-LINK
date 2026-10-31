"""Executable JVM tests for the durable, fixed-width chunk SHA-256 sidecar."""
import subprocess
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/src/main/java/dev/xarkon/link/ChunkDigestStore.java"
HARNESS = r"""
import dev.xarkon.link.ChunkDigestStore;
import java.io.File;
import java.io.RandomAccessFile;
import java.nio.file.Files;
import java.util.Arrays;

public final class ChunkDigestStoreHarness {
    public static void main(String[] args)throws Exception {
        File dir=Files.createTempDirectory("chunk-digest").toFile();
        File file=new File(dir,"received.sha");
        if(ChunkDigestStore.open(file)!=null)throw new AssertionError("missing file trusted");
        byte[] a=new byte[32],b=new byte[32];
        Arrays.fill(a,(byte)0x5a);Arrays.fill(b,(byte)0x3c);
        ChunkDigestStore.put(file,0,a);
        ChunkDigestStore.put(file,5,b);
        try(ChunkDigestStore.Reader reader=ChunkDigestStore.open(file)){
            if(!Arrays.equals(a,reader.read(0)))throw new AssertionError("first digest");
            if(!Arrays.equals(b,reader.read(5)))throw new AssertionError("sparse digest");
            if(reader.read(6)!=null)throw new AssertionError("absent digest accepted");
        }
        try(RandomAccessFile truncated=new RandomAccessFile(file,"rw")){
            truncated.setLength(5L*32+10);
        }
        try(ChunkDigestStore.Reader reader=ChunkDigestStore.open(file)){
            if(reader.read(5)!=null)throw new AssertionError("partial digest accepted");
        }
        try{ChunkDigestStore.put(file,-1,a);throw new AssertionError("negative index");}
        catch(IllegalArgumentException expected){}
        try{ChunkDigestStore.put(file,0,new byte[31]);throw new AssertionError("short hash");}
        catch(IllegalArgumentException expected){}
    }
}
"""
class ChunkDigestStoreTests(unittest.TestCase):
    def test_durable_hash_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness=Path(tmp)/"ChunkDigestStoreHarness.java"
            harness.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,str(SOURCE),str(harness)],check=True)
            subprocess.run(["java","-cp",tmp,"ChunkDigestStoreHarness"],check=True)

if __name__=="__main__":
    unittest.main()
