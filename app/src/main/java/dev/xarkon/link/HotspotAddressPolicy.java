package dev.xarkon.link;

import java.util.Locale;

/** Never mistake the primary Wi-Fi station for the hosted access point. */
final class HotspotAddressPolicy {
    private HotspotAddressPolicy(){}
    static boolean isCandidateInterface(String interfaceName){
        if(interfaceName==null)return false;
        String name=interfaceName.toLowerCase(Locale.ROOT);
        return name.startsWith("ap")||name.startsWith("swlan")||
            name.startsWith("softap")||
            (name.startsWith("wlan")&&!name.equals("wlan0"));
    }
}
