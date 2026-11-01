package dev.xarkon.link;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.LinkProperties;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.RouteInfo;
import android.net.wifi.WifiManager;
import android.os.Build;
import java.net.Inet4Address;
import java.net.InetAddress;

/**
 * A Wi-Fi interface is not necessarily a connected station:
 * P2P group owners, hotspot networks, and VPN-backed networks also exist.
 * Never decide to use a LAN QR merely because TRANSPORT_WIFI is present.
 */
public final class WifiState {
    private WifiState(){}
    public static boolean radioOn(Context c){
        WifiManager wm=(WifiManager)c.getApplicationContext().getSystemService(Context.WIFI_SERVICE);
        return wm!=null&&wm.isWifiEnabled();
    }
    /**
     * The actual IPv4 address of a Wi-Fi station attached to an access point.
     * A P2P interface, hotspot, VPN interface or mere enabled radio is NOT LAN.
     * A routed IPv4 gateway is required, but internet access is not.
     */
    public static String clientAddress(Context c){
        if(!radioOn(c))return "";
        ConnectivityManager cm=(ConnectivityManager)c.getSystemService(Context.CONNECTIVITY_SERVICE);
        if(cm!=null)try{
            for(Network network:cm.getAllNetworks()){
                NetworkCapabilities caps=cm.getNetworkCapabilities(network);
                if(caps==null||!caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)||
                   caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_WIFI_P2P))continue;
                LinkProperties links=cm.getLinkProperties(network);
                if(links==null)continue;
                String address="";
                for(android.net.LinkAddress la:links.getLinkAddresses()){
                    InetAddress addr=la.getAddress();
                    if(addr instanceof Inet4Address&&addr.isSiteLocalAddress()&&
                       !addr.isLoopbackAddress()&&!addr.isLinkLocalAddress()){
                        address=addr.getHostAddress();break;
                    }
                }
                if(address.isEmpty())continue;
                for(RouteInfo route:links.getRoutes()){
                    InetAddress gw=route.getGateway();
                    if(gw instanceof Inet4Address&&gw.isSiteLocalAddress()&&
                       !gw.isAnyLocalAddress()&&!gw.getHostAddress().equals(address))
                        return address;
                }
            }
        }catch(SecurityException ignored){}
        // OEMs sometimes omit Wi-Fi LinkProperties from getAllNetworks.
        // Only fall back to DHCP if Wi-Fi is actually associated with an AP.
        try{
            WifiManager wifi=(WifiManager)c.getApplicationContext()
                .getSystemService(Context.WIFI_SERVICE);
            if(wifi==null||wifi.getConnectionInfo()==null||
               wifi.getConnectionInfo().getSupplicantState()!=
                   android.net.wifi.SupplicantState.COMPLETED)return "";
            android.net.DhcpInfo dhcp=wifi.getDhcpInfo();
            if(dhcp==null||dhcp.ipAddress==0||dhcp.gateway==0||
               dhcp.ipAddress==dhcp.gateway)return "";
            String ip=dhcpIpv4(dhcp.ipAddress);
            String gateway=dhcpIpv4(dhcp.gateway);
            java.net.InetAddress host=java.net.InetAddress.getByName(ip);
            java.net.InetAddress router=java.net.InetAddress.getByName(gateway);
            if(host.isSiteLocalAddress()&&router.isSiteLocalAddress())return ip;
        }catch(Exception ignored){}
        return "";
    }
    private static String dhcpIpv4(int address){
        return (address&255)+"."+((address>>>8)&255)+"."+
            ((address>>>16)&255)+"."+((address>>>24)&255);
    }
    public static boolean clientConnected(Context c){
        return !clientAddress(c).isEmpty();
    }
    /** Android hotspot hosting is not a Wi-Fi client connection. */
    public static String hostedApAddress(Context c){
        if(clientConnected(c))return "";
        ConnectivityManager cm=(ConnectivityManager)c.getSystemService(Context.CONNECTIVITY_SERVICE);
        if(cm!=null&&Build.VERSION.SDK_INT>=35)try{
            for(Network n:cm.getAllNetworks()){
                NetworkCapabilities cap=cm.getNetworkCapabilities(n);
                if(cap==null||!cap.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)||
                    !cap.hasCapability(NetworkCapabilities.NET_CAPABILITY_LOCAL_NETWORK))continue;
                LinkProperties lp=cm.getLinkProperties(n);
                if(lp==null)continue;
                for(android.net.LinkAddress la:lp.getLinkAddresses()){
                    InetAddress addr=la.getAddress();
                    if(addr instanceof Inet4Address&&addr.isSiteLocalAddress())return addr.getHostAddress();
                }
            }
        }catch(Exception ignored){}
        // Many tethering devices leave AP active while STA Wi-Fi is disabled.
        if(!radioOn(c)){
            String ip=HotspotSupport.hotspotIp();
            if(!ip.isEmpty()&&!"127.0.0.1".equals(ip))return ip;
        }
        return "";
    }
    public static boolean localTransferReady(Context c){
        return radioOn(c)||!hostedApAddress(c).isEmpty();
    }
    public static String receiveHint(Context c){
        if(!hostedApAddress(c).isEmpty())
            return "Системная точка доступа включена. Приём доступен.";
        if(!radioOn(c))return "Wi-Fi выключен. Включите его в настройках телефона.";
        if(clientConnected(c))return "Подключение через общую сеть Wi-Fi.";
        return "Нет подключения к роутеру. Используем Wi-Fi Direct.";
    }
}
