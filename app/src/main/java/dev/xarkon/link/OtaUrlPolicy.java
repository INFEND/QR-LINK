package dev.xarkon.link;

import java.net.URL;

/** Two explicitly pinned GitHub release slugs for the same renamed repository. */
public final class OtaUrlPolicy {
    public static final String LEGACY_MANIFEST=
        "https://github.com/ANTIFERMENT/QR-LINK/releases/latest/download/update.json";
    public static final String CANONICAL_MANIFEST=
        "https://github.com/INFEND/QR-LINK/releases/latest/download/update.json";
    private OtaUrlPolicy(){}

    /** Never accept arbitrary GitHub repositories or mismatched version tags. */
    public static boolean trustedApk(String raw,String version){
        if(raw==null||version==null||!version.matches("[A-Za-z0-9._-]{1,40}"))return false;
        try{
            URL u=new URL(raw);
            if(!"https".equalsIgnoreCase(u.getProtocol())||
                !"github.com".equalsIgnoreCase(u.getHost())||
                u.getPort()!=-1||u.getUserInfo()!=null||
                u.getQuery()!=null||u.getRef()!=null)return false;
            String suffix="/releases/download/v"+version+"/QR-LINK.apk";
            String path=u.getPath();
            return path.equals("/ANTIFERMENT/QR-LINK"+suffix)||
                path.equals("/INFEND/QR-LINK"+suffix);
        }catch(Exception invalid){return false;}
    }
}
