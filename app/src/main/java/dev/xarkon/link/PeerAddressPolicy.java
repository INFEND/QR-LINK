package dev.xarkon.link;

import java.net.Inet4Address;
import java.net.InetAddress;

/** Only on-link private IPv4 endpoints may receive a scanned QR session key. */
public final class PeerAddressPolicy {
    private PeerAddressPolicy(){}
    public static boolean localIpv4(InetAddress address){
        return address instanceof Inet4Address &&
            !address.isAnyLocalAddress() && !address.isLoopbackAddress() &&
            !address.isMulticastAddress() &&
            (address.isSiteLocalAddress() || address.isLinkLocalAddress());
    }
}
