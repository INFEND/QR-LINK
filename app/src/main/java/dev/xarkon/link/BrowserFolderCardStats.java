package dev.xarkon.link;

import java.util.Map;

/** Constant-size summary for a folder card; no file URIs are retained. */
final class BrowserFolderCardStats {
    final int fileCount;
    final long bytes;
    final boolean complete,bytesKnown;

    private BrowserFolderCardStats(int fileCount,long bytes,boolean complete,boolean bytesKnown){
        this.fileCount=fileCount;
        this.bytes=bytes;
        this.complete=complete;
        this.bytesKnown=bytesKnown;
    }

    static BrowserFolderCardStats summarize(Map<String,Long> files,boolean complete){
        long total=0;
        boolean known=complete;
        for(Long value:files.values()){
            if(value==null||value<0||Long.MAX_VALUE-total<value){
                known=false;
            }else total+=value;
        }
        return new BrowserFolderCardStats(files.size(),total,complete,known);
    }
}
