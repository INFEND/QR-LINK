package dev.xarkon.link;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.Environment;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.net.URLConnection;
import java.util.List;

/** Read-only, URI-grant-protected previews of files within shared internal storage. */
public final class PreviewProvider extends ContentProvider {
    @Override public boolean onCreate(){return true;}
    private File approved(Uri uri)throws FileNotFoundException{
        if(uri==null||!"dev.xarkon.link.preview".equals(uri.getAuthority()))
            throw new FileNotFoundException("Неверная ссылка");
        List<String> parts=uri.getPathSegments();
        if(parts.size()!=2||!"file".equals(parts.get(0)))
            throw new FileNotFoundException("Неверный путь");
        try{
            File root=Environment.getExternalStorageDirectory().getCanonicalFile();
            File target=new File(root,parts.get(1)).getCanonicalFile();
            if(!target.getPath().startsWith(root.getPath()+File.separator)||!target.isFile())
                throw new FileNotFoundException("Файл недоступен");
            return target;
        }catch(IOException ex){throw new FileNotFoundException("Не удалось открыть файл");}
    }
    @Override public ParcelFileDescriptor openFile(Uri uri,String mode)throws FileNotFoundException{
        if(!"r".equals(mode))throw new FileNotFoundException("Только чтение");
        return ParcelFileDescriptor.open(approved(uri),ParcelFileDescriptor.MODE_READ_ONLY);
    }
    @Override public String getType(Uri uri){
        try{
            String type=URLConnection.guessContentTypeFromName(approved(uri).getName());
            return type==null?"application/octet-stream":type;
        }catch(Exception ignored){return "application/octet-stream";}
    }
    @Override public Cursor query(Uri uri,String[] projection,String selection,String[] args,String sortOrder){
        try{
            File file=approved(uri);
            String[] cols=projection==null?new String[]{OpenableColumns.DISPLAY_NAME,OpenableColumns.SIZE}:projection;
            MatrixCursor cursor=new MatrixCursor(cols);Object[] values=new Object[cols.length];
            for(int i=0;i<cols.length;i++){
                if(OpenableColumns.DISPLAY_NAME.equals(cols[i]))values[i]=file.getName();
                else if(OpenableColumns.SIZE.equals(cols[i]))values[i]=file.length();
            }
            cursor.addRow(values);return cursor;
        }catch(Exception ignored){return null;}
    }
    @Override public Uri insert(Uri uri,ContentValues values){throw new UnsupportedOperationException();}
    @Override public int update(Uri uri,ContentValues values,String selection,String[] args){return 0;}
    @Override public int delete(Uri uri,String selection,String[] args){return 0;}
}
