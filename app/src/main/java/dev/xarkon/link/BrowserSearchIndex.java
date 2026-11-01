package dev.xarkon.link;

import java.util.ArrayList;
import java.util.function.Supplier;

/** Main-thread cache for the sorted, expanded browser tree, not search results. */
final class BrowserSearchIndex<T> {
    private ArrayList<T> rows;
    private int sort;
    private boolean includeClosedMedia;

    ArrayList<T> get(int requestedSort,boolean requestedClosedMedia,
                     Supplier<ArrayList<T>> builder){
        if(rows==null||sort!=requestedSort||includeClosedMedia!=requestedClosedMedia){
            ArrayList<T> computed=builder.get();
            if(computed==null)throw new IllegalStateException("Missing browser rows");
            rows=computed;
            sort=requestedSort;
            includeClosedMedia=requestedClosedMedia;
        }
        return rows;
    }

    void invalidate(){rows=null;}
}
