package dev.xarkon.link;

/** Literal folder-prefix matching for MediaStore (including SQL wildcard characters). */
final class BrowserMediaQuery {
    private BrowserMediaQuery(){}
    static String likeSelection(String column){
        return column+" LIKE ? ESCAPE '\\'";
    }
    static String likeArgument(String prefix){
        String path=BrowserMediaFolders.normalize(prefix);
        StringBuilder result=new StringBuilder(path.length()+8);
        for(int i=0;i<path.length();i++){
            char c=path.charAt(i);
            if(c=='%'||c=='_'||c=='\\')result.append('\\');
            result.append(c);
        }
        return result.append('%').toString();
    }
    static boolean matches(String path,String prefix){
        return BrowserMediaFolders.normalize(path)
            .startsWith(BrowserMediaFolders.normalize(prefix));
    }
}
