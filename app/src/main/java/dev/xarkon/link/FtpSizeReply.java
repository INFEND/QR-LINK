package dev.xarkon.link;

import java.io.IOException;

/** Optional FTP SIZE parsing; malformed advertised sizes must never be trusted. */
final class FtpSizeReply {
    private FtpSizeReply(){}

    static long expectedBytes(int code,String line)throws IOException{
        if(code!=213)return -1L;
        if(line==null||!line.matches("213[ \\t]+[0-9]{1,19}[ \\t]*"))
            throw new IOException("FTP-сервер сообщил неверный размер файла");
        try{return Long.parseLong(line.substring(3).trim());}
        catch(NumberFormatException invalid){
            throw new IOException("FTP-сервер сообщил слишком большой размер файла",invalid);
        }
    }
}
