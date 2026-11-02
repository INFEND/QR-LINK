package dev.xarkon.link;

import java.io.Closeable;
import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/** Fixed-width, crash-durable SHA-256 index for received chunks. */
public final class ChunkDigestStore {
    public static final int SHA256_BYTES=32;
    private ChunkDigestStore(){}

    public static void put(File path,int index,byte[] digest)throws IOException{
        if(index<0||digest==null||digest.length!=SHA256_BYTES)
            throw new IllegalArgumentException("Неверный SHA-256 блока");
        File parent=path.getParentFile();
        if(parent!=null&&!parent.isDirectory()&&!parent.mkdirs())
            throw new IOException("Не удалось создать хранилище контрольных сумм");
        try(RandomAccessFile out=new RandomAccessFile(path,"rw")){
            out.seek((long)index*SHA256_BYTES);
            out.write(digest);
            out.getFD().sync();
        }
    }

    /** Verify persisted bytes, not merely a digest copied from the same sidecar. */
    public static boolean matches(FileChannel file,long offset,long length,byte[] expected)throws IOException{
        if(file==null||expected==null||expected.length!=SHA256_BYTES||
            offset<0||length<0||offset>Long.MAX_VALUE-length)return false;
        final MessageDigest digest;
        try{digest=MessageDigest.getInstance("SHA-256");}
        catch(NoSuchAlgorithmException failure){throw new IOException("SHA-256 недоступен",failure);}
        ByteBuffer buffer=ByteBuffer.allocate(256*1024);
        long position=offset,remaining=length;
        while(remaining>0){
            buffer.clear();
            buffer.limit((int)Math.min(buffer.capacity(),remaining));
            int n=file.read(buffer,position);
            if(n<=0)return false;
            digest.update(buffer.array(),0,n);
            position+=n;
            remaining-=n;
        }
        return MessageDigest.isEqual(expected,digest.digest());
    }

    public static Reader open(File path)throws IOException{
        return path.isFile()?new Reader(path):null;
    }

    public static final class Reader implements Closeable {
        private final RandomAccessFile in;
        private Reader(File path)throws IOException{in=new RandomAccessFile(path,"r");}
        /** Null means absent or incomplete digest; never treat it as verified. */
        public byte[] read(int index)throws IOException{
            if(index<0)throw new IllegalArgumentException("Неверный индекс блока");
            long offset=(long)index*SHA256_BYTES;
            if(offset>in.length()-SHA256_BYTES)return null;
            byte[] digest=new byte[SHA256_BYTES];
            in.seek(offset);
            in.readFully(digest);
            return digest;
        }
        @Override public void close()throws IOException{in.close();}
    }
}
