package dev.xarkon.link;

import java.util.Locale;

/** Strictly user-facing change lines for the in-app OTA screen, including older manifests. */
public final class ReleaseNotes {
    private ReleaseNotes(){}
    public static String visible(String source){
        if(source==null||source.isEmpty())return "";
        StringBuilder out=new StringBuilder();
        for(String raw:source.split("\\r?\\n")){
            String line=raw.trim();
            if(line.length()<5||line.length()>260)continue;
            if(!(line.startsWith("[+] ")||line.startsWith("[-] ")||line.startsWith("[=] ")))continue;
            String lower=line.toLowerCase(Locale.ROOT);
            if(lower.contains("jvm")||lower.contains("регрессион")||
                lower.contains("тестирован")||lower.contains("тесты")||
                lower.contains("аппаратн")||lower.contains("scoped storage")||
                lower.contains("github")||lower.contains("chatgpt")||
                lower.contains("лимит 30000")||lower.contains("не проверен"))continue;
            // Keep every validated change. Never silently truncate OTA notes.
            if(out.length()>0)out.append('\n');
            out.append(line);
        }
        return out.toString();
    }
}
