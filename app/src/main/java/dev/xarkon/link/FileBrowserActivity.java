package dev.xarkon.link;

import android.Manifest;
import android.app.Activity;
import android.content.*;
import android.content.pm.*;
import android.database.Cursor;
import android.graphics.Color;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.drawable.Drawable;
import android.util.LruCache;
import android.util.Size;
import java.lang.ref.WeakReference;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.*;
import android.provider.DocumentsContract;
import android.provider.MediaStore;
import android.text.*;
import android.text.style.ForegroundColorSpan;
import android.text.style.StyleSpan;
import android.view.*;
import android.widget.*;
import java.io.File;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

/** Permission-aware in-app browser. SAF is used only to grant access to external folders. */
public final class FileBrowserActivity extends Activity {
    private static final String[] TABS={"Картинки","Видео","Музыка","Приложения","Файлы"};
    private static final int PICK_TREE=501,MEDIA_PERMISSION=502,STORAGE_PERMISSION=503,MAX_QUEUE=30000,MAX_VISIBLE=60,MAX_MEDIA_SCAN=60000,MAX_SAF_SCAN=120000;
    private final ExecutorService io=Executors.newSingleThreadExecutor();
    private final ExecutorService previews=Executors.newFixedThreadPool(2);
    private final LruCache<String,Bitmap> previewCache=new LruCache<String,Bitmap>(8*1024*1024){
        @Override protected int sizeOf(String key,Bitmap image){return image.getByteCount();}
    };
    // Accessed on the UI thread. Weak references never retain off-screen rows.
    private final HashMap<String,ArrayList<WeakReference<ImageView>>> previewWaiters=new HashMap<>();
    private final LinkedHashMap<String,Entry> selected=new LinkedHashMap<>();
    // Only the current page is bound to views; selection persists across pages and tabs.
    private final HashMap<String,TextView> selectionIndicators=new HashMap<>();
    private final ArrayList<Entry> visibleEntries=new ArrayList<>();
    private final ArrayList<Entry> current=new ArrayList<>();
    private final ArrayDeque<Location> history=new ArrayDeque<>();
    private final HashSet<Integer> permissionPrompted=new HashSet<>();
    private final HashMap<String,ArrayList<Entry>> expandedChildren=new HashMap<>();
    private final HashSet<String> expandedFolders=new HashSet<>();
    private final LinkedHashMap<String,Entry> openedFolders=new LinkedHashMap<>();
    private final HashSet<String> loadingFolders=new HashSet<>();
    private final HashMap<String,CancellationSignal> expansionSignals=new HashMap<>();
    private final HashSet<String> incompleteFolders=new HashSet<>();
    private final HashMap<String,Integer> rowDepths=new HashMap<>();
    private LinearLayout list,tabs,root;
    private ScrollView scroll;
    private int page=0;
    private TextView title,subtitle,count,action,sortButton,empty;
    private EditText search;
    private int accent,bg,card,fg,muted,stroke,tab=0,serial=0,sort=0;
    private String mediaPath="",folderPath="",folderId="";
    private Uri tree;
    private boolean busy=false,storagePermissionRequested=false;
    private boolean safTruncated=false,mediaTruncated=false;
    // Cancel obsolete provider queries when navigating quickly between tabs/folders.
    private CancellationSignal activeQuery;
    private final Handler ui=new Handler(Looper.getMainLooper());
    // Coalesce rapid keystrokes instead of sorting and rebuilding the page each time.
    private final Runnable searchRefresh=()->{page=0;render();};

    private static final class Entry {
        Uri uri,tree;
        String name="",mime="",path="",docId="",group="",version="";
        long size=-1,date=0;
        boolean folder=false,mediaFolder=false;
        int mediaCount=0;
        File localFile;
        String key(){return (folder?"dir:":"file:")+(tree==null?"":tree.toString()+"|")+
            (mediaFolder?group+"|"+path:docId.isEmpty()?uri.toString():docId);}
    }
    private static final class Entries extends ArrayList<Entry> {
        boolean truncated;
    }
    private static final class Location {
        Uri tree;String docId,path,media;
        Location(Uri t,String d,String p,String m){tree=t;docId=d;path=p;media=m;}
    }
    private int dp(float value){return (int)(getResources().getDisplayMetrics().density*value+.5f);}
    private GradientDrawable shape(int color,int border,int radius){
        GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));
        if(border!=0)d.setStroke(dp(1),border);return d;
    }
    private TextView label(String s,int sp,int color,boolean bold){
        TextView t=new TextView(this);t.setText(s);t.setTextColor(color);t.setTextSize(sp);
        if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);return t;
    }
    private void pad(View v,int x,int y){v.setPadding(dp(x),dp(y),dp(x),dp(y));}
    private LinearLayout column(){LinearLayout v=new LinearLayout(this);v.setOrientation(1);return v;}
    private void theme(){
        android.content.SharedPreferences p=getSharedPreferences("settings",0);
        accent=p.getInt("accent",0xff55dfcb);
        String mode=p.getString("theme_mode",p.getBoolean("light",false)?"light":"dark");
        boolean light="light".equals(mode),amoled="amoled".equals(mode);
        bg=amoled?Color.BLACK:light?0xfff5f7fb:0xff0a111b;
        card=amoled?0xff0b0b0d:light?Color.WHITE:0xff121e2a;
        fg=light?0xff152536:0xfff1f6fb;
        muted=light?0xff607587:0xff9caebd;
        stroke=amoled?0xff27282e:light?0xffdce5ed:0xff283947;
        getWindow().setStatusBarColor(bg);getWindow().setNavigationBarColor(bg);
        getWindow().getDecorView().setSystemUiVisibility(light?
            View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR:0);
    }
    @Override public void onCreate(Bundle state){
        super.onCreate(state);theme();buildUi();applyInsets();switchTab(0);
    }
    @Override protected void onResume(){
        super.onResume();
        if(storagePermissionRequested){
            storagePermissionRequested=false;
            if(list!=null){
                for(CancellationSignal signal:expansionSignals.values())signal.cancel();
                expansionSignals.clear();expandedChildren.clear();expandedFolders.clear();openedFolders.clear();
                loadingFolders.clear();incompleteFolders.clear();rowDepths.clear();
                load();
            }
        }
    }
    private boolean hasLocalStorageAccess(){
        if(Build.VERSION.SDK_INT>=30)return Environment.isExternalStorageManager();
        return checkSelfPermission(Manifest.permission.READ_EXTERNAL_STORAGE)==PackageManager.PERMISSION_GRANTED;
    }
    /** All-files access is opt-in, used only for the shared /storage/emulated/0 tree. */
    private void requestLocalStorageAccess(){
        if(hasLocalStorageAccess()){load();return;}
        if(Build.VERSION.SDK_INT<30){
            requestPermissions(new String[]{Manifest.permission.READ_EXTERNAL_STORAGE},STORAGE_PERMISSION);
            return;
        }
        storagePermissionRequested=true;
        try{
            startActivity(new Intent(android.provider.Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                Uri.parse("package:"+getPackageName())));
        }catch(android.content.ActivityNotFoundException missing){
            try{startActivity(new Intent(android.provider.Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION));}
            catch(Exception ignored){
                storagePermissionRequested=false;
                Toast.makeText(this,"Не удалось открыть настройки доступа к файлам",Toast.LENGTH_LONG).show();
            }
        }
    }
    /** Android 15+ draws behind system bars even for legacy target SDKs. */
    private void applyInsets(){
        if(Build.VERSION.SDK_INT>=30)getWindow().setDecorFitsSystemWindows(false);
        root.setOnApplyWindowInsetsListener((view,insets)->{
            int top,bottom;
            if(Build.VERSION.SDK_INT>=30){
                android.graphics.Insets bars=insets.getInsets(
                    WindowInsets.Type.statusBars()|WindowInsets.Type.navigationBars());
                top=bars.top;bottom=bars.bottom;
            }else{top=insets.getSystemWindowInsetTop();bottom=insets.getSystemWindowInsetBottom();}
            view.setPadding(0,top,0,bottom);
            return insets;
        });
        root.requestApplyInsets();
    }
    private int browserStyle(){return Math.max(0,Math.min(2,
        getSharedPreferences("settings",0).getInt("browser_style",2)));}
    /** A custom themed dropdown anchored to the sorting control. */
    private void showSortDialog(){
        final PopupWindow popup=new PopupWindow(this);
        LinearLayout panel=column();pad(panel,12,12);
        panel.setBackground(shape(card,accent,16));
        TextView heading=label("СОРТИРОВКА",12,muted,true);pad(heading,12,10);panel.addView(heading);
        String[] names={"Имя","Дата","Размер","Тип"};int[] values={0,2,1,3};
        for(int i=0;i<names.length;i++){
            final int choice=values[i];boolean active=sort==choice;
            TextView option=label((active?"✓  ":"     ")+names[i],16,active?accent:fg,active);
            pad(option,15,14);option.setBackground(shape(active?bg:card,active?accent:0,10));
            panel.addView(option,new LinearLayout.LayoutParams(-1,-2));
            option.setOnClickListener(v->{sort=choice;page=0;popup.dismiss();render();});
        }
        popup.setContentView(panel);popup.setWidth(dp(230));popup.setHeight(-2);
        popup.setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(Color.TRANSPARENT));
        popup.setOutsideTouchable(true);popup.setFocusable(true);popup.setElevation(dp(12));
        popup.showAsDropDown(sortButton,0,dp(5),Gravity.END);
    }
    private void buildUi(){
        root=column();root.setBackgroundColor(bg);setContentView(root);
        LinearLayout top=new LinearLayout(this);top.setGravity(Gravity.CENTER_VERTICAL);pad(top,16,14);
        TextView back=label("‹",35,accent,true);back.setGravity(Gravity.CENTER);
        top.addView(back,new LinearLayout.LayoutParams(dp(42),dp(44)));
        back.setOnClickListener(v->onBackPressed());
        LinearLayout heads=column();title=label("ПРОВОДНИК",20,fg,true);
        subtitle=label("Выберите файлы для передачи",12,muted,false);
        subtitle.setSingleLine(true);subtitle.setEllipsize(TextUtils.TruncateAt.START);
        heads.addView(title);heads.addView(subtitle);
        top.addView(heads,new LinearLayout.LayoutParams(0,-2,1));root.addView(top);
        HorizontalScrollView horizontal=new HorizontalScrollView(this);
        horizontal.setHorizontalScrollBarEnabled(false);horizontal.setFillViewport(true);
        tabs=new LinearLayout(this);tabs.setGravity(Gravity.CENTER);tabs.setPadding(dp(12),dp(5),dp(12),dp(12));
        horizontal.addView(tabs);root.addView(horizontal);
        LinearLayout tools=new LinearLayout(this);tools.setGravity(Gravity.CENTER_VERTICAL);
        tools.setPadding(dp(16),dp(3),dp(16),dp(10));
        search=new EditText(this);search.setSingleLine(true);search.setTextSize(14);
        search.setHint("Поиск по картинкам");search.setHintTextColor(muted);
        search.setTextColor(fg);search.setBackground(shape(card,stroke,14));
        search.setCompoundDrawablePadding(dp(8));pad(search,12,10);
        tools.addView(search,new LinearLayout.LayoutParams(0,dp(48),1));
        sortButton=label("↕",22,accent,true);sortButton.setGravity(Gravity.CENTER);
        tools.addView(sortButton,new LinearLayout.LayoutParams(dp(52),dp(48)));
        sortButton.setContentDescription("Сортировка файлов");
        sortButton.setOnClickListener(v->showSortDialog());
        root.addView(tools);
        search.addTextChangedListener(new TextWatcher(){
            public void beforeTextChanged(CharSequence s,int start,int c,int after){}
            public void onTextChanged(CharSequence s,int start,int before,int count){
                ui.removeCallbacks(searchRefresh);
                ui.postDelayed(searchRefresh,140);
            }
            public void afterTextChanged(Editable e){}
        });
        scroll=new ScrollView(this);scroll.setFillViewport(true);
        list=column();list.setPadding(dp(16),dp(3),dp(16),dp(20));
        scroll.addView(list);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        LinearLayout footer=column();pad(footer,16,12);
        footer.setBackground(shape(card,stroke,16));
        count=label("Ничего не выбрано",13,muted,false);footer.addView(count);
        LinearLayout selectionTools=new LinearLayout(this);
        selectionTools.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout.LayoutParams toolsParams=new LinearLayout.LayoutParams(-1,dp(40));
        toolsParams.topMargin=dp(8);footer.addView(selectionTools,toolsParams);
        TextView selectPage=label("✓  ВЫБРАТЬ ПАПКУ",11,accent,true);
        selectPage.setGravity(Gravity.CENTER);
        selectPage.setBackground(shape(bg,stroke,11));
        LinearLayout.LayoutParams selectParams=new LinearLayout.LayoutParams(0,-1,1);
        selectParams.rightMargin=dp(6);selectionTools.addView(selectPage,selectParams);
        selectPage.setOnClickListener(v->selectCurrentFolder());
        TextView clear=label("×  СНЯТЬ ВЫБОР",11,fg,true);
        clear.setGravity(Gravity.CENTER);clear.setBackground(shape(bg,stroke,11));
        selectionTools.addView(clear,new LinearLayout.LayoutParams(0,-1,1));
        clear.setOnClickListener(v->clearSelection());
        action=label("ОТПРАВИТЬ",15,Color.BLACK,true);
        action.setGravity(Gravity.CENTER);pad(action,12,15);
        LinearLayout.LayoutParams ap=new LinearLayout.LayoutParams(-1,dp(52));
        ap.topMargin=dp(9);footer.addView(action,ap);
        action.setOnClickListener(v->commitSelection());
        LinearLayout.LayoutParams fp=new LinearLayout.LayoutParams(-1,-2);
        fp.setMargins(dp(12),dp(4),dp(12),dp(10));root.addView(footer,fp);
        updateCount();
    }
    private void updateTabs(){
        tabs.removeAllViews();
        for(int i=0;i<TABS.length;i++){
            final int index=i;int style=browserStyle();
            LinearLayout chip=new LinearLayout(this);chip.setGravity(style==1?Gravity.CENTER:Gravity.CENTER_VERTICAL);
            chip.setOrientation(LinearLayout.HORIZONTAL);chip.setPadding(dp(12),dp(10),dp(12),dp(10));
            chip.setBackground(shape(i==tab?accent:card,i==tab?0:stroke,14));
            if(style!=0){
                String[] glyphs={"image","video","music","apps","file"};
                UiIcon icon=new UiIcon(this,glyphs[i],i==tab?Color.BLACK:accent);
                chip.addView(icon,new LinearLayout.LayoutParams(dp(22),dp(22)));
            }
            if(style!=1){
                TextView title=label(TABS[i],13,i==tab?Color.BLACK:fg,true);
                if(style==2)title.setPadding(dp(7),0,0,0);
                chip.addView(title);
            }
            LinearLayout.LayoutParams lp=style==1?new LinearLayout.LayoutParams(0,-2,1):new LinearLayout.LayoutParams(-2,-2);
            if(style!=1)lp.rightMargin=dp(8);tabs.addView(chip,lp);
            chip.setContentDescription(TABS[i]);
            chip.setOnClickListener(v->switchTab(index));
        }
    }
    private void switchTab(int index){
        tab=index;page=0;tree=null;folderId="";folderPath="";mediaPath="";history.clear();
        for(CancellationSignal signal:expansionSignals.values())signal.cancel();
        expansionSignals.clear();incompleteFolders.clear();
        expandedChildren.clear();expandedFolders.clear();openedFolders.clear();loadingFolders.clear();rowDepths.clear();
        String[] hints={"Поиск по картинкам","Поиск по видео","Поиск по музыке","Поиск по приложениям","Поиск по файлам"};
        search.setHint(hints[index]);
        // Do not expose the previous tab's entries while the new provider query is pending.
        current.clear();safTruncated=false;mediaTruncated=false;
        ui.removeCallbacks(searchRefresh);
        search.setText("");updateTabs();load();
    }
    private boolean isMedia(){return tab<3;}
    private Uri collection(int category){
        if(category==0)return MediaStore.Images.Media.EXTERNAL_CONTENT_URI;
        if(category==1)return MediaStore.Video.Media.EXTERNAL_CONTENT_URI;
        return MediaStore.Audio.Media.EXTERNAL_CONTENT_URI;
    }
    private String permission(){
        if(Build.VERSION.SDK_INT>=33){
            return tab==0?Manifest.permission.READ_MEDIA_IMAGES:
                tab==1?Manifest.permission.READ_MEDIA_VIDEO:Manifest.permission.READ_MEDIA_AUDIO;
        }
        return Manifest.permission.READ_EXTERNAL_STORAGE;
    }
    private boolean hasMediaAccess(){
        if(checkSelfPermission(permission())==PackageManager.PERMISSION_GRANTED)return true;
        return Build.VERSION.SDK_INT>=34&&tab<2&&
            checkSelfPermission(Manifest.permission.READ_MEDIA_VISUAL_USER_SELECTED)==PackageManager.PERMISSION_GRANTED;
    }
    private void requestMedia(){
        if(!isMedia()||hasMediaAccess())return;
        if(Build.VERSION.SDK_INT>=34&&tab<2)
            requestPermissions(new String[]{permission(),Manifest.permission.READ_MEDIA_VISUAL_USER_SELECTED},MEDIA_PERMISSION);
        else requestPermissions(new String[]{permission()},MEDIA_PERMISSION);
    }
    @Override public void onRequestPermissionsResult(int req,String[] p,int[] grants){
        super.onRequestPermissionsResult(req,p,grants);
        if(req==MEDIA_PERMISSION||req==STORAGE_PERMISSION)load();
    }
    private void showMessage(String message,boolean grant){
        list.removeAllViews();
        TextView m=label(message,14,muted,false);m.setGravity(Gravity.CENTER);
        pad(m,15,32);list.addView(m);
        if(grant){
            addWide("РАЗРЕШИТЬ ДОСТУП",this::requestMedia);
            addWide("ВЫБРАТЬ ПАПКУ",this::pickTree);
            addWide("ПОКАЗАТЬ КОРЕНЬ /0",this::requestLocalStorageAccess);
        }
    }
    private void addWide(String text,Runnable action){
        TextView b=label(text,13,accent,true);b.setGravity(Gravity.CENTER);pad(b,15,15);
        b.setBackground(shape(card,stroke,14));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.bottomMargin=dp(8);
        list.addView(b,lp);b.setOnClickListener(v->action.run());
    }
    private void load(){
        page=0;
        if(activeQuery!=null)activeQuery.cancel();
        final CancellationSignal signal=new CancellationSignal();
        activeQuery=signal;
        int token=++serial;
        subtitle.setText(breadcrumb());
        if(isMedia()&&!hasMediaAccess()&&!hasLocalStorageAccess()){
            showMessage("Для просмотра медиа требуется разрешение Android.\nМожно также выбрать папку вручную.",true);
            if(permissionPrompted.add(tab))requestMedia();
            return;
        }
        showMessage("Загрузка файлов…",false);
        final int cat=tab;final Uri rootTree=tree;final String doc=folderId;
        final String mediaFolder=mediaPath;final String displayPath=folderPath;
        io.execute(()->{
            try{
                // Media tabs use MediaStore; only Files traverses every folder in /0.
                ArrayList<Entry> result=cat<3?queryMedia(cat,mediaFolder,false,signal):
                    cat==3?queryApps(signal):queryDocuments(rootTree,doc,displayPath,signal);
                MediaGrouping grouped=cat<3?groupMedia(result,cat):null;
                ui.post(()->{if(token!=serial||isFinishing())return;
                    safTruncated=cat==4&&result instanceof Entries&&((Entries)result).truncated;
                    mediaTruncated=cat<3&&result instanceof Entries&&((Entries)result).truncated;
                    current.clear();
                    if(grouped==null)current.addAll(result);
                    else{
                        expandedFolders.clear();expandedChildren.clear();openedFolders.clear();
                        current.addAll(grouped.folders);
                        for(Entry folder:grouped.folders){
                            String key=folder.key();
                            expandedFolders.add(key);
                            expandedChildren.put(key,grouped.children.get(key));
                        }
                    }
                    render();});
            }catch(Exception ex){
                ui.post(()->{if(token==serial&&!isFinishing())
                    showMessage("Не удалось открыть каталог. "+ErrorText.human(ex),false);});
            }
        });
    }
    /**
     * A folder query must not silently drop older files because the top-level
     * gallery only indexes its newest MAX_QUEUE entries. When a whole folder is
     * selected, reject oversized folders rather than sending an incomplete set.
     */
    private ArrayList<Entry> queryMedia(int cat,String prefix,boolean complete){
        return queryMedia(cat,prefix,complete,null);
    }
    private ArrayList<Entry> queryMedia(int cat,String prefix,boolean complete,CancellationSignal cancellation){
        Entries result=new Entries();
        Uri base=collection(cat);
        String[] cols={MediaStore.MediaColumns._ID,MediaStore.MediaColumns.DISPLAY_NAME,
            MediaStore.MediaColumns.SIZE,MediaStore.MediaColumns.DATE_MODIFIED,
            MediaStore.MediaColumns.MIME_TYPE,MediaStore.MediaColumns.RELATIVE_PATH};
        String selection=prefix.isEmpty()?null:MediaStore.MediaColumns.RELATIVE_PATH+" LIKE ?";
        String[] args=prefix.isEmpty()?null:new String[]{prefix+"%"};
        int scanned=0;
        try(Cursor c=getContentResolver().query(base,cols,selection,args,
                MediaStore.MediaColumns.DATE_MODIFIED+" DESC",cancellation)){
            if(c==null)throw new IllegalStateException("Медиатека недоступна");
            while(c.moveToNext()){
                if(cancellation!=null&&cancellation.isCanceled())throw new OperationCanceledException();
                if(!complete&&++scanned>MAX_MEDIA_SCAN){result.truncated=true;break;}
                String path=c.isNull(5)?"":c.getString(5);
                // LIKE has wildcard semantics; still verify the actual prefix.
                if(!path.startsWith(prefix))continue;
                String name=Util.safeName(c.getString(1));
                String mime=c.getString(4);
                if(!BrowserCategoryFilter.accepts(cat,name,mime))continue;
                if(result.size()>=MAX_QUEUE){
                    if(complete)throw new IllegalStateException(
                        "В папке больше 30000 файлов. Выберите меньшую папку или отдельные файлы.");
                    result.truncated=true;break;
                }
                Entry e=new Entry();
                e.uri=ContentUris.withAppendedId(base,c.getLong(0));
                e.name=name;e.size=c.isNull(2)?-1:c.getLong(2);
                e.date=c.isNull(3)?0:c.getLong(3);
                e.mime=mime;e.path=BrowserMediaFolders.normalize(path);
                result.add(e);
            }
        }
        return result;
    }
    private static final class MediaGrouping {
        final ArrayList<Entry> folders=new ArrayList<>();
        final HashMap<String,ArrayList<Entry>> children=new HashMap<>();
    }
    /** Only media-bearing folders are shown, pre-expanded with their matching files. */
    private MediaGrouping groupMedia(ArrayList<Entry> media,int category){
        MediaGrouping listing=new MediaGrouping();
        LinkedHashMap<String,ArrayList<Entry>> groups=
            BrowserMediaFolders.group(media,entry->entry.path);
        for(Map.Entry<String,ArrayList<Entry>> item:groups.entrySet()){
            if(item.getValue().isEmpty())continue;
            Entry folder=new Entry();folder.folder=true;folder.mediaFolder=true;
            folder.group=TABS[category];folder.path=item.getKey();
            folder.name=BrowserMediaFolders.label(item.getKey());
            folder.mediaCount=item.getValue().size();
            folder.uri=item.getValue().get(0).uri;
            for(Entry file:item.getValue())folder.date=Math.max(folder.date,file.date);
            listing.folders.add(folder);
            listing.children.put(folder.key(),item.getValue());
        }
        return listing;
    }
    private ArrayList<Entry> queryApps(CancellationSignal cancellation)throws Exception{
        PackageManager pm=getPackageManager();
        Intent launch=new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> infos=pm.queryIntentActivities(launch,0);
        LinkedHashSet<String> seen=new LinkedHashSet<>();
        ArrayList<Entry> result=new ArrayList<>();
        for(ResolveInfo info:infos){
            if(cancellation.isCanceled())throw new OperationCanceledException();
            if(info.activityInfo==null)continue;
            String pkg=info.activityInfo.packageName;
            if(!seen.add(pkg))continue;
            try{
                ApplicationInfo app=pm.getApplicationInfo(pkg,0);
                File apk=new File(app.publicSourceDir);
                if(!apk.isFile())continue;
                Entry e=new Entry();e.name=Util.safeName(pm.getApplicationLabel(app).toString());
                try{PackageInfo pkgInfo=pm.getPackageInfo(pkg,0);
                    e.version=pkgInfo.versionName==null?"Неизвестна":pkgInfo.versionName;
                }catch(Exception ignored){e.version="Неизвестна";}
                e.uri=Uri.parse("content://dev.xarkon.link.updates/installed/"+Uri.encode(pkg));
                e.mime="application/vnd.android.package-archive";
                e.size=apk.length();e.date=apk.lastModified()/1000;
                result.add(e);
            }catch(Exception ignored){}
        }
        // Applications shows installed packages only, never directories or archives from /0.
        return result;
    }
    /** Stream the actual shared-storage root, without materialising an unbounded file array. */
    private ArrayList<Entry> queryLocal(File directory,CancellationSignal cancellation)throws Exception{
        return queryLocal(directory,cancellation,4);
    }
    private ArrayList<Entry> queryLocal(File directory,CancellationSignal cancellation,int category)throws Exception{
        if(!hasLocalStorageAccess())throw new SecurityException("Нет разрешения на внутреннюю память");
        File base=Environment.getExternalStorageDirectory().getCanonicalFile();
        File folder=directory.getCanonicalFile();
        String rootPath=base.getPath();
        if(!folder.equals(base)&&!folder.getPath().startsWith(rootPath+File.separator))
            throw new SecurityException("Папка находится вне внутренней памяти");
        if(!Files.isDirectory(folder.toPath(),LinkOption.NOFOLLOW_LINKS))
            throw new IllegalStateException("Каталог недоступен");
        Entries result=new Entries();
        ArrayList<Entry> directories=new ArrayList<>(),files=new ArrayList<>();
        String parent=base.toPath().relativize(folder.toPath()).toString().replace(File.separatorChar,'/');
        int scanned=0;
        try(DirectoryStream<Path> stream=Files.newDirectoryStream(folder.toPath())){
            for(Path child:stream){
                if(cancellation!=null&&cancellation.isCanceled())throw new OperationCanceledException();
                if(++scanned>MAX_SAF_SCAN){result.truncated=true;break;}
                // Do not follow symbolic links or expose locations outside /storage/emulated/0.
                if(Files.isSymbolicLink(child))continue;
                boolean isDir=Files.isDirectory(child,LinkOption.NOFOLLOW_LINKS);
                if(!isDir&&!Files.isRegularFile(child,LinkOption.NOFOLLOW_LINKS))continue;
                File file=child.toFile();
                if(!file.getCanonicalPath().startsWith(rootPath+File.separator))continue;
                Entry e=new Entry();e.localFile=file;e.uri=Uri.fromFile(file);
                e.name=Util.safeName(file.getName());e.folder=isDir;
                e.path=isDir?(parent.isEmpty()?e.name:parent+"/"+e.name):parent;
                e.size=isDir?-1:file.length();e.date=file.lastModified()/1000;
                e.mime=isDir?DocumentsContract.Document.MIME_TYPE_DIR:
                    java.net.URLConnection.guessContentTypeFromName(file.getName());
                if(e.mime==null)e.mime="application/octet-stream";
                // Always display directories; only files are filtered by category.
                // A selected directory is collected separately, with ALL descendants.
                if(!isDir&&!BrowserCategoryFilter.accepts(category,file.getName(),e.mime))continue;
                if(category==3&&!isDir){
                    e.version="Неизвестна";
                    if(file.getName().toLowerCase(Locale.ROOT).endsWith(".apk")){
                        try{
                            PackageInfo archive=getPackageManager().getPackageArchiveInfo(file.getPath(),0);
                            if(archive!=null&&archive.versionName!=null)e.version=archive.versionName;
                        }catch(Exception ignored){}
                    }
                }
                ArrayList<Entry> target=isDir?directories:files;
                if(target.size()<MAX_QUEUE)target.add(e);
                else result.truncated=true;
            }
        }
        result.addAll(directories);result.addAll(files);
        return result;
    }
    private ArrayList<Entry> queryDocuments(Uri rootTree,String doc,String displayPath,CancellationSignal cancellation)throws Exception{
        Entries result=new Entries();
        if(rootTree==null){
            if(hasLocalStorageAccess()){
                ArrayList<Entry> local=queryLocal(Environment.getExternalStorageDirectory(),cancellation);
                result.addAll(local);
                if(local instanceof Entries)result.truncated=((Entries)local).truncated;
            }
            // Keep individually authorised SAF folders accessible even without broad access.
            for(UriPermission perm:getContentResolver().getPersistedUriPermissions()){
                if(cancellation.isCanceled())throw new OperationCanceledException();
                if(!perm.isReadPermission())continue;
                Uri u=perm.getUri();
                try{
                    String id=DocumentsContract.getTreeDocumentId(u);
                    Uri d=DocumentsContract.buildDocumentUriUsingTree(u,id);
                    Entry e=new Entry();e.folder=true;e.tree=u;e.docId=id;
                    e.name=Util.name(this,d);e.uri=d;result.add(e);
                }catch(Exception ignored){}
            }
            return result;
        }
        Uri children=DocumentsContract.buildChildDocumentsUriUsingTree(rootTree,doc);
        String[] cols={DocumentsContract.Document.COLUMN_DOCUMENT_ID,
            DocumentsContract.Document.COLUMN_DISPLAY_NAME,
            DocumentsContract.Document.COLUMN_MIME_TYPE,DocumentsContract.Document.COLUMN_SIZE,
            DocumentsContract.Document.COLUMN_LAST_MODIFIED};
        try(Cursor c=getContentResolver().query(children,cols,null,null,null,cancellation)){
            if(c==null)throw new IllegalStateException("Папка недоступна");
            // Keep subdirectories navigable even when a provider returns thousands
            // of files first. Bound memory and mark incomplete listings explicitly.
            ArrayList<Entry> directories=new ArrayList<>();
            ArrayList<Entry> files=new ArrayList<>();
            int scanned=0;
            while(c.moveToNext()){
                if(cancellation.isCanceled())throw new OperationCanceledException();
                if(++scanned>MAX_SAF_SCAN){result.truncated=true;break;}
                Entry e=new Entry();e.docId=c.getString(0);e.name=Util.safeName(c.getString(1));
                e.mime=c.getString(2);e.folder=DocumentsContract.Document.MIME_TYPE_DIR.equals(e.mime);
                e.size=c.isNull(3)?-1:c.getLong(3);e.date=c.isNull(4)?0:c.getLong(4)/1000;
                e.tree=rootTree;e.uri=DocumentsContract.buildDocumentUriUsingTree(rootTree,e.docId);
                e.path=displayPath;
                ArrayList<Entry> target=e.folder?directories:files;
                if(target.size()<MAX_QUEUE)target.add(e);
                else result.truncated=true;
            }
            result.addAll(directories);
            result.addAll(files);
        }
        return result;
    }
    private Entry focusedFolder(){
        Entry focus=null;
        for(Entry e:openedFolders.values())if(expandedFolders.contains(e.key()))focus=e;
        return focus;
    }
    private String breadcrumb(){
        Entry focus=focusedFolder();
        if(focus==null)return "Внутренняя память";
        if(focus.localFile!=null||focus.mediaFolder)return BrowserBreadcrumbs.format(focus.path);
        if(focus.tree!=null){
            String id=focus.docId;int colon=id.indexOf(':');
            if(colon>=0)id=id.substring(colon+1);
            return BrowserBreadcrumbs.format(id.isEmpty()?focus.name:id);
        }
        return BrowserBreadcrumbs.format(focus.name);
    }
    private void render(){
        if(list==null)return;
        subtitle.setText(breadcrumb());
        list.removeAllViews();
        selectionIndicators.clear();visibleEntries.clear();
        if(tab==4&&tree==null){
            if(!hasLocalStorageAccess())addWide("РАЗРЕШИТЬ ДОСТУП К ВНУТРЕННЕЙ ПАМЯТИ",this::requestLocalStorageAccess);
            addWide("СИСТЕМНЫЙ ПРОВОДНИК",this::pickTree);
        }

        String filter=search.getText().toString().trim().toLowerCase(Locale.ROOT);
        // Category search includes indexed files in nested media folders, even
        // when the folder has not yet been expanded. SAF search respects grants.
        ArrayList<Entry> rows=new ArrayList<>(current);
        rowDepths.clear();
        Comparator<Entry> cmp=(a,b)->{
            if(a.folder!=b.folder)return a.folder?-1:1;
            if(sort==1)return Long.compare(b.size,a.size);
            if(sort==2)return Long.compare(b.date,a.date);
            if(sort==3){String am=a.mime==null?"":a.mime,bm=b.mime==null?"":b.mime;
                int r=am.compareToIgnoreCase(bm);if(r!=0)return r;}
            return a.name.compareToIgnoreCase(b.name);
        };
        Collections.sort(rows,cmp);
        ArrayList<Entry> flattened=new ArrayList<>();
        HashSet<String> renderedKeys=new HashSet<>();
        for(Entry entry:rows)appendExpanded(flattened,entry,0,cmp,renderedKeys);
        rows=flattened;
        // Search after expanding the tree so a matching SAF child remains visible
        // even when the parent folder's name does not match the query.
        if(!filter.isEmpty())rows=new ArrayList<>(BrowserSearchTree.filter(rows,
            e->rowDepths.getOrDefault(e.key(),0),e->e.name,filter));
        if(rows.isEmpty()){
            TextView nothing=label(tab==4&&tree==null?"Нет доступных файлов. Проверьте разрешения или выберите папку":
                "В этом разделе пока нет файлов",14,muted,false);
            nothing.setGravity(Gravity.CENTER);pad(nothing,8,35);list.addView(nothing);
        }
        // Only build one page of rows: a 30000-item directory must not create
        // hundreds of Android Views on every search, selection or tab change.
        int pages=Math.max(1,(rows.size()+MAX_VISIBLE-1)/MAX_VISIBLE);
        page=Math.max(0,Math.min(page,pages-1));
        int from=page*MAX_VISIBLE,to=Math.min(rows.size(),from+MAX_VISIBLE);
        for(int i=from;i<to;i++){
            Entry entry=rows.get(i);visibleEntries.add(entry);drawRow(entry,rowDepths.getOrDefault(entry.key(),0));
        }
        if(rows.size()>MAX_VISIBLE){
            TextView position=label("Показаны "+(from+1)+"–"+to+" из "+rows.size()+
                " · страница "+(page+1)+"/"+pages,12,muted,false);
            position.setGravity(Gravity.CENTER);pad(position,10,14);list.addView(position);
            if(page>0)addWide("← ПРЕДЫДУЩИЕ",()->changePage(-1));
            if(page+1<pages)addWide("СЛЕДУЮЩИЕ →",()->changePage(1));
        }
        if(tab==4&&safTruncated){
            TextView cap=label("Каталог очень большой: показана только часть содержимого. Для полного выбора откройте вложенную папку или предоставьте доступ к более узкому каталогу.",12,muted,false);
            pad(cap,10,12);list.addView(cap);
        }
        if(isMedia()&&mediaTruncated){
            TextView cap=label("Список файлов ограничен 30000, поиск папок — первыми 60 000 записями. Для полного доступа к старым файлам откройте нужную папку в разделе «Файлы».",12,muted,false);
            pad(cap,10,12);list.addView(cap);
        }
    }
    private void changePage(int delta){
        page=Math.max(0,page+delta);render();
        if(scroll!=null)scroll.post(()->scroll.smoothScrollTo(0,0));
    }
    private void drawRow(Entry e,int depth){
        LinearLayout row=new LinearLayout(this);row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(12+Math.min(7,depth)*10),dp(11),dp(9),dp(11));
        row.setBackground(shape(card,stroke,14));
        LinearLayout.LayoutParams rp=new LinearLayout.LayoutParams(-1,-2);rp.bottomMargin=dp(8);
        list.addView(row,rp);
        row.setContentDescription(e.folder?
            "Папка "+e.name+(e.mediaFolder?", найдено файлов: "+e.mediaCount:""):
            (tab==3?"Приложение ":"Файл ")+e.name);
        String glyph=e.folder&&!e.mediaFolder?"folder":
            tab==0?"image":tab==1?"video":tab==2?"music":tab==3?"apps":"file";
        int style=browserStyle();
        if(style==1){
            FrameLayout tile=new FrameLayout(this);
            UiIcon centered=new UiIcon(this,glyph,accent);
            // Center real previews too, not only the generic category glyph.
            View centeredContent=e.uri!=null&&(!e.folder||e.mediaFolder)?
                previewFrame(e,centered,tab):centered;
            tile.addView(centeredContent,
                new FrameLayout.LayoutParams(dp(40),dp(40),Gravity.CENTER));
            if(e.folder){
                TextView arrow=label(expandedFolders.contains(e.key())?"⌄":"›",20,accent,true);
                arrow.setGravity(Gravity.CENTER);
                tile.addView(arrow,new FrameLayout.LayoutParams(dp(30),dp(40),Gravity.START|Gravity.CENTER_VERTICAL));
            }
            boolean checked=selected.containsKey(e.key());
            TextView check=label(checked?"✓":"＋",22,checked?Color.BLACK:accent,true);
            check.setGravity(Gravity.CENTER);check.setBackground(shape(checked?accent:bg,checked?0:stroke,11));
            tile.addView(check,new FrameLayout.LayoutParams(dp(39),dp(39),Gravity.END|Gravity.CENTER_VERTICAL));
            row.addView(tile,new LinearLayout.LayoutParams(-1,dp(54)));
            selectionIndicators.put(e.key(),check);
            check.setOnClickListener(v->toggle(e));
            row.setOnClickListener(v->{if(e.folder)expandFolder(e);else toggle(e);});
            row.setOnLongClickListener(v->{toggle(e);return true;});
            return;
        }
        if(e.folder){
            TextView arrow=label(expandedFolders.contains(e.key())?"⌄":"›",20,accent,true);
            arrow.setGravity(Gravity.CENTER);
            row.addView(arrow,new LinearLayout.LayoutParams(dp(20),dp(36)));
        }
        UiIcon icon=new UiIcon(this,glyph,accent);
        if(style!=0){
            if((!e.folder&&(tab==0||tab==1||tab==3))||
                (e.mediaFolder&&e.uri!=null))addPreview(row,e,icon,tab);
            else row.addView(icon,new LinearLayout.LayoutParams(dp(36),dp(36)));
        }
        LinearLayout detail=column();detail.setPadding(dp(10),0,dp(4),0);
        String display=e.name;
        if(tab==3&&display.toLowerCase(Locale.ROOT).endsWith(".apk"))display=display.substring(0,display.length()-4);
        TextView name=label(display,14,fg,true);name.setMaxLines(style==1?1:2);name.setEllipsize(TextUtils.TruncateAt.END);
        detail.addView(name);
        // Counts describe items currently indexed, not the total in a truncated library.
        String sub=e.mediaFolder?
            (tab==0?"Найдено изображений: ":tab==1?"Найдено видео: ":"Найдено аудиофайлов: ")+e.mediaCount:
            e.folder?(loadingFolders.contains(e.key())?"Загрузка папки…":
            incompleteFolders.contains(e.key())?"Показана часть содержимого · нажмите, чтобы свернуть":
            expandedFolders.contains(e.key())?"Папка · нажмите, чтобы свернуть":"Папка · нажмите, чтобы раскрыть"):
            Util.readable(e.size)+(e.mime==null||e.mime.isEmpty()?"":" · "+e.mime);
        if(tab==3&&!e.folder)sub="Размер: "+Util.readable(e.size)+" | Версия: "+e.version;
        if(style!=1||e.folder||tab==3){
            TextView meta=label(sub,11,muted,false);meta.setSingleLine(true);
            meta.setEllipsize(TextUtils.TruncateAt.END);
            if(tab==3&&!e.folder){
                SpannableStringBuilder rich=new SpannableStringBuilder(sub);
                int sizeStart="Размер: ".length(),sizeEnd=sub.indexOf(" | Версия:");
                int versionStart=sizeEnd+" | Версия: ".length();
                for(int[] range:new int[][]{{sizeStart,sizeEnd},{versionStart,sub.length()}}){
                    rich.setSpan(new ForegroundColorSpan(accent),range[0],range[1],Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                    rich.setSpan(new StyleSpan(Typeface.BOLD),range[0],range[1],Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                }
                meta.setText(rich);
            }
            detail.addView(meta);
        }
        row.addView(detail,new LinearLayout.LayoutParams(0,-2,1));
        boolean checked=selected.containsKey(e.key());
        TextView check=label(checked?"✓":"＋",22,checked?Color.BLACK:accent,true);
        check.setGravity(Gravity.CENTER);check.setBackground(shape(checked?accent:bg,checked?0:stroke,11));
        row.addView(check,new LinearLayout.LayoutParams(dp(39),dp(39)));
        selectionIndicators.put(e.key(),check);
        check.setOnClickListener(v->toggle(e));
        row.setOnClickListener(v->{if(e.folder)expandFolder(e);else toggle(e);});
        row.setOnLongClickListener(v->{toggle(e);return true;});
    }
    /** Asynchronous, bounded-memory thumbnails; never decode images on the UI thread. */
    private void addPreview(LinearLayout row,Entry entry,UiIcon placeholder,int category){
        row.addView(previewFrame(entry,placeholder,category),
            new LinearLayout.LayoutParams(dp(40),dp(40)));
    }
    /** A shared cover renderer for list rows and icon-only tiles. */
    private FrameLayout previewFrame(Entry entry,UiIcon placeholder,int category){
        FrameLayout frame=new FrameLayout(this);
        frame.setBackground(shape(bg,stroke,11));
        frame.setClipToOutline(true);
        frame.addView(placeholder,new FrameLayout.LayoutParams(-1,-1));
        ImageView image=new ImageView(this);
        image.setScaleType(ImageView.ScaleType.CENTER_CROP);
        image.setVisibility(View.GONE);
        frame.addView(image,new FrameLayout.LayoutParams(-1,-1));
        String key=entry.uri.toString();
        Bitmap cached=previewCache.get(key);
        if(cached!=null){
            image.setImageBitmap(cached);image.setVisibility(View.VISIBLE);return frame;
        }
        ArrayList<WeakReference<ImageView>> waiting=previewWaiters.get(key);
        if(waiting==null){
            waiting=new ArrayList<>();previewWaiters.put(key,waiting);
            final Uri uri=entry.uri;
            previews.execute(()->{
                Bitmap bitmap=null;
                try{
                    if(category==3){
                        Drawable icon=getPackageManager().getApplicationIcon(uri.getLastPathSegment());
                        int side=dp(72);
                        bitmap=Bitmap.createBitmap(side,side,Bitmap.Config.ARGB_8888);
                        Canvas canvas=new Canvas(bitmap);
                        icon.setBounds(0,0,side,side);icon.draw(canvas);
                    }else{
                        bitmap=getContentResolver().loadThumbnail(uri,new Size(dp(80),dp(80)),null);
                    }
                }catch(Exception ignored){
                    // Keep the category icon when Android denies a thumbnail.
                }
                final Bitmap ready=bitmap;
                ui.post(()->{
                    if(isDestroyed())return;
                    if(ready!=null)previewCache.put(key,ready);
                    ArrayList<WeakReference<ImageView>> listeners=previewWaiters.remove(key);
                    if(listeners==null||ready==null)return;
                    for(WeakReference<ImageView> ref:listeners){
                        ImageView view=ref.get();
                        // The decode may finish before a newly created row is attached.
                        // Binding the bitmap is safe even before the first layout pass.
                        if(view!=null){
                            view.setImageBitmap(ready);view.setVisibility(View.VISIBLE);
                        }
                    }
                });
            });
        }
        waiting.add(new WeakReference<>(image));
        return frame;
    }
    private void refreshIndicator(String key){
        TextView indicator=selectionIndicators.get(key);
        if(indicator==null)return;
        boolean checked=selected.containsKey(key);
        indicator.setText(checked?"✓":"＋");
        indicator.setTextColor(checked?Color.BLACK:accent);
        indicator.setBackground(shape(checked?accent:bg,checked?0:stroke,11));
    }
    private void toggle(Entry e){
        if(busy)return;
        String key=e.key();
        if(selected.containsKey(key))selected.remove(key);
        else{
            if(selected.size()>=MAX_QUEUE){
                Toast.makeText(this,"Не более 30000 объектов в одной операции",Toast.LENGTH_SHORT).show();
                return;
            }
            selected.put(key,e);
        }
        refreshIndicator(key);
        updateCount();
        // Do not rebuild up to 60 rows (and restart their thumbnails) per tap.
    }
    private void selectCurrentFolder(){
        if(busy)return;
        Entry folder=focusedFolder();
        if(folder==null){
            if(!hasLocalStorageAccess()){
                Toast.makeText(this,"Откройте доступную папку или разрешите доступ к внутренней памяти",Toast.LENGTH_LONG).show();
                return;
            }
            File base=Environment.getExternalStorageDirectory();
            folder=new Entry();folder.folder=true;folder.localFile=base;
            folder.uri=Uri.fromFile(base);folder.name="Внутренняя память";folder.path="";
        }
        if(folder.mediaFolder&&!hasLocalStorageAccess()){
            Toast.makeText(this,"Для полного выбора папки разрешите доступ к внутренней памяти",Toast.LENGTH_LONG).show();
            return;
        }
        // The folder is expanded into every descendant at commit time, not just visible rows.
        if(!selected.containsKey(folder.key())&&selected.size()>=MAX_QUEUE){
            Toast.makeText(this,"Слишком много выбранных папок и файлов",Toast.LENGTH_LONG).show();
            return;
        }
        // Selecting another folder must not discard the user's earlier choices.
        selected.put(folder.key(),folder);
        for(String key:selectionIndicators.keySet())refreshIndicator(key);
        updateCount();
        Toast.makeText(this,"Выбрана вся папка. Вложенные файлы проверяются при отправке.",Toast.LENGTH_SHORT).show();
    }
    private void clearSelection(){
        if(busy||selected.isEmpty())return;
        selected.clear();
        for(String key:selectionIndicators.keySet())refreshIndicator(key);
        updateCount();
    }
    private void updateCount(){
        if(count==null)return;
        if(selected.isEmpty())count.setText("Ничего не выбрано");
        else{
            int folders=0,unknown=0;
            long bytes=0;
            for(Entry e:selected.values()){
                if(e.folder){folders++;continue;}
                if(e.size<0){unknown++;continue;}
                bytes=Long.MAX_VALUE-bytes<e.size?Long.MAX_VALUE:bytes+e.size;
            }
            String summary="Выбрано: "+selected.size()+" · файлов: "+(selected.size()-folders)+
                " · папок: "+folders+" · размер файлов: "+Util.readable(bytes);
            if(folders>0||unknown>0)summary+=" (без размера папок"+(unknown>0?", неизвестно: "+unknown:"")+")";
            if(selected.size()==1&&folders==1){
                Entry folder=selected.values().iterator().next();
                summary="Папка: "+folder.name+" · все вложенные файлы будут проверены при отправке";
            }
            count.setText(summary);
        }
        action.setAlpha(selected.isEmpty()||busy?.42f:1f);
        action.setBackground(shape(accent,0,14));
    }
    /** Build direct children only. Nested folders are queried on demand and cached. */
    private ArrayList<Entry> mediaRows(List<Entry> entries,String prefix){
        ArrayList<Entry> rows=new ArrayList<>();
        LinkedHashMap<String,Entry> folders=new LinkedHashMap<>();
        for(Entry e:entries){
            if(e.mediaFolder){if(e.path.startsWith(prefix)&&!e.path.equals(prefix))
                folders.putIfAbsent(e.path,e);continue;}
            if(!e.path.startsWith(prefix))continue;
            String remaining=e.path.substring(prefix.length());
            if(!remaining.isEmpty()){
                int slash=remaining.indexOf('/');
                String segment=slash<0?remaining:remaining.substring(0,slash);
                if(segment.isEmpty())continue;
                String path=prefix+segment+"/";
                if(!folders.containsKey(path)){
                    Entry f=new Entry();f.folder=true;f.mediaFolder=true;f.group=TABS[tab];
                    f.path=path;f.name=segment;folders.put(path,f);
                }
            }else rows.add(e);
        }
        rows.addAll(0,folders.values());
        return rows;
    }
    private void appendExpanded(ArrayList<Entry> result,Entry entry,int depth,
                                Comparator<Entry> cmp,Set<String> seen){
        if(depth>16||result.size()>=MAX_SAF_SCAN||!seen.add(entry.key()))return;
        rowDepths.put(entry.key(),depth);result.add(entry);
        if(!entry.folder||!expandedFolders.contains(entry.key()))return;
        ArrayList<Entry> children=expandedChildren.get(entry.key());
        if(children==null)return;
        ArrayList<Entry> direct=entry.mediaFolder?mediaRows(children,entry.path):new ArrayList<>(children);
        direct.sort(cmp);
        for(Entry child:direct)appendExpanded(result,child,depth+1,cmp,seen);
    }
    private boolean descendantOf(Entry child,Entry parent){
        if(child==parent)return true;
        if(child.localFile!=null&&parent.localFile!=null)
            return child.localFile.toPath().startsWith(parent.localFile.toPath());
        if(child.mediaFolder&&parent.mediaFolder)
            return BrowserPathRules.isSameOrDescendant(child.path,parent.path);
        return child.tree!=null&&parent.tree!=null&&child.tree.equals(parent.tree)&&
            child.docId.startsWith(parent.docId+"/");
    }
    private void expandFolder(Entry e){
        String key=e.key();
        if(expandedFolders.remove(key)){
            for(Entry opened:new ArrayList<>(openedFolders.values())){
                if(!descendantOf(opened,e))continue;
                String childKey=opened.key();
                openedFolders.remove(childKey);expandedFolders.remove(childKey);
                CancellationSignal old=expansionSignals.remove(childKey);
                if(old!=null)old.cancel();
                loadingFolders.remove(childKey);
            }
            render();return;
        }
        expandedFolders.add(key);openedFolders.remove(key);openedFolders.put(key,e);
        if(expandedChildren.containsKey(key)){render();return;}
        if(!loadingFolders.add(key))return;
        final int token=serial,category=tab;
        final CancellationSignal signal=new CancellationSignal();
        expansionSignals.put(key,signal);
        render();
        io.execute(()->{
            try{
                ArrayList<Entry> children=e.localFile!=null?queryLocal(e.localFile,signal,category):
                    e.mediaFolder?queryMedia(category,e.path,false,signal):
                    queryDocuments(e.tree,e.docId,e.name,signal);
                ui.post(()->{
                    if(expansionSignals.get(key)!=signal)return;
                    expansionSignals.remove(key);loadingFolders.remove(key);
                    if(token!=serial||isFinishing())return;
                    if(children instanceof Entries&&((Entries)children).truncated){
                        incompleteFolders.add(key);
                        Toast.makeText(this,"Каталог слишком большой: показана часть файлов",
                            Toast.LENGTH_LONG).show();
                    }else incompleteFolders.remove(key);
                    expandedChildren.put(key,children);render();
                });
            }catch(Exception error){
                ui.post(()->{
                    if(expansionSignals.get(key)!=signal)return;
                    expansionSignals.remove(key);loadingFolders.remove(key);
                    if(token!=serial||isFinishing())return;
                    expandedFolders.remove(key);
                    if(!(error instanceof OperationCanceledException))
                        Toast.makeText(this,"Не удалось раскрыть папку",Toast.LENGTH_SHORT).show();
                    render();
                });
            }
        });
    }
    @Override public void onBackPressed(){
        Entry focused=focusedFolder();
        if(focused!=null){expandFolder(focused);return;}
        if(!history.isEmpty()){
            Location l=history.pop();tree=l.tree;folderId=l.docId;folderPath=l.path;mediaPath=l.media;
            search.setText("");load();return;
        }
        super.onBackPressed();
    }
    private void pickTree(){
        try{
            Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
            startActivityForResult(intent,PICK_TREE);
        }catch(Exception e){Toast.makeText(this,"Выбор папки недоступен. "+ErrorText.human(e),Toast.LENGTH_LONG).show();}
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request!=PICK_TREE||result!=RESULT_OK||data==null||data.getData()==null)return;
        Uri uri=data.getData();
        try{
            getContentResolver().takePersistableUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION);
            // Open the granted folder immediately. Back returns to the saved roots.
            String id=DocumentsContract.getTreeDocumentId(uri);
            Uri rootDocument=DocumentsContract.buildDocumentUriUsingTree(uri,id);
            tab=4;tree=null;folderId="";folderPath="";
            for(CancellationSignal signal:expansionSignals.values())signal.cancel();
            expansionSignals.clear();incompleteFolders.clear();
            expandedChildren.clear();expandedFolders.clear();openedFolders.clear();loadingFolders.clear();
            // Show the granted root in the tree instead of navigating into it.
            tree=null;
            mediaPath="";history.clear();
            // The granted folder appears among the available roots.
            current.clear();safTruncated=false;
            ui.removeCallbacks(searchRefresh);
            search.setText("");updateTabs();load();
        }catch(Exception e){Toast.makeText(this,"Нет доступа к папке. "+ErrorText.human(e),Toast.LENGTH_LONG).show();}
    }
    private void commitSelection(){
        if(busy||selected.isEmpty())return;
        busy=true;updateCount();action.setText("ПОДГОТОВКА ФАЙЛОВ…");
        ArrayList<Entry> items=new ArrayList<>(selected.values());
        io.execute(()->{
            try{
                ArrayList<FileCatalog.Item> jobs=new ArrayList<>();
                HashSet<String> used=new HashSet<>();
                for(Entry e:items){
                    if(e.folder){
                        ArrayList<FileCatalog.Item> folderJobs;
                        if(e.mediaFolder){
                            // MediaStore indexes only category files. Never silently send
                            // an incomplete folder when the user selected ALL descendants.
                            if(!hasLocalStorageAccess())throw new SecurityException(
                                "Для отправки всей папки разрешите доступ к /0 или выберите папку через системный проводник.");
                            File storage=Environment.getExternalStorageDirectory();
                            folderJobs=FileCatalog.fromLocalFolder(this,new File(storage,e.path),e.path);
                        }else{
                            folderJobs=e.localFile!=null?
                                FileCatalog.fromLocalFolder(this,e.localFile,e.path):
                                FileCatalog.fromDocumentFolder(this,e.tree,e.docId,e.name);
                        }
                        for(FileCatalog.Item f:folderJobs)
                            if(used.add(f.uri))jobs.add(f);
                    }else addJob(jobs,used,e,e.path);
                    if(jobs.size()>MAX_QUEUE)throw new IllegalStateException("Не более 30000 файлов в одной операции");
                }
                if(jobs.isEmpty())throw new IllegalStateException("В выбранных папках нет доступных файлов");
                FileCatalog.append(this,jobs);
                ui.post(()->{setResult(RESULT_OK,new Intent());finish();});
            }catch(Exception e){
                ui.post(()->{busy=false;action.setText("ОТПРАВИТЬ");
                    updateCount();Toast.makeText(this,ErrorText.human("Ошибка: "+e.getMessage()),Toast.LENGTH_LONG).show();});
            }
        });
    }
    private void addJob(ArrayList<FileCatalog.Item> jobs,Set<String> used,Entry e,String path){
        if(e.uri==null||!used.add(e.uri.toString()))return;
        FileCatalog.Item it=new FileCatalog.Item();
        it.id=Util.id();it.uri=e.uri.toString();
        it.name=Util.safeName(tab==3&&!e.name.endsWith(".apk")?e.name+".apk":e.name);
        it.mime=e.mime==null||e.mime.isEmpty()?"application/octet-stream":e.mime;
        it.size=e.size;it.path=Util.safePath(path);it.status="В очереди";
        jobs.add(it);
    }
    @Override protected void onDestroy(){
        ++serial;if(activeQuery!=null)activeQuery.cancel();
        for(CancellationSignal signal:expansionSignals.values())signal.cancel();
        expansionSignals.clear();
        ui.removeCallbacks(searchRefresh);
        io.shutdownNow();previews.shutdownNow();previewWaiters.clear();
        previewCache.evictAll();super.onDestroy();
    }
}
