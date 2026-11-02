package dev.xarkon.link;

import android.content.*;
import android.net.Uri;
import android.os.Environment;
import android.provider.MediaStore;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** ShareMe's documented 'Connect to computer' FTP mode: download-only bridge. */
public final class FtpBridge implements AutoCloseable {
    public static final class Entry {
        public final String name; public final boolean directory;public final long size;
        Entry(String n,boolean d,long s){name=n;directory=d;size=s;}
        public String toString(){return (directory?"[ПАПКА] ":"[ФАЙЛ] ")+name+(size>=0?" · "+Util.readable(size):"");}
    }
    private final Socket control;
    private final BufferedReader reader;
    private final BufferedWriter writer;
    private final Context context;
    private final String host;
    private int port;
    public FtpBridge(Context ctx,String ftp)throws Exception{
        this.context=ctx.getApplicationContext();
        URI uri=new URI(ftp.trim());if(!"ftp".equalsIgnoreCase(uri.getScheme()))throw new IOException("Введите ftp://IP:порт/");
        host=uri.getHost();if(host==null)throw new IOException("Нет FTP-адреса");
        port=uri.getPort()>0?uri.getPort():21;
        control=new Socket();
        try{
            control.connect(new InetSocketAddress(host,port),5000);control.setSoTimeout(20000);
        reader=new BufferedReader(new InputStreamReader(control.getInputStream(),StandardCharsets.UTF_8));
        writer=new BufferedWriter(new OutputStreamWriter(control.getOutputStream(),StandardCharsets.UTF_8));
        expect(220);
        String user="anonymous",pass="anonymous@";
        if(uri.getUserInfo()!=null){String[]parts=uri.getUserInfo().split(":",2);user=parts[0];if(parts.length>1)pass=parts[1];}
        int code=send("USER "+user);
        if(code==331){code=send("PASS "+pass);}
        if(code!=230&&code!=202)throw serverFailure(code);
        expectResult(send("TYPE I"));
        }catch(Exception failure){
            try{control.close();}catch(IOException ignored){}
            throw failure;
        }
    }
    private String last;
    private int response()throws IOException{
        FtpReplyReader.Reply reply=FtpReplyReader.read(reader);
        last=reply.lastLine;return reply.code;
    }
    private static IOException serverFailure(int code){
        return new IOException("FTP-сервер отклонил запрос (код "+code+"). Проверьте доступ и повторите попытку.");
    }
    private int send(String cmd)throws IOException{if(cmd.contains("\n")||cmd.contains("\r"))throw new IOException("Неверный FTP-путь");writer.write(cmd+"\r\n");writer.flush();return response();}
    private void expect(int expect)throws IOException{int n=response();if(n!=expect)throw serverFailure(n);}
    private void expectResult(int code)throws IOException{if(code<200||code>=300)throw serverFailure(code);}
    private Socket passive()throws IOException{
        int code=send("EPSV");int dataport;
        if(code==229){
            dataport=FtpPassiveReply.epsvPort(last);
        }else{
            code=send("PASV");
            if(code!=227)throw new IOException("FTP не поддерживает пассивный режим");
            dataport=FtpPassiveReply.pasvPort(last);
        }
        // Always connect to the authenticated control-connection host,
        // never to the IP advertised by an untrusted FTP server.
        return FtpDataSocket.connect(host,dataport);
    }
    private void navigate(String path)throws IOException{
        int res=send("CWD /");expectResult(res);
        if(path==null||path.isEmpty()||path.equals("/"))return;
        for(String segment:path.replace('\\','/').split("/")){
            if(segment.isEmpty())continue;
            if(!FtpListingReader.safeName(segment))throw new IOException("Некорректный путь");
            expectResult(send("CWD "+segment));
        }
    }
    public List<Entry> list(String dir)throws Exception{
        navigate(dir);List<Entry> result=new ArrayList<>();
        try(Socket data=passive()){
            int code=send("LIST");if(code!=125&&code!=150)throw serverFailure(code);
            try(BufferedReader r=new BufferedReader(new InputStreamReader(data.getInputStream(),StandardCharsets.UTF_8))){
                String line;
                while((line=FtpListingReader.readLine(r))!=null){
                    if(line.startsWith("total "))continue;
                    FtpListingReader.ListedEntry dos=FtpListingReader.parseDosEntry(line);
                    if(dos!=null){
                        FtpListingReader.requireCapacity(result.size());
                        result.add(new Entry(dos.name,dos.directory,dos.size));
                        continue;
                    }
                    if(FtpListingReader.looksLikeDosLine(line))continue;
                    // Unix LIST: permissions links owner group size month day time name
                    String[]fields=line.trim().split("\\s+",9);
                    if(fields.length>=9){
                        boolean isDir=fields[0].charAt(0)=='d';long size=-1;
                        try{size=Long.parseLong(fields[4]);}catch(Exception ignored){}
                        String name=fields[8];if(!FtpListingReader.safeName(name))continue;
                        FtpListingReader.requireCapacity(result.size());
                        result.add(new Entry(name,isDir,size));
                    }else{
                        // Some ShareMe servers support minimal LIST without Unix attributes.
                        String name=line.trim();
                        if(FtpListingReader.safeName(name)){
                            FtpListingReader.requireCapacity(result.size());
                            result.add(new Entry(name,false,-1));
                        }
                    }
                }
            }
        }
        expectResult(response());
        result.sort((a,b)->a.directory==b.directory?a.name.compareToIgnoreCase(b.name):(a.directory?-1:1));
        return result;
    }
    public Uri download(String dir,String file,TransferEngine.Events events)throws Exception{
        navigate(dir);
        if(!FtpListingReader.safeName(file))throw new IOException("Неверное имя файла FTP");
        int sizeCode=send("SIZE "+file);
        long expectedBytes=FtpSizeReply.expectedBytes(sizeCode,last);
        String name=Util.safeName(file);
        ContentValues cv=new ContentValues();cv.put(MediaStore.Downloads.DISPLAY_NAME,name);
        cv.put(MediaStore.Downloads.MIME_TYPE,"application/octet-stream");
        cv.put(MediaStore.Downloads.RELATIVE_PATH,Environment.DIRECTORY_DOWNLOADS+"/QR LINK/ShareMe/");
        cv.put(MediaStore.Downloads.IS_PENDING,1);
        Uri dst=context.getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI,cv);
        if(dst==null)throw new IOException("Не удалось создать файл");
        boolean success=false;
        long start=Util.now(),total=0;
        try(Socket data=passive()){
            int code=send("RETR "+file);
            if(code!=125&&code!=150)throw serverFailure(code);
            try(InputStream in=data.getInputStream();OutputStream out=context.getContentResolver().openOutputStream(dst,"w")){
                if(out==null)throw new IOException("Нет доступа к загрузкам");
                byte[]b=new byte[256*1024];int n;long lastUpdate=0;
                while((n=in.read(b))!=-1){
                    total=FtpSizeReply.checkedTotal(expectedBytes,total,n);
                    out.write(b,0,n);
                    if(Util.now()-lastUpdate>500){lastUpdate=Util.now();events.progress("ShareMe FTP: "+name,total,expectedBytes,total/Math.max(.001,(Util.now()-start)/1000.0));}
                }
                out.flush();
            }
            expectResult(response());
            if(expectedBytes>=0&&total!=expectedBytes)
                throw new IOException("FTP-файл получен не полностью: размер не совпадает");
            success=true;
        }finally{
            if(success){
                ContentValues publish=new ContentValues();publish.put(MediaStore.Downloads.IS_PENDING,0);
                try{
                    if(context.getContentResolver().update(dst,publish,null,null)!=1)
                        throw new IOException("Android не подтвердил сохранение FTP-файла");
                }catch(Exception failure){
                    try{context.getContentResolver().delete(dst,null,null);}catch(Exception ignored){}
                    throw new IOException("Не удалось опубликовать загруженный FTP-файл",failure);
                }
                events.note("FTP получено: "+name+" ("+Util.readable(total)+")");
            }else{
                try{context.getContentResolver().delete(dst,null,null);}catch(Exception ignored){}
            }
        }
        return dst;
    }
    @Override public void close(){try{send("QUIT");}catch(Exception ignored){}try{control.close();}catch(Exception ignored){}}
}
