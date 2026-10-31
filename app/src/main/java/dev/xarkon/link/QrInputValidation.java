package dev.xarkon.link;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.nio.charset.StandardCharsets;
import java.util.Set;
import java.util.Locale;

/** Strict, DNS-free validation of untrusted QR pairing fields. Android-independent for JVM tests. */
public final class QrInputValidation {
    private QrInputValidation() {}

    private static final Set<String> QR_FIELDS=Set.of(
        "v","host","port","key","ap","ssid","pwd","sec","p2p","mac");

    /** Unknown fields are not silently ignored: they may alter future protocol semantics. */
    public static boolean allowedField(String field){return QR_FIELDS.contains(field);}

    /** Reject dummy, multicast and malformed P2P addresses before Android discovery. */
    public static boolean validP2pMac(String raw){
        if(raw==null||!raw.matches("(?i)[0-9a-f]{2}(:[0-9a-f]{2}){5}"))return false;
        if((Integer.parseInt(raw.substring(0,2),16)&1)!=0)return false;
        String compact=raw.replace(":","").toLowerCase(Locale.ROOT);
        return !"000000000000".equals(compact)&&!"020000000000".equals(compact);
    }

    /** Android Wi-Fi credentials must be bounded in UTF-8 bytes and contain no controls. */
    public static boolean validWifiCredentials(String ssid,String password){
        if(ssid==null||password==null)return false;
        int ssidBytes=ssid.getBytes(StandardCharsets.UTF_8).length;
        int passBytes=password.getBytes(StandardCharsets.UTF_8).length;
        if(ssidBytes<1||ssidBytes>32||passBytes<8||passBytes>63)return false;
        for(String part:new String[]{ssid,password}){
            for(int i=0;i<part.length();){
                int cp=part.codePointAt(i);
                if(Character.isISOControl(cp)||Character.getType(cp)==Character.FORMAT)return false;
                i+=Character.charCount(cp);
            }
        }
        return true;
    }

    public static boolean isLocalIpv4(String host) {
        if(host==null||host.isEmpty()||host.length()>15)return false;
        String[] parts=host.split("\\.",-1);
        if(parts.length!=4)return false;
        byte[] address=new byte[4];
        for(int i=0;i<4;i++){
            String part=parts[i];
            if(part.isEmpty()||part.length()>3||(part.length()>1&&part.charAt(0)=='0'))
                return false;
            int octet=0;
            for(int j=0;j<part.length();j++){
                char c=part.charAt(j);
                if(c<'0'||c>'9')return false;
                octet=octet*10+(c-'0');
            }
            if(octet>255)return false;
            address[i]=(byte)octet;
        }
        try{
            InetAddress ip=InetAddress.getByAddress(address);
            return ip.isSiteLocalAddress()||ip.isLinkLocalAddress();
        }catch(UnknownHostException impossible){return false;}
    }

    public static int requirePort(String raw,int expected) {
        if(raw==null||!raw.equals(Integer.toString(expected)))
            throw new IllegalArgumentException("Несовместимый или отсутствующий порт QR");
        return expected;
    }

    /** Version and transport flags must agree; never silently downgrade a QR invitation. */
    public static void requireMode(String version,String ap,String p2p) {
        boolean valid=("2".equals(version)&&ap==null&&p2p==null) ||
            ("3".equals(version)&&"1".equals(ap)&&p2p==null) ||
            ("4".equals(version)&&"1".equals(ap)&&"1".equals(p2p));
        if(!valid)throw new IllegalArgumentException("Несогласованные параметры подключения в QR");
    }

    public static int security(String raw) {
        // Android SoftApConfiguration currently defines security modes 0..4.
        if(raw==null||raw.length()!=1||raw.charAt(0)<'0'||raw.charAt(0)>'4')
            throw new IllegalArgumentException("Некорректный тип защиты точки Wi-Fi");
        return raw.charAt(0)-'0';
    }
}
