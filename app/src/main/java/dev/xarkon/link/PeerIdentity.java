package dev.xarkon.link;

/** Validated /hello identity and bounded, non-spoofing peer labels. JVM-testable. */
public final class PeerIdentity {
    public static final int PROTOCOL_VERSION=1;
    private static final int MAX_CODEPOINTS=48;
    private PeerIdentity(){}

    public static boolean compatible(String app,int version){
        return "XARKON LINK".equals(app)&&version==PROTOCOL_VERSION;
    }

    /** Drop control and Unicode format/bidi characters; cap UI and persisted names. */
    public static String displayName(String raw){
        if(raw==null)return "Устройство";
        StringBuilder clean=new StringBuilder();
        int count=0;
        for(int i=0;i<raw.length()&&count<MAX_CODEPOINTS;){
            int cp=raw.codePointAt(i);
            i+=Character.charCount(cp);
            int type=Character.getType(cp);
            if(Character.isISOControl(cp)||type==Character.FORMAT||
                type==Character.LINE_SEPARATOR||type==Character.PARAGRAPH_SEPARATOR)continue;
            if(Character.isWhitespace(cp)){
                if(clean.length()>0&&clean.charAt(clean.length()-1)!=' ')clean.append(' ');
            }else{
                clean.appendCodePoint(cp);
                count++;
            }
        }
        String value=clean.toString().trim();
        return value.isEmpty()?"Устройство":value;
    }
}
