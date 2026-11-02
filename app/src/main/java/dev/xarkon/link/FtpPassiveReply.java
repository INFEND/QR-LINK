package dev.xarkon.link;

import java.io.IOException;

/** Strict passive-mode FTP port parsing; the advertised server IP is never trusted. */
public final class FtpPassiveReply {
    private FtpPassiveReply(){}

    private static String body(String reply,String mode)throws IOException{
        if(reply==null)throw new IOException("Нет ответа FTP "+mode);
        int begin=reply.indexOf('(');
        int end=reply.indexOf(')',begin+1);
        if(begin<0||end<=begin)throw new IOException("Некорректный ответ FTP "+mode);
        return reply.substring(begin+1,end).trim();
    }
    private static int port(String value,String mode)throws IOException{
        if(!value.matches("[0-9]{1,5}"))
            throw new IOException("Некорректный порт FTP "+mode);
        int port=Integer.parseInt(value);
        if(port<1||port>65535)throw new IOException("Неверный порт данных FTP");
        return port;
    }
    public static int epsvPort(String reply)throws IOException{
        String value=body(reply,"EPSV");
        if(value.length()<5)throw new IOException("Некорректный ответ FTP EPSV");
        char delimiter=value.charAt(0);
        if(value.charAt(1)!=delimiter||value.charAt(2)!=delimiter||
           value.charAt(value.length()-1)!=delimiter)
            throw new IOException("Некорректный ответ FTP EPSV");
        return port(value.substring(3,value.length()-1),"EPSV");
    }
    public static int pasvPort(String reply)throws IOException{
        String[] fields=body(reply,"PASV").split(",",-1);
        if(fields.length!=6)throw new IOException("Некорректный ответ FTP PASV");
        int[] octets=new int[6];
        for(int i=0;i<6;i++){
            String value=fields[i].trim();
            if(!value.matches("[0-9]{1,3}"))
                throw new IOException("Некорректный ответ FTP PASV");
            octets[i]=Integer.parseInt(value);
            if(octets[i]>255)throw new IOException("Некорректный ответ FTP PASV");
        }
        return port(Integer.toString(octets[4]*256+octets[5]),"PASV");
    }
}
