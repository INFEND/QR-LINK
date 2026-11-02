package dev.xarkon.link;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.util.Locale;

/** Crash-durable sender receipts, never an authority to skip receiver uploads. */
public final class SenderAckStore {
    private static final int RECORD_BYTES=ChunkDigestStore.SHA256_BYTES+1;
    private static final int PRESENT=0xA5;
    private final File path;
    public SenderAckStore(File appFiles,String id,String sourceSha256) {
        if(appFiles==null||!TransferFileIdentity.validId(id)||
            !TransferFileIdentity.validSha256(sourceSha256))
            throw new IllegalArgumentException("Неверные параметры журнала отправки");
        // Old sparse .sha files have no presence marker and cannot prove a receipt.
        path=new File(new File(appFiles,"sender_chunk_sha256"),
            id+"-"+sourceSha256.toLowerCase(Locale.ROOT)+".ack2");
    }
    /** Only a receiver SHA-256 checked against the sent bytes may be recorded. */
    public synchronized void acknowledge(int index,String remoteSha256)throws IOException {
        if(index<0||!TransferFileIdentity.validSha256(remoteSha256))
            throw new IllegalArgumentException("Неверное подтверждение блока");
        byte[] digest=new byte[ChunkDigestStore.SHA256_BYTES];
        for(int i=0;i<digest.length;i++)
            digest[i]=(byte)Integer.parseInt(remoteSha256.substring(2*i,2*i+2),16);
        File parent=path.getParentFile();
        if(parent!=null&&!parent.isDirectory()&&!parent.mkdirs())
            throw new IOException("Не удалось сохранить журнал подтверждений");
        try(RandomAccessFile out=new RandomAccessFile(path,"rw")){
            long offset=(long)index*RECORD_BYTES;
            // A previous attempt may have left a valid marker at this slot.
            // Revoke it durably before changing the digest: a crash during
            // replacement must never turn torn bytes into a trusted receipt.
            out.seek(offset+ChunkDigestStore.SHA256_BYTES);
            out.write(0);
            out.getFD().sync();
            out.seek(offset);
            out.write(digest);
            out.write(PRESENT);
            out.getFD().sync();
        }
    }
    /** Reopenable evidence for recovery diagnostics, not a substitute for /offer. */
    public synchronized boolean hasAcknowledgement(int index,String sha256)throws IOException {
        if(index<0||!TransferFileIdentity.validSha256(sha256))
            throw new IllegalArgumentException("Неверный запрос подтверждения");
        if(!path.isFile())return false;
        try(RandomAccessFile in=new RandomAccessFile(path,"r")){
            long offset=(long)index*RECORD_BYTES;
            if(offset>in.length()-RECORD_BYTES)return false;
            in.seek(offset);
            byte[] digest=new byte[ChunkDigestStore.SHA256_BYTES];
            in.readFully(digest);
            if(in.read()!=PRESENT)return false;
            for(int i=0;i<digest.length;i++)
                if((digest[i]&255)!=Integer.parseInt(sha256.substring(2*i,2*i+2),16))return false;
            return true;
        }
    }
}
