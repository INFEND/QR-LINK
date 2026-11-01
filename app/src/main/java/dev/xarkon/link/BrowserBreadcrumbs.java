package dev.xarkon.link;

/** Format shared-storage paths without exposing Android's system filesystem root. */
public final class BrowserBreadcrumbs {
    private BrowserBreadcrumbs(){}
    public static String format(String path){
        String value=path==null?"":path.replace('\\','/');
        if(value.equals("/storage/emulated/0")||value.equals("/0"))value="";
        else if(value.startsWith("/storage/emulated/0/"))value=value.substring("/storage/emulated/0/".length());
        else if(value.startsWith("/0/"))value=value.substring(3);
        StringBuilder out=new StringBuilder("Устройство");
        for(String part:value.split("/")){
            if(part.isEmpty()||part.equals(".")||part.equals(".."))continue;
            out.append(" › ").append(part);
        }
        return out.toString();
    }
}
