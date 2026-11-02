"""Real JVM tests for crash-durable sender-side SHA-256 receipts."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
HARNESS=r'''package dev.xarkon.link;
import java.io.*;
import java.nio.file.*;
import java.util.concurrent.*;
public class SenderAckStoreCheck {
    private static void yes(boolean v){if(!v)throw new AssertionError("Sender receipt failed");}
    public static void main(String[] args)throws Exception {
        File root=Files.createTempDirectory("sender-acks").toFile();
        String id="12345678-1234-1234-1234-123456789abc";
        String hash="a".repeat(64),second="b".repeat(64);
        String ack="0123456789abcdef".repeat(4);
        SenderAckStore store=new SenderAckStore(root,id,hash);
        yes(!store.hasAcknowledgement(2,ack));
        store.acknowledge(2,ack);
        String zeroHash="0".repeat(64);
        yes(!store.hasAcknowledgement(1,zeroHash)); // Sparse gap is not a receipt.
        store.acknowledge(1,zeroHash);
        yes(new SenderAckStore(root,id,hash).hasAcknowledgement(1,zeroHash));
        SenderAckStore reopened=new SenderAckStore(root,id,hash);
        yes(reopened.hasAcknowledgement(2,ack));
        yes(!reopened.hasAcknowledgement(2,second));
        yes(!reopened.hasAcknowledgement(1,ack));
        // Replacing an existing receipt must revoke the old digest.
        store.acknowledge(2,second);
        yes(reopened.hasAcknowledgement(2,second));
        yes(!reopened.hasAcknowledgement(2,ack));
        store.acknowledge(2,ack);
        yes(!new SenderAckStore(root,id,second).hasAcknowledgement(2,ack));
        ExecutorService pool=Executors.newFixedThreadPool(4);
        try {
            java.util.List<Future<?>> futures=new java.util.ArrayList<>();
            for(int i=0;i<32;i++){
                final int index=i;
                futures.add(pool.submit(()->{
                    try{store.acknowledge(index,ack);}
                    catch(IOException e){throw new RuntimeException(e);}
                }));
            }
            for(Future<?> f:futures)f.get();
        }finally{pool.shutdownNow();}
        for(int i=0;i<32;i++)yes(reopened.hasAcknowledgement(i,ack));
        File record=new File(new File(root,"sender_chunk_sha256"),id+"-"+hash+".ack2");
        // Simulate a crash after the old marker was revoked but before commit.
        try(RandomAccessFile f=new RandomAccessFile(record,"rw")){
            f.seek(2L*33+32);f.write(0);f.getFD().sync();
            f.seek(2L*33);f.write(new byte[32]);f.getFD().sync();
        }
        yes(!reopened.hasAcknowledgement(2,ack));
        yes(!reopened.hasAcknowledgement(2,zeroHash));
        // A fully persisted replacement digest without a committed marker
        // is still unacknowledged, even when it matches the requested hash.
        try(RandomAccessFile f=new RandomAccessFile(record,"rw")){
            f.seek(2L*33);f.write(new byte[32]);f.getFD().sync();
        }
        yes(!reopened.hasAcknowledgement(2,zeroHash));
        store.acknowledge(2,ack);
        yes(reopened.hasAcknowledgement(2,ack));
        try(RandomAccessFile f=new RandomAccessFile(record,"rw")){
            f.seek(2L*33+32);f.write(0);
        }
        yes(!reopened.hasAcknowledgement(2,ack)); // Missing marker must fail closed.
        File legacy=new File(new File(root,"sender_chunk_sha256"),id+"-"+hash+".sha");
        ChunkDigestStore.put(legacy,2,new byte[32]);
        yes(!reopened.hasAcknowledgement(2,zeroHash)); // Old unmarked files are not trusted.
        try{store.acknowledge(-1,ack);throw new AssertionError();}
        catch(IllegalArgumentException expected){}
        try{store.acknowledge(0,"invalid");throw new AssertionError();}
        catch(IllegalArgumentException expected){}
        try{new SenderAckStore(root,"../escape",hash);throw new AssertionError();}
        catch(IllegalArgumentException expected){}
    }
}
'''

class SenderAckTests(unittest.TestCase):
    def test_durable_sender_receipts(self):
        with tempfile.TemporaryDirectory() as work:
            harness=Path(work)/"SenderAckStoreCheck.java"
            harness.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",work,
                str(JAVA/"TransferFileIdentity.java"),
                str(JAVA/"ChunkDigestStore.java"),
                str(JAVA/"SenderAckStore.java"),str(harness)],
                check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",work,"dev.xarkon.link.SenderAckStoreCheck"],
                check=True,capture_output=True,text=True)

    def test_rewrite_invalidates_old_marker_before_replacing_digest(self):
        source=(JAVA/"SenderAckStore.java").read_text(encoding="utf-8")
        method=source.split("void acknowledge(",1)[1].split("boolean hasAcknowledgement(",1)[0]
        revoked=method.index("out.seek(offset+ChunkDigestStore.SHA256_BYTES);")
        invalidated=method.index("out.write(0);",revoked)
        durable=method.index("out.getFD().sync();",invalidated)
        replaced=method.index("out.write(digest);",durable)
        digest_durable=method.index("out.getFD().sync();",replaced)
        committed=method.index("out.write(PRESENT);",digest_durable)
        marker_durable=method.index("out.getFD().sync();",committed)
        self.assertLess(revoked,invalidated)
        self.assertLess(invalidated,durable)
        self.assertLess(durable,replaced)
        self.assertLess(replaced,digest_durable)
        self.assertLess(digest_durable,committed)
        self.assertLess(committed,marker_durable)
        self.assertEqual(method.count("out.getFD().sync();"),3)

    def test_sender_records_verified_hash_only(self):
        source=(JAVA/"TransferEngine.java").read_text(encoding="utf-8")
        self.assertIn("final SenderAckStore senderAcks=verifyFileSha?",source)
        self.assertIn("if(senderAcks!=null)senderAcks.acknowledge(index,remote);",source)
        self.assertIn("!remote.equalsIgnoreCase(hex(checksum.digest()))",source)
        self.assertIn('BitSet.valueOf(Base64.decode(result.optString("done",""),Base64.DEFAULT))',source)
