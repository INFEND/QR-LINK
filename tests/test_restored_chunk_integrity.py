"""A restored receiver must hash saved file bytes, never compare sidecar to itself."""
from pathlib import Path
import subprocess
import tempfile
import unittest

JAVA=Path(__file__).resolve().parents[1]/"app/src/main/java/dev/xarkon/link"
HARNESS=r'''package dev.xarkon.link;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
public final class RestoredChunkCheck {
    static void yes(boolean ok){if(!ok)throw new AssertionError("Untrusted restored block");}
    public static void main(String[] args)throws Exception{
        File f=Files.createTempFile("qr-restored-chunk",".bin").toFile();
        byte[] a="correct-first-chunk".getBytes(StandardCharsets.UTF_8);
        byte[] b="second".getBytes(StandardCharsets.UTF_8);
        try(RandomAccessFile data=new RandomAccessFile(f,"rw")){
            data.write(a);data.write(b);
            byte[] first=MessageDigest.getInstance("SHA-256").digest(a);
            byte[] second=MessageDigest.getInstance("SHA-256").digest(b);
            yes(ChunkDigestStore.matches(data.getChannel(),0,a.length,first));
            yes(ChunkDigestStore.matches(data.getChannel(),a.length,b.length,second));
            yes(!ChunkDigestStore.matches(data.getChannel(),0,a.length,second));
            data.seek(1);data.writeByte('X');
            yes(!ChunkDigestStore.matches(data.getChannel(),0,a.length,first));
            data.setLength(a.length+2);
            yes(!ChunkDigestStore.matches(data.getChannel(),a.length,b.length,second));
            yes(!ChunkDigestStore.matches(data.getChannel(),-1,1,first));
            yes(!ChunkDigestStore.matches(data.getChannel(),Long.MAX_VALUE,2,first));
            yes(!ChunkDigestStore.matches(data.getChannel(),0,1,new byte[31]));
            byte[] empty=MessageDigest.getInstance("SHA-256").digest(new byte[0]);
            yes(ChunkDigestStore.matches(data.getChannel(),0,0,empty));
        }
    }
}
'''

class RestoredChunkTests(unittest.TestCase):
    def test_file_bytes_verified_on_jvm(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness=Path(tmp)/"RestoredChunkCheck.java"
            harness.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,
                str(JAVA/"ChunkDigestStore.java"),str(harness)],
                check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.RestoredChunkCheck"],
                check=True,capture_output=True,text=True)

    def test_receiver_uses_actual_file_bytes_for_resume(self):
        src=(JAVA/"TransferEngine.java").read_text(encoding="utf-8")
        body=src.split("private void verifyRestored(",1)[1].split("private void restore()",1)[0]
        self.assertIn("ChunkDigestStore.matches(channel,offset,length,expected)",body)
        self.assertNotIn("hex(expected).equalsIgnoreCase(storedSha256(",body)
        self.assertIn("if(inc.completed)throw new IOException(",body)
        self.assertLess(body.index("ChunkDigestStore.matches("),body.index("inc.done.clear(index)"))
