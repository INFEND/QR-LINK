package dev.xarkon.link;

import java.io.File;
import java.io.IOException;
import java.util.Locale;

/** Crash-durable sender receipts, never an authority to skip receiver uploads. */
public final class SenderAckStore {
    private final File path;
    public SenderAckStore(File appFiles,String id,String sourceSha256) {
        if(appFiles==null||!TransferFileIdentity.validId(id)||
            !TransferFileIdentity.validSha256(sourceSha256))
            throw new IllegalArgumentException("Неверные параметры журнала отправки");
        path=new File(new File(appFiles,"sender_chunk_sha256"),
            id+"-"+sourceSha256.toLowerCase(Locale.ROOT)+".sha");
    }
    /** Only a receiver SHA-256 checked against the sent bytes may be recorded. */
    public synchronized void acknowledge(int index,String remoteSha256)throws IOException {
        if(index<0||!TransferFileIdentity.validSha256(remoteSha256))
            throw new IllegalArgumentException("Неверное подтверждение блока");
        byte[] digest=new byte[ChunkDigestStore.SHA256_BYTES];
        for(int i=0;i<digest.length;i++)
            digest[i]=(byte)Integer.parseInt(remoteSha256.substring(2*i,2*i+2),16);
        ChunkDigestStore.put(path,index,digest);
    }
    /** Reopenable evidence for recovery diagnostics, not a substitute for /offer. */
    public synchronized boolean hasAcknowledgement(int index,String sha256)throws IOException {
        if(index<0||!TransferFileIdentity.validSha256(sha256))
            throw new IllegalArgumentException("Неверный запрос подтверждения");
        try(ChunkDigestStore.Reader reader=ChunkDigestStore.open(path)){
            if(reader==null)return false;
            byte[] digest=reader.read(index);
            if(digest==null)return false;
            for(int i=0;i<digest.length;i++)
                if((digest[i]&255)!=Integer.parseInt(sha256.substring(2*i,2*i+2),16))return false;
            return true;
        }
    }
}
