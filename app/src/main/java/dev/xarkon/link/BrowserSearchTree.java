package dev.xarkon.link;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.function.Function;
import java.util.function.ToIntFunction;

/** Preserve visible ancestors when a search matches a child in an expanded tree. */
final class BrowserSearchTree {
    private BrowserSearchTree(){}

    static <T> List<T> filter(List<T> rows,ToIntFunction<T> depth,
                              Function<T,String> name,String query){
        if(query==null||query.trim().isEmpty())return new ArrayList<>(rows);
        String needle=query.trim().toLowerCase(Locale.ROOT);
        boolean[] keep=new boolean[rows.size()];
        ArrayList<Integer> ancestors=new ArrayList<>(20);
        ArrayList<Boolean> ancestorMatches=new ArrayList<>(20);
        for(int i=0;i<rows.size();i++){
            T row=rows.get(i);
            int level=Math.max(0,Math.min(depth.applyAsInt(row),ancestors.size()));
            while(ancestors.size()>level){
                ancestors.remove(ancestors.size()-1);
                ancestorMatches.remove(ancestorMatches.size()-1);
            }
            String title=name.apply(row);
            boolean matched=title!=null&&title.toLowerCase(Locale.ROOT).contains(needle);
            boolean insideMatchingFolder=!ancestorMatches.isEmpty()&&
                ancestorMatches.get(ancestorMatches.size()-1);
            if(matched||insideMatchingFolder){
                keep[i]=true;
                // Every ancestor becomes marked at most once across the whole
                // result. If an ancestor is already marked, its parents are too.
                // This avoids O(matches * nesting depth) on huge media trees.
                for(int j=ancestors.size()-1;j>=0;j--){
                    int parent=ancestors.get(j);
                    if(keep[parent])break;
                    keep[parent]=true;
                }
            }
            // A matching expanded folder should expose its files too, rather
            // than showing an apparently empty folder while search is active.
            ancestors.add(i);
            ancestorMatches.add(matched||insideMatchingFolder);
        }
        ArrayList<T> result=new ArrayList<>();
        for(int i=0;i<rows.size();i++)if(keep[i])result.add(rows.get(i));
        return result;
    }
}
