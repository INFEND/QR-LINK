package dev.xarkon.link;

import java.util.*;

/** Pure selection-size accounting, independent of Android UI and SAF providers.
 * A selected folder already contains its descendants; independently selected
 * files inside it must never be added twice.
 */
final class BrowserSelectionTotals {
    static final class Selection {
        final String key,uri,path;
        final boolean folder;
        final long bytes,provisionalBytes;
        Selection(String key,String uri,String path,boolean folder,long bytes,long provisionalBytes){
            this.key=key;this.uri=uri;this.path=normalize(path);
            this.folder=folder;this.bytes=bytes;this.provisionalBytes=provisionalBytes;
        }
    }
    static final class FolderStats {
        final LinkedHashMap<String,Long> files;
        final boolean unknown;
        FolderStats(Map<String,Long> files,boolean unknown){
            this.files=new LinkedHashMap<>(files);this.unknown=unknown;
        }
    }
    static final class Result {
        final long bytes;
        final boolean pending,unknown,provisional;
        Result(long bytes,boolean pending,boolean unknown,boolean provisional){
            this.bytes=bytes;this.pending=pending;this.unknown=unknown;this.provisional=provisional;
        }
    }
    private BrowserSelectionTotals(){}
    private static String normalize(String p){
        if(p==null)return "";
        String result=p.replace('\\','/');
        while(result.endsWith("/"))result=result.substring(0,result.length()-1);
        return result;
    }
    private static boolean inside(String folder,String path){
        return folder.isEmpty()||path.equals(folder)||path.startsWith(folder+"/");
    }
    private static boolean sameSharedStorage(String folderUri,String fileUri){
        return isSharedUri(folderUri)&&isSharedUri(fileUri);
    }
    private static boolean isSharedUri(String uri){
        return uri!=null&&(uri.startsWith("file:/")||
            uri.startsWith("content://media/"));
    }
    private static long add(long a,long b){
        return b<0||Long.MAX_VALUE-a<b?Long.MAX_VALUE:a+b;
    }
    /** A selected parent already represents every nested shared-storage folder.
     * Ignore overlapping child estimates, including while the parent is loading.
     */
    private static boolean coveredByAnotherFolder(Selection folder,List<Selection> all,int index){
        for(int j=0;j<all.size();j++){
            if(j==index)continue;
            Selection parent=all.get(j);
            if(!parent.folder)continue;
            boolean sameSource=sameSharedStorage(parent.uri,folder.uri)||
                (!parent.uri.isEmpty()&&parent.uri.equals(folder.uri));
            if(!sameSource||!inside(parent.path,folder.path))continue;
            if(!parent.path.equals(folder.path)||j<index)return true;
        }
        return false;
    }
    static Result sum(Collection<Selection> selected,Map<String,FolderStats> snapshots){
        ArrayList<Selection> all=new ArrayList<>(selected);
        HashSet<String> covered=new HashSet<>();
        ArrayList<Selection> provisionalFolders=new ArrayList<>();
        boolean pending=false,unknown=false,provisional=false;
        long total=0;
        // Count exact folder contents first; deduplicate shared files by URI.
        for(int i=0;i<all.size();i++){
            Selection entry=all.get(i);
            if(!entry.folder)continue;
            if(coveredByAnotherFolder(entry,all,i))continue;
            FolderStats stats=snapshots.get(entry.key);
            if(stats==null){
                pending=true;
                provisionalFolders.add(entry);
                if(entry.provisionalBytes>=0)provisional=true;
                continue;
            }
            if(stats.unknown&&stats.files.isEmpty()&&entry.provisionalBytes>=0){
                // A storage permission/scan failure must not erase the real
                // MediaStore estimate already shown on the folder card.
                // The ≈ symbol makes it clear that this is not an exact scan.
                provisional=true;
                total=add(total,entry.provisionalBytes);
                continue;
            }
            unknown|=stats.unknown;
            for(Map.Entry<String,Long> file:stats.files.entrySet()){
                if(!covered.add(file.getKey()))continue;
                if(file.getValue()==null||file.getValue()<0)unknown=true;
                else total=add(total,file.getValue());
            }
        }
        // A provisional folder amount is a media-index estimate. Keep the UI
        // responsive while a full recursive scan computes its exact total.
        for(Selection entry:provisionalFolders){
            if(entry.provisionalBytes>=0)total=add(total,entry.provisionalBytes);
        }
        HashSet<String> countedFiles=new HashSet<>();
        for(Selection entry:all){
            if(entry.folder)continue;
            if(covered.contains(entry.uri))continue;
            if(!entry.uri.isEmpty()&&!countedFiles.add(entry.uri))continue;
            // A media file has a content://media URI while a recursive local
            // folder scan returns file:// URIs. Both represent the same shared
            // storage file. Relative paths prevent this cross-provider double
            // count; never equate unrelated SAF providers by path alone.
            boolean enclosed=false;
            for(Selection folder:selected){
                if(!folder.folder)continue;
                if(sameSharedStorage(folder.uri,entry.uri)&&inside(folder.path,entry.path)){
                    enclosed=true;break;
                }
            }
            if(enclosed)continue;
            if(entry.bytes<0)unknown=true;
            else total=add(total,entry.bytes);
        }
        return new Result(total,pending,unknown,provisional);
    }
}
