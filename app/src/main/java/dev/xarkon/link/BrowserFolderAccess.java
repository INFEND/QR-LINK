package dev.xarkon.link;

import java.io.IOException;
import java.nio.file.AccessDeniedException;
import java.util.Locale;

/** Explain Android's protected shared-storage folders without claiming to bypass OS access. */
final class BrowserFolderAccess {
    private BrowserFolderAccess(){}

    static boolean protectedAndroidPath(String relativePath){
        if(relativePath==null)return false;
        String path=relativePath.replace('\\','/').replaceAll("^/+","");
        String lower=path.toLowerCase(Locale.ROOT);
        return lower.equals("android/data")||lower.startsWith("android/data/")||
            lower.equals("android/obb")||lower.startsWith("android/obb/");
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
                lower.contains("недоступная папка")||lower.contains("каталог недоступен"))
                return true;
        }
        return false;
    }

    static String message(String relativePath,Throwable error){
        if(denied(error)&&protectedAndroidPath(relativePath))
            return "Android ограничивает доступ к Android/data и Android/obb даже при разрешении «Все файлы». Содержимое этой папки недоступно приложению.";
        if(denied(error))
            return "Нет доступа к папке. Проверьте разрешения на файлы или выберите доступную папку через системный проводник.";
        return "Не удалось раскрыть папку. Проверьте, что она существует и доступна.";
    }
}
