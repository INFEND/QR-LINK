package dev.xarkon.link;

import java.io.IOException;
import java.nio.file.AccessDeniedException;
import java.util.Locale;

/** Explain Android's protected shared-storage folders without claiming to bypass OS access. */
final class BrowserFolderAccess {
    private BrowserFolderAccess(){}

    static boolean protectedAndroidPath(String relativePath){
        if(relativePath==null)return false;
        // File-browser paths are relative to shared storage, but diagnostics
        // can provide /storage/emulated/0 or the file-manager /0 alias.
        // Resolve dot segments before classifying; never escape the root.
        String path=relativePath.replace('\\','/').replaceAll("^/+","");
        String lower=path.toLowerCase(Locale.ROOT);
        if(lower.startsWith("storage/emulated/0/"))
            path=path.substring("storage/emulated/0/".length());
        else if(lower.startsWith("0/"))path=path.substring(2);
        else if(lower.startsWith("sdcard/"))path=path.substring(7);
        else if(lower.startsWith("storage/")||lower.startsWith("mnt/"))
            return false;
        java.util.ArrayDeque<String> segments=new java.util.ArrayDeque<>();
        for(String part:path.split("/")){
            if(part.isEmpty()||part.equals("."))continue;
            if(part.equals("..")){
                if(segments.isEmpty())return false;
                segments.removeLast();
            }else segments.addLast(part);
        }
        if(segments.size()<2)return false;
        String first=segments.removeFirst(),second=segments.removeFirst();
        return first.equalsIgnoreCase("Android")&&
            (second.equalsIgnoreCase("data")||second.equalsIgnoreCase("obb"));
    }

    /** Android 11+ may silently filter a protected directory to an empty listing.
     * That is not proof that its real contents are empty. Other data folders are unaffected.
     */
    static void requireVisibleEvidence(String relativePath,int sdk,int observedEntries)
            throws AccessDeniedException{
        if(sdk>=30&&protectedAndroidPath(relativePath)&&observedEntries==0)
            throw new AccessDeniedException(relativePath);
    }

    static boolean denied(Throwable error){
        for(Throwable cause=error;cause!=null;cause=cause.getCause()){
            if(cause instanceof SecurityException||cause instanceof AccessDeniedException)return true;
            String text=cause.getMessage();
            if(text==null)continue;
            String lower=text.toLowerCase(Locale.ROOT);
            if(lower.contains("permission denied")||lower.contains("access denied")||
                lower.contains("eacces")||lower.contains("eperm")||
                lower.contains("operation not permitted")||
                lower.contains("доступ запрещ")||lower.contains("нет разрешения")||
                lower.contains("недоступная папка")||lower.contains("каталог недоступен")||
                lower.contains("нет доступа")||lower.contains("недоступный элемент")||
                lower.contains("недоступный каталог"))
                return true;
        }
        return false;
    }

    static String message(String relativePath,Throwable error){
        if(denied(error)&&protectedAndroidPath(relativePath))
            return "Нет доступа к системной папке Android. Android ограничивает просмотр её содержимого.";
        if(denied(error))
            return "Нет доступа к папке. Проверьте разрешения на файлы или выберите доступную папку через системный проводник.";
        return "Не удалось раскрыть папку. Проверьте, что она существует и доступна.";
    }
}
