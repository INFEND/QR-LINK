package dev.xarkon.link;

import android.content.*;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.DocumentsContract;
import android.webkit.MimeTypeMap;
import java.io.File;
import java.io.IOException;
import java.util.concurrent.CancellationException;
import java.nio.file.*;
import org.json.*;
import java.util.*;

public final class FileCatalog {
    public static final String PREF="xarkon_queue";
    private static final int MAX_FOLDER_FILES=30000;
    // Bound traversal even when a folder contains only empty directories.
    private static final int MAX_FOLDER_ENTRIES=120000;
    private static final class ScanBudget {
        int entries;
        final HashSet<String> visited=new HashSet<>();
        void step(){
            if(Thread.currentThread().isInterrupted())
                throw new CancellationException("Выбор папки отменён");
            if(++entries>MAX_FOLDER_ENTRIES)
                throw new IllegalStateException("Слишком много элементов в папке (предел 120000)");
        }
    }
    private FileCatalog(){}
    // Queue metadata is a JSON snapshot. Per-file status changes must not
    // deserialize and rewrite thousands of unrelated entries after every file.
    // A small SQLite table keeps each status update durable and O(log n).
    private static StatusStore statusStore;
    // A single-process monotonic invalidation signal for the large queue UI.
    // The durable JSON snapshot and SQLite status journal remain authoritative.
    private static final class StatusStore extends SQLiteOpenHelper {
        StatusStore(Context c){super(c.getApplicationContext(),"qr_link_status.db",null,1);}
        @Override public void onCreate(SQLiteDatabase db){
            db.execSQL("CREATE TABLE item_status (id TEXT PRIMARY KEY NOT NULL, status TEXT NOT NULL)");
        }
        @Override public void onUpgrade(SQLiteDatabase db,int oldVersion,int newVersion){
            db.execSQL("DROP TABLE IF EXISTS item_status");onCreate(db);
        }
    }
    private static SQLiteDatabase statusDb(Context c){
        if(statusStore==null)statusStore=new StatusStore(c);
        return statusStore.getWritableDatabase();
    }
    public static class Item {
        public String id,uri,name,mime,path,status;
        public long size;
        public JSONObject json()throws JSONException{
            JSONObject j=new JSONObject();j.put("id",id).put("uri",uri).put("name",name).put("mime",mime)
               .put("path",path).put("status",status).put("size",size);return j;
        }
        public static Item from(JSONObject j){
            Item x=new Item();x.id=j.optString("id");x.uri=j.optString("uri");
            x.name=j.optString("name");x.mime=j.optString("mime","application/octet-stream");
            x.path=j.optString("path");x.status=j.optString("status","В очереди");x.size=j.optLong("size",-1);return x;
        }
    }
    public static synchronized ArrayList<Item> load(Context c){
        ArrayList<Item> out=new ArrayList<>();
        android.content.SharedPreferences prefs=c.getSharedPreferences(PREF,0);
        String primary=prefs.getString("list","[]");
        try{
            JSONArray j=new JSONArray(primary);
            for(int i=0;i<j.length();i++)out.add(Item.from(j.getJSONObject(i)));
        }catch(Exception damaged){
            // Recover the last successfully committed mirror, never silently clear.
            String mirror=prefs.getString("list_mirror",null);
            if(mirror==null)throw new IllegalStateException("Не удалось прочитать сохранённую очередь",damaged);
            out.clear();
            try{
                JSONArray j=new JSONArray(mirror);
                for(int i=0;i<j.length();i++)out.add(Item.from(j.getJSONObject(i)));
            }catch(Exception lost){
                throw new IllegalStateException("Сохранённая очередь повреждена",lost);
            }
        }
        if(out.isEmpty())return out;
        try{
            HashMap<String,Item> byId=new HashMap<>();
            for(Item item:out)byId.put(item.id,item);
            try(Cursor cursor=statusDb(c).rawQuery("SELECT id,status FROM item_status",null)){
                while(cursor.moveToNext()){
                    Item item=byId.get(cursor.getString(0));
                    if(item!=null)item.status=cursor.getString(1);
                }
            }
        }catch(Exception ignored){
            // Older JSON snapshots remain readable if the status DB is unavailable.
        }
        return out;
    }
    public static synchronized void save(Context c,List<Item> items){
        saveSnapshot(c,items,true);
    }
    private static void saveSnapshot(Context c,List<Item> items,boolean mergePendingStatuses){
        // A caller may hold a stale queue snapshot while the transfer service
        // has written newer statuses to SQLite. Merge them BEFORE deleting the
        // status journal, otherwise a queue edit can revert "Передан" to "В очереди".
        if(mergePendingStatuses&&!items.isEmpty())try{
            HashMap<String,Item> byId=new HashMap<>();
            for(Item item:items)if(item.id!=null)byId.put(item.id,item);
            try(Cursor cursor=statusDb(c).rawQuery("SELECT id,status FROM item_status",null)){
                while(cursor.moveToNext()){
                    Item item=byId.get(cursor.getString(0));
                    if(item!=null)item.status=cursor.getString(1);
                }
            }
        }catch(Exception ignored){
            // Preserve the supplied queue snapshot if the status DB is unavailable.
        }
        JSONArray a=new JSONArray();
        try{for(Item it:items)a.put(it.json());}
        catch(Exception invalid){throw new IllegalStateException("Не удалось сохранить очередь целиком",invalid);}
        // Both copies are committed atomically; an invalid primary can be recovered.
        String snapshot=a.toString();
        boolean saved=c.getSharedPreferences(PREF,0).edit()
            .putString("list",snapshot).putString("list_mirror",snapshot).commit();
        if(!saved)throw new IllegalStateException("Android не сохранил очередь файлов");
        // Never discard the status journal unless the merged snapshot is durable.
        try{statusDb(c).delete("item_status",null,null);}catch(Exception ignored){}
        QueueRevision.changed();
    }
    public static synchronized void append(Context c,List<Item> items){
        ArrayList<Item> all=load(c);
        HashSet<String> seen=new HashSet<>();
        for(Item old:all)if(old.uri!=null&&!old.uri.isEmpty())seen.add(old.uri);
        for(Item item:items){
            if(item==null||item.uri==null||item.uri.isEmpty())
                throw new IllegalArgumentException("Файл без адреса нельзя добавить в очередь");
            if(!seen.add(item.uri))continue;
            if(all.size()>=MAX_FOLDER_FILES)
                throw new IllegalStateException("В очереди может быть не более 30000 файлов");
            all.add(item);
        }
        // Commit only after the entire new selection has passed validation.
        save(c,all);
    }
    public static synchronized void setStatus(Context c,String id,String status){
        if(id==null||id.isEmpty())return;
        try{
            ContentValues values=new ContentValues();
            values.put("id",id);values.put("status",status);
            if(statusDb(c).insertWithOnConflict("item_status",null,values,
                    SQLiteDatabase.CONFLICT_REPLACE)!=-1){QueueRevision.changed();return;}
        }catch(Exception ignored){}
        // Conservative fallback: retain the original JSON status path if
        // SQLite is temporarily unavailable. No transfer result is discarded.
        ArrayList<Item> all=load(c);
        for(Item it:all)if(id.equals(it.id)){it.status=status;break;}
        // The fallback has explicitly updated this status. Do not overlay a
        // stale SQLite row if the database has become read-only.
        saveSnapshot(c,all,false);
    }
    public static Item single(Context c,Uri uri,String path){
        Item it=new Item();it.id=Util.id();it.uri=uri.toString();it.name=Util.name(c,uri);
        it.size=Util.size(c,uri);it.mime=Util.mime(c,uri);it.path=Util.safePath(path);it.status="В очереди";return it;
    }
    /** Collect a user-authorised shared-storage folder without following symlinks. */
    public static ArrayList<Item> fromLocalFolder(Context c,File folder,String relativePath)throws Exception{
        if(Build.VERSION.SDK_INT>=30&&!Environment.isExternalStorageManager())
            throw new SecurityException("Разрешение на внутреннюю память отозвано");
        File base=Environment.getExternalStorageDirectory().getCanonicalFile();
        File directory=folder.getCanonicalFile();
        if(!directory.equals(base)&&!directory.getPath().startsWith(base.getPath()+File.separator))
            throw new SecurityException("Папка находится вне внутренней памяти");
        ArrayList<Item> result=new ArrayList<>();
        collectLocal(directory.toPath(),base.getPath()+File.separator,Util.safePath(relativePath),result,0,new ScanBudget());
        return result;
    }
    private static void collectLocal(Path directory,String root, String relative,
                                     ArrayList<Item> result,int depth,ScanBudget budget)throws Exception{
        if(depth>24||result.size()>MAX_FOLDER_FILES)
            throw new IllegalStateException("Папка слишком велика: максимум 30000 файлов / 24 уровня");
        if(Files.isSymbolicLink(directory)||!Files.isDirectory(directory,LinkOption.NOFOLLOW_LINKS))
            throw new SecurityException("Недоступная папка");
        try(DirectoryStream<Path> stream=Files.newDirectoryStream(directory)){
            for(Path child:stream){
                budget.step();
                // Never silently send a subset of a selected folder.
                if(Files.isSymbolicLink(child))
                    throw new SecurityException("Папка содержит символическую ссылку");
                if(!child.toFile().getCanonicalPath().startsWith(root))
                    throw new SecurityException("Элемент выходит за пределы внутренней памяти");
                String name=Util.safeName(child.getFileName().toString());
                if(Files.isDirectory(child,LinkOption.NOFOLLOW_LINKS)){
                    collectLocal(child,root,relative.isEmpty()?name:relative+"/"+name,result,depth+1,budget);
                }else if(Files.isRegularFile(child,LinkOption.NOFOLLOW_LINKS)){
                    if(!Files.isReadable(child))
                        throw new IOException("Нет доступа к файлу: "+name);
                    Item it=new Item();it.id=Util.id();it.uri=Uri.fromFile(child.toFile()).toString();
                    it.name=name;it.size=Files.size(child);it.path=Util.safePath(relative);
                    String original=child.getFileName().toString();
                    int dot=original.lastIndexOf('.');
                    String ext=dot<0?"":original.substring(dot+1).toLowerCase(Locale.ROOT);
                    String mime=MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext);
                    it.mime=mime==null?"application/octet-stream":mime;it.status="В очереди";
                    result.add(it);
                    if(result.size()>MAX_FOLDER_FILES)throw new IllegalStateException("Больше 30000 файлов");
                }else throw new IOException("Не удалось прочитать элемент папки: "+name);
            }
        }
    }
    public static ArrayList<Item> fromDocumentFolder(Context c,Uri tree,String docId,String name)throws Exception{
        ArrayList<Item> result=new ArrayList<>();
        if(tree==null||docId==null||docId.isEmpty())throw new IllegalArgumentException("Папка недоступна");
        collect(c,tree,docId,Util.safePath(name),result,0,new ScanBudget());
        return result;
    }
    public static ArrayList<Item> fromFolder(Context c,Uri tree)throws Exception{
        ArrayList<Item> result=new ArrayList<>();
        String id=DocumentsContract.getTreeDocumentId(tree);
        Uri base=DocumentsContract.buildDocumentUriUsingTree(tree,id);
        String root=Util.name(c,base);
        collect(c,tree,id,root,result,0,new ScanBudget());
        return result;
    }
    private static void collect(Context c,Uri tree,String docId,String path,ArrayList<Item> result,int depth,ScanBudget budget)throws Exception{
        if(!budget.visited.add(docId))throw new IllegalStateException("Обнаружен циклический каталог");
        if(depth>24||result.size()>MAX_FOLDER_FILES)throw new IllegalStateException("Папка слишком велика: максимум 30000 файлов / 24 уровня");
        Uri children=DocumentsContract.buildChildDocumentsUriUsingTree(tree,docId);
        String[]cols={DocumentsContract.Document.COLUMN_DOCUMENT_ID,DocumentsContract.Document.COLUMN_DISPLAY_NAME,
                DocumentsContract.Document.COLUMN_MIME_TYPE,DocumentsContract.Document.COLUMN_SIZE};
        try(Cursor cursor=c.getContentResolver().query(children,cols,null,null,null)){
            if(cursor==null)throw new IllegalStateException("Каталог недоступен");
            while(cursor.moveToNext()){
                budget.step();
                String childId=cursor.getString(0),name=Util.safeName(cursor.getString(1)),mime=cursor.getString(2);
                if(childId==null||childId.isEmpty())
                    throw new IOException("Папка содержит элемент без идентификатора");
                if(DocumentsContract.Document.MIME_TYPE_DIR.equals(mime))collect(c,tree,childId,path+"/"+name,result,depth+1,budget);
                else {
                    Uri u=DocumentsContract.buildDocumentUriUsingTree(tree,childId);
                    // The directory cursor already contains all metadata. Avoid
                    // three extra ContentResolver queries per file (name/size/MIME).
                    Item it=new Item();
                    it.id=Util.id();it.uri=u.toString();it.name=name;
                    it.mime=mime==null||mime.isEmpty()?"application/octet-stream":mime;
                    it.path=path;it.status="В очереди";
                    it.size=cursor.isNull(3)?-1:cursor.getLong(3);
                    result.add(it);
                    if(result.size()>MAX_FOLDER_FILES)throw new IllegalStateException("Больше 30000 файлов");
                }
            }
        }
    }
}
