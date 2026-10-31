package dev.xarkon.link;

import android.app.*;
import android.content.*;
import android.os.*;
import android.content.pm.ServiceInfo;
import android.net.wifi.WifiManager;
import org.json.*;
import java.security.SecureRandom;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

public final class TransferService extends Service implements TransferEngine.Events {
    public static final String RECEIVE="dev.xarkon.link.RECEIVE",STOP="dev.xarkon.link.STOP",SEND="dev.xarkon.link.SEND";
    public static final String CONNECT="dev.xarkon.link.CONNECT";
    public static final String CANCEL_SEND="dev.xarkon.link.CANCEL_SEND";
    public static final String DISCONNECT_PEER="dev.xarkon.link.DISCONNECT_PEER";
    public static final String BENCH="dev.xarkon.link.BENCH",FTP="dev.xarkon.link.FTP",ROTATE="dev.xarkon.link.ROTATE";
    public static volatile String status="Служба выключена",detail="",receiveKey="";
    public static volatile long progress=0,total=0;
    public static volatile double bytesPerSecond=0;
    public static volatile String activeFile="";
    public static volatile String transferDirection="";
    private long sampleAt=0,sampleBytes=0;
    private String sampledFile="";
    public static volatile boolean isReceiving=false,isBusy=false,isSending=false;
    private static final String CHANNEL="xarkon_transfer";
    private static final int NOTIFICATION=118;
    private final AtomicBoolean busy=new AtomicBoolean();
    private final PeerAttemptGuard peerAttempts=new PeerAttemptGuard();
    private final ExecutorService peerHealth=Executors.newSingleThreadExecutor();
    private volatile boolean autoReconnectLan;
    private volatile boolean destroyed;
    private boolean routeActive(int route){
        return !destroyed&&route==directRouteAttempt&&wantReceive&&isReceiving&&
            engine!=null&&engine.receiving()&&WifiState.localTransferReady(this);
    }
    private boolean peerHealthBusy,peerReconnectBusy;
    private long lastPeerHealthAt,lastPeerReconnectAt;
    private final Handler networkHandler=new Handler(Looper.getMainLooper());
    private boolean wantReceive;
    private boolean senderWifiLost;
    private boolean groupProbeRunning;
    // Invalidates delayed Wi-Fi Direct callbacks after radio loss or STOP.
    private int directRouteAttempt;
    private final Runnable networkWatch=new Runnable(){
        @Override public void run(){
            if(destroyed)return;
            try{
                // A verified idle peer is no longer reachable when the local radio disappears.
                // Do not keep showing a connected device while Wi-Fi is off.
                if(peerVerified&&!WifiState.localTransferReady(TransferService.this)){
                    peerAttempts.next();peerVerified=false;
                    peerState="Соединение потеряно · включите Wi-Fi";
                    status=peerState;refresh();
                }
                if(isSending&&!senderWifiLost&&!WifiState.localTransferReady(TransferService.this)){
                    senderWifiLost=true;
                    engine.cancelSending();
                    peerAttempts.next();peerVerified=false;
                    peerState="Соединение потеряно · передача приостановлена";
                    status=peerState;refresh();
                }
                if(wantReceive){
                    if(!WifiState.localTransferReady(TransferService.this)){
                        ++directRouteAttempt;
                        peerVerified=false;
                        if(isReceiving||directReady||hotspotReady){
                            engine.stop();directWifi.close();hotspot.stop();resetDirect();resetHotspot();
                            systemApHost="";receiveKey="";isReceiving=false;
                            status="Wi-Fi выключен · ожидание включения";refresh();
                        }
                    }else if(!isReceiving){
                        networkHandler.post(()->onStartCommand(
                            new Intent(TransferService.this,TransferService.class).setAction(RECEIVE),0,0));
                    }else if(directReady&&!groupProbeRunning){
                        groupProbeRunning=true;
                        final int probeRoute=directRouteAttempt;
                        directWifi.confirmHosting(directSsid,valid->{
                            if(!routeActive(probeRoute))return;
                            groupProbeRunning=false;
                            if(!valid&&directReady){
                                resetDirect();directWifi.close();
                                status="Соединение Wi-Fi Direct потеряно · восстанавливаем";refresh();
                                establishNetworkRoute();
                            }
                        });
                    }
                }
                monitorPeer();
            }finally{if(!destroyed)networkHandler.postDelayed(this,1700L);}
        }
    };
    private final ExecutorService work=Executors.newSingleThreadExecutor();
    private TransferEngine engine;
    private PowerManager.WakeLock wake;
    private long lastNotify;
    private HotspotSupport hotspot;
    private WifiPeerConnector wifiPeer;
    private DirectWifi directWifi;
    private WifiManager.WifiLock wifiLock;
    public static volatile boolean hotspotReady=false, hotspotStarting=false;
    public static volatile String hotspotSsid="", hotspotPassword="", hotspotHost="";
    public static volatile int hotspotSecurity=0;
    public static volatile String peerState="";
    public static volatile boolean peerVerified=false; // Set only after a successful /hello.
    public static volatile String systemApHost="";
    public static volatile boolean directReady=false,directStarting=false;
    public static volatile String directMac="",directSsid="",directPass="",directHost="";
    @Override public void onCreate(){super.onCreate();
        ((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).createNotificationChannel(
            new NotificationChannel(CHANNEL,"Передача файлов",NotificationManager.IMPORTANCE_LOW));
        engine=new TransferEngine(this,this);
        hotspot=new HotspotSupport(this);
        wifiPeer=new WifiPeerConnector(this);
        directWifi=new DirectWifi(this);
        android.content.SharedPreferences saved=getSharedPreferences("settings",0);
        wantReceive=saved.getBoolean("receive_desired",false);
        try{
            Pairing.Info previous=Pairing.parse(saved.getString("pair_qr",""));
            autoReconnectLan=!previous.hotspot&&
                previous.key.equals(saved.getString("key",""))&&
                !saved.getString("host","").isEmpty();
        }catch(Exception ignored){autoReconnectLan=false;}
        networkHandler.postDelayed(networkWatch,1200L);
    }
    private Notification notification(){
        Intent intent=new Intent(this,MainActivity.class);
        PendingIntent pi=PendingIntent.getActivity(this,0,intent,PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        Intent stopIntent=new Intent(this,TransferService.class).setAction(STOP);
        PendingIntent stopPi=PendingIntent.getService(this,1,stopIntent,PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        String notice=activeFile.isEmpty()?status:(activeFile+" · "+Util.readable(progress)+" / "+Util.readable(total));
        Notification.Builder b=new Notification.Builder(this,CHANNEL).setSmallIcon(android.R.drawable.stat_sys_upload)
            .setContentTitle("QR LINK · фоновая передача").setContentText(notice).setContentIntent(pi).setOngoing(isReceiving||isBusy||!peerState.isEmpty())
            .setOnlyAlertOnce(true).setCategory(Notification.CATEGORY_PROGRESS)
            .addAction(new Notification.Action.Builder(android.R.drawable.ic_menu_close_clear_cancel,"Остановить",stopPi).build());
        if(total>0)b.setProgress(100,(int)Math.min(100,progress*100/Math.max(1,total)),false);
        return b.build();
    }
    private void foreground(){
        if(android.os.Build.VERSION.SDK_INT>=29)startForeground(NOTIFICATION,notification(),ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE);
        else startForeground(NOTIFICATION,notification());
    }
    private void refresh(){if(destroyed)return;MainActivity.changed();
        if(Util.now()-lastNotify>750){lastNotify=Util.now();
            ((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).notify(NOTIFICATION,notification());}
    }
    private void lock(){if(wake==null){PowerManager pm=(PowerManager)getSystemService(POWER_SERVICE);
        wake=pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"XarkonLink:FileTransfer");wake.setReferenceCounted(false);}
        if(!wake.isHeld())wake.acquire();
        if(wifiLock==null){
            WifiManager wm=(WifiManager)getApplicationContext().getSystemService(WIFI_SERVICE);
            if(wm!=null){wifiLock=wm.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF,"QRLink:Transfer");wifiLock.setReferenceCounted(false);}
        }
        if(wifiLock!=null&&!wifiLock.isHeld())wifiLock.acquire();
    }
    private void unlock(){if(wake!=null&&wake.isHeld())wake.release();
        if(wifiLock!=null&&wifiLock.isHeld())wifiLock.release();}
    // An established QR pairing is not an active transfer. Release the CPU and
    // high-performance Wi-Fi locks when idle; SEND acquires them again.
    // Receiving keeps its locks while the server is listening in the background.
    private void unlockIfIdle(){if(!isReceiving&&!isBusy)unlock();}
    @Override public int onStartCommand(Intent in,int flags,int startId){
        if(destroyed||in==null)return START_NOT_STICKY;
        String action=in.getAction();
        if(DISCONNECT_PEER.equals(action)){
            engine.cancelSending();
            peerAttempts.next();peerVerified=false;peerState="";autoReconnectLan=false;
            getSharedPreferences("settings",0).edit().remove("host").remove("key")
                .remove("port").remove("peer_name").remove("pair_qr").commit();
            wifiPeer.stop();if(!wantReceive)directWifi.close();
            if(!wantReceive&&!isBusy){unlock();stopSelf();}else refresh();
            MainActivity.changed();return START_NOT_STICKY;
        }
        if(CANCEL_SEND.equals(action)){
            engine.cancelSending();
            status="Останавливаем передачу · соединение сохранено";refresh();
            return START_NOT_STICKY;
        }
        if(STOP.equals(action)){
            engine.cancelSending();
            ++directRouteAttempt;
            peerAttempts.next();peerVerified=false;autoReconnectLan=false;
            wantReceive=false;getSharedPreferences("settings",0).edit().putBoolean("receive_desired",false).apply();
            engine.stop();hotspot.stop();wifiPeer.stop();directWifi.close();resetHotspot();resetDirect();systemApHost="";isReceiving=false;receiveKey="";peerState="";activeFile="";transferDirection="";progress=0;total=0;status="Служба остановлена";
            unlock();stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();MainActivity.changed();return START_NOT_STICKY;
        }
        foreground();
        if(RECEIVE.equals(action)||ROTATE.equals(action)){
            try{
                wantReceive=true;getSharedPreferences("settings",0).edit().putBoolean("receive_desired",true).apply();
                if(!WifiState.localTransferReady(this)){
                    ++directRouteAttempt;
                    engine.stop();directWifi.close();hotspot.stop();resetDirect();resetHotspot();
                    systemApHost="";isReceiving=false;receiveKey="";
                    note("Wi-Fi выключен. После включения приём запустится автоматически.");
                    return START_NOT_STICKY;
                }
                if(ROTATE.equals(action)){engine.stop();isReceiving=false;receiveKey="";}
                if(!engine.receiving()){
                    byte[] secret=new byte[32];new SecureRandom().nextBytes(secret);
                    StringBuilder hex=new StringBuilder(64);for(byte b:secret)hex.append(String.format(Locale.US,"%02x",b&255));
                    receiveKey=hex.toString();engine.start(receiveKey);isReceiving=true;
                }
                lock();
                establishNetworkRoute();
            }catch(Exception e){note("Не удалось запустить приём: "+e.getMessage());}
        }else if(CONNECT.equals(action)){
            if(!WifiState.localTransferReady(this)){
                peerAttempts.next();peerVerified=false;
                peerState="Нет локального Wi-Fi · подключение не начато";
                note("Включите Wi-Fi для подключения по QR.");
                return START_NOT_STICKY;
            }
            String raw=in.getStringExtra("qr");
            final int attempt=peerAttempts.next();
            autoReconnectLan=false;
            peerVerified=false;peerState="Подключение · проверяем маршрут";refresh();
            wifiPeer.stop();if(!wantReceive)directWifi.close();
            try{
                Pairing.Info info=Pairing.parse(raw);
                // Invalidate the previous receiver before attempting ANY new QR, including LAN.
                getSharedPreferences("settings",0).edit().remove("host").remove("key")
                    .remove("port").remove("peer_name").putString("pair_qr",raw).commit();
                lock();
                if(!info.hotspot){
                    peerState="Подключаемся через общую сеть Wi-Fi";refresh();
                    verifyReceiver(info.host,info,false,raw,attempt);
                }else{
                    if(info.direct){
                        peerState="Ищем Wi-Fi Direct приёмник...";refresh();
                        directWifi.join(info.mac,new DirectWifi.JoinListener(){
                            @Override public void connected(String host){
                                if(peerAttempts.current(attempt))verifyReceiver(host,info,true,raw,attempt);
                            }
                            @Override public void failure(String reason){
                                if(!peerAttempts.current(attempt))return;
                                peerState="Wi-Fi Direct: "+reason+". Пробуем подключение по имени сети...";refresh();
                                fallbackWifi(info,raw,attempt);
                            }
                        });
                    }else fallbackWifi(info,raw,attempt);
                }
            }catch(Exception e){
                peerAttempts.next();peerVerified=false;
                // Invalid QR must not leave a previously paired receiver available.
                getSharedPreferences("settings",0).edit().remove("host").remove("key")
                    .remove("port").remove("peer_name").remove("pair_qr").commit();
                peerState="Ошибка QR: "+ErrorText.human(e);
                note(peerState);unlockIfIdle();
            }
        }else if(SEND.equals(action))runJob(()->{
            if(!WifiState.localTransferReady(this))throw new java.io.IOException(
                "Локальная Wi-Fi сеть недоступна.");
            android.content.SharedPreferences p=getSharedPreferences("settings",0);
            String host=p.getString("host","").trim();int port=p.getInt("port",Util.PORT);
            String pin=p.getString("key","");int lanes=p.getInt("lanes",4);
            List<FileCatalog.Item> list=FileCatalog.load(this);List<FileCatalog.Item>todo=new ArrayList<>();
            for(FileCatalog.Item it:list)if(!"Передан".equals(it.status))todo.add(it);
            if(todo.isEmpty()){note("Нет файлов для отправки");return;}
            if(host.isEmpty()||pin.isEmpty())throw new java.io.IOException(
                "Нет подключённого получателя. Отсканируйте QR заново.");
            try{engine.send(host,port,pin,todo,lanes);}
            catch(Exception failure){peerVerified=false;throw failure;}
        },true);
        else if(BENCH.equals(action))runJob(()->{
            if(!WifiState.localTransferReady(this))throw new java.io.IOException(
                "Локальная Wi-Fi сеть недоступна.");
            android.content.SharedPreferences p=getSharedPreferences("settings",0);
            String host=p.getString("host","");int port=p.getInt("port",Util.PORT);
            String pin=p.getString("key","");int lanes=p.getInt("lanes",4);
            note("Тест сети: 512 МиБ данных, "+lanes+" поток(а/ов)");
            double rate=TransferEngine.benchmark(host,port,pin,lanes);
            note(String.format(Locale.US,"Тест завершён: %.1f МиБ/с (%.0f Мбит/с)",rate/1048576.0,rate*8/1000000.0));
        });
        else if(FTP.equals(action))runJob(()->{
            String url=in.getStringExtra("ftp_url"),dir=in.getStringExtra("ftp_dir"),name=in.getStringExtra("ftp_name");
            if(url==null||name==null)return;
            try(FtpBridge ftp=new FtpBridge(this,url)){ftp.download(dir,name,this);}
        });
        return START_NOT_STICKY;
    }
    /** Direct is preferred even when both phones are connected to different routers.
     * An existing system hotspot takes priority. LocalOnlyHotspot is the fallback.
     */
    private void establishNetworkRoute(){
        if(!wantReceive||!isReceiving)return;
        String external=WifiState.hostedApAddress(this);
        if(!external.isEmpty()){
            // A system hotspot supersedes any pending Direct hosting callback.
            ++directRouteAttempt;
            directWifi.close();hotspot.stop();resetDirect();resetHotspot();
            systemApHost=external;status="Системная точка доступа · готов к приёму";refresh();return;
        }
        systemApHost="";
        if(directReady){
            status="Wi-Fi Direct · ожидание отправителя";refresh();return;
        }
        if(directStarting||hotspotStarting)return;
        if(directWifi.available()){
            directStarting=true;status="Создаём прямое соединение...";refresh();
            final int route=++directRouteAttempt;
            directWifi.host(new DirectWifi.HostListener(){
                @Override public void ready(String mac,String ssid,String pass,String host){
                    if(!routeActive(route))return;
                    if(host==null||!QrInputValidation.isLocalIpv4(host)||mac==null||
                        !mac.matches("(?i)[0-9a-f]{2}(:[0-9a-f]{2}){5}")){
                        resetDirect();directWifi.close();
                        startHotspotFallback("Wi-Fi Direct не предоставил корректный IP или MAC");return;
                    }
                    directReady=true;directStarting=false;directMac=mac;directSsid=ssid;
                    directPass=pass;directHost=host;
                    status="Wi-Fi Direct готов · покажите QR";refresh();
                }
                @Override public void failure(String reason){
                    if(!routeActive(route))return;
                    resetDirect();startHotspotFallback(reason);
                }
            });
        }else startHotspotFallback("Wi-Fi Direct недоступен");
    }
    private void startHotspotFallback(String reason){
        if(!wantReceive||!isReceiving)return;
        if(hotspotReady||hotspotStarting)return;
        hotspotStarting=true;
        final int route=++directRouteAttempt;
        status="Создаём локальную точку доступа...";detail=reason;refresh();
        hotspot.start(new HotspotSupport.Listener(){
            @Override public void ready(String ssid,String pass,int security,String host){
                if(!routeActive(route))return;
                if(ssid==null||ssid.trim().isEmpty()||pass==null||pass.isEmpty()){
                    hotspot.stop();resetHotspot();
                    status="Android не предоставил параметры точки доступа";refresh();return;
                }
                hotspotStarting=false;hotspotReady=true;
                hotspotSsid=ssid;hotspotPassword=pass;hotspotSecurity=security;
                hotspotHost=QrInputValidation.isLocalIpv4(host)?host:"";
                status=hotspotHost.isEmpty()?"Определяем адрес точки доступа...":
                    "Локальная точка доступа готова";
                refresh();
                if(hotspotHost.isEmpty())networkHandler.postDelayed(()->resolveHotspotAddress(0,route),250);
            }
            @Override public void failure(String why){
                if(!routeActive(route))return;
                resetHotspot();
                if(WifiState.clientConnected(TransferService.this)){
                    status="Приём через общую сеть Wi-Fi";detail=why;
                }else{
                    status="Не удалось создать соединение";
                    detail="Wi-Fi Direct и локальная точка недоступны: "+why;
                }
                refresh();
            }
        });
    }
    private void resolveHotspotAddress(int attempt,int route){
        if(!routeActive(route)||!hotspotReady)return;
        String ip=HotspotSupport.hotspotIp();
        if(QrInputValidation.isLocalIpv4(ip)){
            hotspotHost=ip;status="Локальная точка доступа готова";refresh();return;
        }
        if(attempt<24)networkHandler.postDelayed(()->resolveHotspotAddress(attempt+1,route),250);
        else{
            hotspot.stop();resetHotspot();
            status="Не удалось определить адрес точки доступа";
            detail="Android не сообщил IP. Перезапустите приём.";refresh();
        }
    }
    private void fallbackWifi(Pairing.Info info,String raw,int attempt){
        if(destroyed||!peerAttempts.current(attempt))return;
        peerState="Подключение к сети приёмника. Может потребоваться подтверждение Android";refresh();
        wifiPeer.connect(info,new WifiPeerConnector.Listener(){
            @Override public void connected(String host){
                if(peerAttempts.current(attempt))verifyReceiver(host,info,false,raw,attempt);
            }
            @Override public void failure(String reason){
                if(!peerAttempts.current(attempt))return;
                peerVerified=false;peerState="Не удалось подключиться: "+ErrorText.human(reason);
                note(peerState);unlockIfIdle();
            }
        });
    }
    private void verifyReceiver(String host,Pairing.Info info,boolean p2pPath,String raw,int attempt){
        if(destroyed||!peerAttempts.current(attempt))return;
        peerState="Проверяем защищённый сеанс QR LINK...";refresh();
        try{work.execute(()->{
            try{
                org.json.JSONObject hello=new org.json.JSONObject(Util.http(host,info.port,info.key,"/hello","GET",null));
                if(!PeerIdentity.compatible(hello.optString("app"),hello.optInt("version",-1)))throw new Exception("Несовместимый протокол приёмника");
                if(destroyed||!peerAttempts.current(attempt))return;
                if(!WifiState.localTransferReady(TransferService.this))
                    throw new java.io.IOException("Локальная сеть отключилась во время подключения");
                getSharedPreferences("settings",0).edit().putString("host",host).putInt("port",info.port)
                    .putString("key",info.key).putString("pair_qr",raw)
                    .putString("peer_name",PeerIdentity.displayName(hello.optString("deviceName","Получатель"))).apply();
                autoReconnectLan=!info.hotspot;
                peerVerified=true;peerState="Подключено по QR · готово к отправке";status=peerState;
                unlockIfIdle();refresh();
            }catch(Exception e){
                if(destroyed||!peerAttempts.current(attempt))return;
                peerVerified=false;
                if(info.direct&&p2pPath){
                    peerState="Wi-Fi Direct подключён, но приёмник не отвечает. Пробуем резервный маршрут";refresh();
                    fallbackWifi(info,raw,attempt);
                }else{
                    peerState="Ошибка проверки приёмника: "+ErrorText.human(e);
                    note(peerState);unlockIfIdle();
                }
            }
        });}catch(RejectedExecutionException rejected){
            if(!destroyed&&peerAttempts.current(attempt)){
                peerVerified=false;peerState="Не удалось запустить проверку подключения";
                note(peerState);unlockIfIdle();
            }
        }
    }
    /** Check a verified peer after route changes without blocking transfers or the UI. */
    private void monitorPeer(){
        if(destroyed||isSending||isBusy)return;
        final long now=Util.now();
        final android.content.SharedPreferences saved=getSharedPreferences("settings",0);
        if(peerVerified){
            if(peerHealthBusy||now-lastPeerHealthAt<12000L)return;
            final String host=saved.getString("host",""),key=saved.getString("key","");
            final int port=saved.getInt("port",Util.PORT);
            if(host.isEmpty()||key.isEmpty())return;
            final int attempt=peerAttempts.snapshot();
            peerHealthBusy=true;lastPeerHealthAt=now;
            peerHealth.execute(()->{
                boolean reachable=false;
                try{
                    JSONObject hello=new JSONObject(Util.http(host,port,key,"/hello","GET",null));
                    reachable=PeerIdentity.compatible(hello.optString("app"),hello.optInt("version",-1));
                }catch(Exception ignored){}
                final boolean ok=reachable;
                networkHandler.post(()->{
                    peerHealthBusy=false;
                    if(destroyed||!peerAttempts.current(attempt)||!peerVerified||isSending||isBusy)return;
                    if(!host.equals(saved.getString("host",""))||
                        !key.equals(saved.getString("key","")))return;
                    if(!ok){
                        peerAttempts.next();peerVerified=false;
                        peerState="Получатель недоступен · ожидаем восстановления соединения";
                        status=peerState;refresh();
                    }
                });
            });
            return;
        }
        // Only LAN invitations can be retried silently; Direct/hotspot may need
        // an explicit Android network-connection approval.
        if(!autoReconnectLan||peerReconnectBusy||now-lastPeerReconnectAt<10000L||
            !WifiState.clientConnected(this))return;
        final Pairing.Info info;
        try{
            info=Pairing.parse(saved.getString("pair_qr",""));
            if(info.hotspot||!info.key.equals(saved.getString("key","")))return;
        }catch(Exception ignored){autoReconnectLan=false;return;}
        peerReconnectBusy=true;lastPeerReconnectAt=now;
        final String pairedQr=saved.getString("pair_qr","");
        final int attempt=peerAttempts.next();
        peerHealth.execute(()->{
            boolean reachable=false;String name="";
            try{
                JSONObject hello=new JSONObject(Util.http(info.host,info.port,info.key,"/hello","GET",null));
                reachable=PeerIdentity.compatible(hello.optString("app"),hello.optInt("version",-1));
                if(reachable)name=PeerIdentity.displayName(hello.optString("deviceName","Получатель"));
            }catch(Exception ignored){}
            final boolean ok=reachable,validRoute=reachable;
            final String peerName=name;
            networkHandler.post(()->{
                peerReconnectBusy=false;
                if(destroyed||!peerAttempts.current(attempt)||!autoReconnectLan||isSending||isBusy||
                    !WifiState.clientConnected(this))return;
                if(!pairedQr.equals(saved.getString("pair_qr",""))||
                    !info.key.equals(saved.getString("key","")))return;
                if(ok&&validRoute){
                    saved.edit().putString("host",info.host).putInt("port",info.port)
                        .putString("peer_name",peerName).apply();
                    peerVerified=true;peerState="Соединение восстановлено · готово к отправке";
                    status=peerState;refresh();
                }else{
                    peerState="Ожидаем восстановления соединения с получателем";
                    status=peerState;refresh();
                }
            });
        });
    }
    private interface Work{void run()throws Exception;}
    private void runJob(Work job){runJob(job,false);}
    private void runJob(Work job,boolean sending){
        if(!busy.compareAndSet(false,true)){note("Другая операция ещё выполняется");return;}
        // Arm cancellation before queueing work: STOP during preparation must win.
        if(sending)engine.prepareSending();
        isBusy=true;isSending=sending;senderWifiLost=false;
        status="Подготовка...";lock();refresh();
        try{work.submit(()->{
            try{job.run();}catch(Exception e){note("Ошибка: "+ErrorText.human(e));}
            finally{isSending=false;isBusy=false;busy.set(false);
                // Keep last transfer figures visible after completion.
                if(transferDirection.isEmpty()){progress=0;total=0;bytesPerSecond=0;activeFile="";}
                status=isReceiving&&engine.receiving()&&WifiState.localTransferReady(this)?
                    (directReady&&QrInputValidation.isLocalIpv4(directHost)?
                        "Wi-Fi Direct готов":"Приём включён · "+Util.ip()+":"+Util.PORT):
                    isReceiving?"Ожидание восстановления сети":
                    (!peerState.isEmpty()?peerState:"Готов к работе");
                unlockIfIdle();refresh();}
        });}catch(RejectedExecutionException rejected){
            isSending=false;isBusy=false;busy.set(false);
            status="Не удалось запустить операцию";unlockIfIdle();refresh();
        }
    }
    @Override public void note(String message){
        if(destroyed)return;
        message=ErrorText.human(message);
        detail=message;status=message;
        android.content.SharedPreferences prefs=getSharedPreferences("history",0);
        String old=prefs.getString("log","");
        String next=new java.text.SimpleDateFormat("dd.MM HH:mm:ss",Locale.getDefault()).format(new Date())+"  "+message+"\n"+old;
        if(next.length()>20000)next=next.substring(0,20000);
        prefs.edit().putString("log",next).apply();refresh();
    }
    @Override public synchronized void progress(String label,long received,long max,double speed){
        if(destroyed)return;
        status=label;
        String file=TransferLabel.file(label);
        String direction=TransferLabel.direction(label);
        if(!file.equals(sampledFile)||received<sampleBytes){
            sampledFile=file;sampleAt=Util.now();sampleBytes=received;
            bytesPerSecond=0;
        }
        long now=Util.now();
        // Both devices use the same moving-window payload metric. The old sender
        // used average-from-start while the receiver used an instant estimate.
        if(now-sampleAt>=300){
            long delta=Math.max(0L,received-sampleBytes);
            double instant=delta*1000d/Math.max(1L,now-sampleAt);
            bytesPerSecond=bytesPerSecond<=0?instant:
                (bytesPerSecond*.72d+instant*.28d);
            sampleAt=now;sampleBytes=received;
        }
        transferDirection=direction;activeFile=file;progress=received;total=max;refresh();
    }
    @Override public void onTimeout(int startId,int foregroundServiceType){
        note("Достигнуто системное ограничение фоновой службы. Продолжите позднее.");
        stopSelf();
    }
    private void resetDirect(){groupProbeRunning=false;directReady=false;directStarting=false;directMac="";directSsid="";
        directPass="";directHost="";MainActivity.changed();}
    private void resetHotspot(){hotspotReady=false;hotspotStarting=false;hotspotSsid="";hotspotPassword="";hotspotHost="";hotspotSecurity=0;MainActivity.changed();}
    @Override public void onDestroy(){destroyed=true;peerAttempts.next();autoReconnectLan=false;wantReceive=false;
        ++directRouteAttempt;networkHandler.removeCallbacksAndMessages(null);engine.shutdown();hotspot.stop();wifiPeer.stop();directWifi.destroy();resetHotspot();resetDirect();systemApHost="";work.shutdownNow();peerHealth.shutdownNow();unlock();
        peerVerified=false;peerState="";isReceiving=false;isBusy=false;isSending=false;receiveKey="";activeFile="";transferDirection="";progress=0;total=0;status="Служба выключена";MainActivity.changed();super.onDestroy();}
    @Override public IBinder onBind(Intent i){return null;}
}
