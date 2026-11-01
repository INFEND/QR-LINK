package dev.xarkon.link;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/** Authenticates the receiver's UDP address before an HTTP request carries a pairing key. */
final class DiscoveryAuth {
    private static final String REQUEST="XARKON_DISCOVER_2|";
    private static final String RESPONSE="XARKON_LINK_2|";
    private static final String DOMAIN="QR-LINK-DISCOVERY-V2:";
    private DiscoveryAuth(){}

    static String newNonce(){
        byte[] random=new byte[16];
        new SecureRandom().nextBytes(random);
        return hex(random);
    }

    static String request(String nonce){
        if(!validNonce(nonce))throw new IllegalArgumentException("Неверный запрос поиска");
        return REQUEST+nonce;
    }

    /** Returns null for malformed, unauthenticated or legacy discovery requests. */
    static String reply(String request,String sessionKey,int port){
        if(request==null||!request.startsWith(REQUEST))return null;
        String nonce=request.substring(REQUEST.length());
        if(!validNonce(nonce)||!validKey(sessionKey)||port<1||port>65535)return null;
        return RESPONSE+nonce+"|"+signature(sessionKey,nonce)+"|"+port;
    }

    /** Never trust an IP from an unauthenticated UDP reply, even on a local network. */
    static boolean verifies(String reply,String nonce,String sessionKey,int port){
        if(reply==null||!validNonce(nonce)||!validKey(sessionKey)||port<1||port>65535)return false;
        String[] fields=reply.split("\\|",-1);
        if(fields.length!=4||!"XARKON_LINK_2".equals(fields[0])||
            !nonce.equals(fields[1])||!Integer.toString(port).equals(fields[3])||
            !fields[2].matches("[0-9a-f]{64}"))return false;
        byte[] expected=signature(sessionKey,nonce).getBytes(StandardCharsets.US_ASCII);
        byte[] supplied=fields[2].getBytes(StandardCharsets.US_ASCII);
        return MessageDigest.isEqual(expected,supplied);
    }

    private static boolean validNonce(String nonce){
        return nonce!=null&&nonce.matches("[0-9a-f]{32}");
    }
    private static boolean validKey(String key){
        return key!=null&&key.matches("[0-9a-f]{64}");
    }
    private static String signature(String key,String nonce){
        try{
            byte[] secret=new byte[32];
            for(int i=0;i<secret.length;i++)
                secret[i]=(byte)((Character.digit(key.charAt(i*2),16)<<4)|
                    Character.digit(key.charAt(i*2+1),16));
            Mac mac=Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(secret,"HmacSHA256"));
            return hex(mac.doFinal((DOMAIN+nonce).getBytes(StandardCharsets.US_ASCII)));
        }catch(Exception error){
            throw new IllegalStateException("Невозможно подтвердить адрес приёмника",error);
        }
    }
    private static String hex(byte[] bytes){
        char[] chars=new char[bytes.length*2];
        final char[] digits="0123456789abcdef".toCharArray();
        for(int i=0;i<bytes.length;i++){
            int value=bytes[i]&255;
            chars[i*2]=digits[value>>>4];chars[i*2+1]=digits[value&15];
        }
        return new String(chars);
    }
}
