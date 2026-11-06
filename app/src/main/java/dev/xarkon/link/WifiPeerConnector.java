package dev.xarkon.link;

import android.content.*;
import android.net.*;
import android.net.wifi.*;
import java.net.*;
import java.nio.charset.StandardCharsets;

/** WifiNetworkSpecifier requires a one-time Android connection approval. */
public final class WifiPeerConnector {
    public interface Listener {void connected(String host);void failure(String reason);}
    private final ConnectivityManager manager;
    private ConnectivityManager.NetworkCallback callback;
    private long generation;
    private synchronized boolean current(long token,ConnectivityManager.NetworkCallback owner){
        return generation==token&&callback==owner;
    }
    public WifiPeerConnector(Context c){manager=(ConnectivityManager)c.getSystemService(Context.CONNECTIVITY_SERVICE);}
    public synchronized void stop(){
        generation++; // Invalidate callbacks and background discovery from the previous attempt.
        if(callback!=null){try{manager.unregisterNetworkCallback(callback);}catch(Exception ignored){}callback=null;}
        try{manager.bindProcessToNetwork(null);}catch(Exception ignored){}
    }
    public synchronized void connect(Pairing.Info info,Listener listener){
        stop();
        final long attempt=++generation;
        try{
            WifiNetworkSpecifier.Builder spec=new WifiNetworkSpecifier.Builder().setSsid(info.ssid);
            // Android may choose WPA3; use the same mode specified by the receiver.
            if(info.security==SoftApConfiguration.SECURITY_TYPE_WPA3_SAE)spec.setWpa3Passphrase(info.password);
            else spec.setWpa2Passphrase(info.password);
            NetworkRequest request=new NetworkRequest.Builder()
                .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                .removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                .setNetworkSpecifier(spec.build()).build();
            final boolean[] delivered={false};
            final boolean[] discovering={false};
            callback=new ConnectivityManager.NetworkCallback(){
                private final java.util.concurrent.atomic.AtomicBoolean failed=
                    new java.util.concurrent.atomic.AtomicBoolean(false);
                private volatile boolean bound;
                private volatile LinkProperties latestProperties;
                private volatile Network propertiesNetwork;
                private volatile Network boundNetwork;
                private final java.util.concurrent.atomic.AtomicBoolean ipDeadlineScheduled=
                    new java.util.concurrent.atomic.AtomicBoolean(false);
                private boolean active(){return current(attempt,this);}
                private void fail(String reason){
                    if(!active()||!failed.compareAndSet(false,true))return;
                    WifiPeerConnector.this.stop();
                    listener.failure(reason);
                }
                @Override public void onAvailable(Network n){
                    synchronized(WifiPeerConnector.this){
                        if(!active()||failed.get())return;
                        if(!manager.bindProcessToNetwork(n)){
                            fail("Android не разрешил использовать выбранную сеть Wi-Fi");
                            return;
                        }
                        boundNetwork=n;
                        bound=true;
                    }
                    LinkProperties properties=n.equals(propertiesNetwork)?latestProperties:null;
                    deliver(n,properties!=null?properties:manager.getLinkProperties(n));
                    // onAvailable can precede DHCP; Android's request timeout no longer
                    // guarantees onUnavailable after a network has been delivered.
                    if(ipDeadlineScheduled.compareAndSet(false,true)){
                        new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(()->{
                            if(!active()||failed.get())return;
                            synchronized(delivered){if(delivered[0])return;}
                            fail("Wi-Fi подключён, но не получил IPv4-адрес. Повторите подключение.");
                        },12000L);
                    }
                }
                @Override public void onLinkPropertiesChanged(Network n,LinkProperties lp){
                    if(!active())return;
                    latestProperties=lp;propertiesNetwork=n;
                    // Ignore properties from a superseded network while Android switches routes.
                    if(bound&&n.equals(boundNetwork))deliver(n,lp);
                }
                private void deliver(Network n,LinkProperties lp){
                    if(!active()||failed.get()||!bound||lp==null)return;
                    synchronized(delivered){if(delivered[0])return;}
                    boolean hasIpv4=false;
                    for(LinkAddress local:lp.getLinkAddresses()){
                        if(local.getAddress() instanceof Inet4Address){hasIpv4=true;break;}
                    }
                    if(!hasIpv4)return;
                    synchronized(discovering){if(discovering[0])return;discovering[0]=true;}
                    final LinkProperties properties=lp;
                    // DHCP gateways are not necessarily QR LINK receivers. On some
                    // LocalOnlyHotspot/Direct implementations the QR IP is stale or
                    // DHCP reports a different gateway. Verify /hello before
                    // declaring a peer, then use authenticated UDP discovery.
                    new Thread(()->{
                        String candidate=info.host==null?"":info.host;
                        if(candidate.isEmpty())candidate=resolveApAddress(properties);
                        String confirmed=verifyReceiverOnNetwork(n,candidate,info)?candidate:"";
                        if(confirmed.isEmpty()&&active()&&!failed.get()){
                            String discovered=discoverPeer(n,properties,info.key);
                            if(verifyReceiverOnNetwork(n,discovered,info))confirmed=discovered;
                        }
                        if(!active()||failed.get())return;
                        if(confirmed.isEmpty()){
                            fail("Сеть подключена, но приёмник QR LINK не отвечает. Повторите подключение.");
                            return;
                        }
                        synchronized(delivered){if(delivered[0])return;delivered[0]=true;}
                        listener.connected(confirmed);
                    },"qr-link-verify-peer").start();
                }
                @Override public void onUnavailable(){
                    fail("Android не подключился к точке доступа. Подтвердите запрос Wi-Fi и повторите сканирование.");
                }
                @Override public void onLost(Network n){
                    if(boundNetwork==null||n.equals(boundNetwork))
                        fail("Соединение с точкой доступа потеряно");
                }
            };
            manager.requestNetwork(request,callback,25000);
        }catch(Exception e){stop();listener.failure("Подключение Wi-Fi: "+ErrorText.human(e));}
    }
    /** Probe only on Android's requested Wi-Fi network, never via default mobile/VPN.
     * The /hello response must identify a compatible QR LINK receiver; a
     * successful TCP handshake with a random local gateway is not enough.
     */
    private static boolean verifyReceiverOnNetwork(Network network,String host,Pairing.Info info){
        if(host==null||host.isEmpty()||!QrInputValidation.isLocalIpv4(host))return false;
        HttpURLConnection connection=null;
        try{
            URL url=new URL("http",host,info.port,"/hello");
            connection=(HttpURLConnection)network.openConnection(url);
            connection.setConnectTimeout(2000);
            connection.setReadTimeout(2000);
            connection.setInstanceFollowRedirects(false);
            connection.setRequestProperty("X-Xarkon-Key",info.key);
            if(connection.getResponseCode()!=200)return false;
            try(java.io.InputStream stream=connection.getInputStream()){
                org.json.JSONObject reply=new org.json.JSONObject(Util.readText(stream,4096));
                return PeerIdentity.compatible(reply.optString("app"),reply.optInt("version",-1));
            }
        }catch(Exception ignored){return false;}
        finally{if(connection!=null)connection.disconnect();}
    }
    /** Uses the existing authenticated receiver's UDP discovery endpoint when DHCP omits its IP. */
    private static String discoverPeer(Network network,LinkProperties links,String key){
        try(DatagramSocket socket=new DatagramSocket(null)){
            socket.setReuseAddress(true);
            socket.bind(new InetSocketAddress(0));
            network.bindSocket(socket);
            socket.setBroadcast(true);socket.setSoTimeout(2500);
            String nonce=DiscoveryAuth.newNonce();
            byte[] data=DiscoveryAuth.request(nonce).getBytes(StandardCharsets.UTF_8);
            for(LinkAddress la:links.getLinkAddresses()){
                if(!(la.getAddress() instanceof Inet4Address))continue;
                byte[] ip=la.getAddress().getAddress();int prefix=la.getPrefixLength();
                if(prefix<0||prefix>32)continue;
                byte[] broadcast=new byte[4];
                for(int b=0;b<4;b++){
                    int remaining=Math.max(0,Math.min(8,prefix-b*8));
                    int mask=remaining==0?0:((255 << (8-remaining))&255);
                    broadcast[b]=(byte)((ip[b]&mask)|(~mask&255));
                }
                socket.send(new DatagramPacket(data,data.length,InetAddress.getByAddress(broadcast),Util.DISCOVERY_PORT));
            }
            // Ignore unrelated UDP packets rather than failing discovery on the first one.
            long deadline=android.os.SystemClock.elapsedRealtime()+2500L;
            while(android.os.SystemClock.elapsedRealtime()<deadline){
                long left=deadline-android.os.SystemClock.elapsedRealtime();
                socket.setSoTimeout((int)Math.max(1L,left));
                byte[] response=new byte[512];
                DatagramPacket packet=new DatagramPacket(response,response.length);
                try{socket.receive(packet);}
                catch(SocketTimeoutException timeout){break;}
                String answer=new String(packet.getData(),packet.getOffset(),packet.getLength(),StandardCharsets.UTF_8);
                if(DiscoveryAuth.verifies(answer,nonce,key,Util.PORT)&&
                   localAddress(packet.getAddress()))return packet.getAddress().getHostAddress();
            }
        }catch(Exception ignored){}
        return "";
    }
    /** Never send a session key to a public gateway or a spoofed public discovery IP. */
    private static boolean localAddress(InetAddress address){
        return PeerAddressPolicy.localIpv4(address);
    }
    private static String resolveApAddress(LinkProperties links){
        if(links==null)return "";
        if(android.os.Build.VERSION.SDK_INT>=30&&
            localAddress(links.getDhcpServerAddress()))
            return links.getDhcpServerAddress().getHostAddress();
        for(RouteInfo r:links.getRoutes()){
            InetAddress gateway=r.getGateway();
            if(localAddress(gateway))return gateway.getHostAddress();
        }
        // When AP does not advertise a gateway, no safe address can be deduced.
        return "";
    }
}
