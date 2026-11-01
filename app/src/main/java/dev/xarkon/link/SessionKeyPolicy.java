package dev.xarkon.link;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/** Validate invitation secrets and compare without a byte-by-byte early exit. */
public final class SessionKeyPolicy {
    private SessionKeyPolicy(){}
    public static boolean valid(String key){
        if(key==null||key.length()!=64)return false;
        for(int i=0;i<64;i++){
            char c=key.charAt(i);
            if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;
        }
        return true;
    }
    public static boolean matches(String expected,String provided){
        if(!valid(expected)||!valid(provided))return false;
        return MessageDigest.isEqual(expected.getBytes(StandardCharsets.US_ASCII),
                                     provided.getBytes(StandardCharsets.US_ASCII));
    }
}
