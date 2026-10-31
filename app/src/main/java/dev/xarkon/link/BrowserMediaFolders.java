package dev.xarkon.link;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.function.Function;

/** Pure category-folder index: no unrelated/empty directories may enter media tabs. */
final class BrowserMediaFolders {
    private BrowserMediaFolders() {}

    static String normalize(String path) {
        if(path==null||path.trim().isEmpty())return "";
        StringBuilder clean=new StringBuilder();
        for(String segment:path.replace('\\','/').split("/")){
            if(segment.isEmpty()||segment.equals(".")||segment.equals(".."))continue;
            if(clean.length()>0)clean.append('/');
            clean.append(segment);
        }
        return clean.length()==0?"":clean.append('/').toString();
    }

    static String label(String path) {
        String normalized=normalize(path);
        if(normalized.isEmpty())return "Внутренняя память";
        int end=normalized.length()-1;
        int start=normalized.lastIndexOf('/',end-1)+1;
        return normalized.substring(start,end);
    }

    static <T> LinkedHashMap<String,ArrayList<T>> group(
            List<T> entries,Function<T,String> pathOf) {
        LinkedHashMap<String,ArrayList<T>> grouped=new LinkedHashMap<>();
        for(T item:entries){
            String path=normalize(pathOf.apply(item));
            grouped.computeIfAbsent(path,unused->new ArrayList<>()).add(item);
        }
        return grouped;
    }
}
