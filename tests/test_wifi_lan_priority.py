"""Regression: receiver chooses real LAN before P2P; QR refresh keeps LAN."""
from pathlib import Path
import unittest

JAVA=Path(__file__).resolve().parents[1]/"app/src/main/java/dev/xarkon/link"


class WifiLanPriorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service=(JAVA/"TransferService.java").read_text(encoding="utf-8")
        cls.main=(JAVA/"MainActivity.java").read_text(encoding="utf-8")
        cls.wifi=(JAVA/"WifiState.java").read_text(encoding="utf-8")

    def test_station_ipv4_is_not_merely_enabled_radio(self):
        self.assertIn("public static String clientAddress(Context c)",self.wifi)
        self.assertIn("caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_WIFI_P2P)",self.wifi)
        self.assertIn("caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN)",self.wifi)
        self.assertIn("gw.isSiteLocalAddress()",self.wifi)
        self.assertIn("android.net.wifi.SupplicantState.COMPLETED",self.wifi)
        self.assertIn("return !clientAddress(c).isEmpty();",self.wifi)

    def test_no_false_direct_status_before_group_ready(self):
        self.assertIn('return "Нет подключения к роутеру. Подготавливаем локальное соединение.";',self.wifi)
        self.assertNotIn('return "Нет подключения к роутеру. Используем Wi-Fi Direct.";',self.wifi)
        self.assertIn('if(clientConnected(c))return "Подключение через общую сеть Wi-Fi.";',self.wifi)

    def test_receiver_prioritizes_lan_before_creating_direct(self):
        body=self.service.split("private void establishNetworkRoute(){",1)[1].split(
            "private void startHotspotFallback(",1)[0]
        self.assertLess(body.index("WifiState.clientAddress(this)"),body.index("directWifi.available()"))
        self.assertLess(body.index('status="Общая сеть Wi-Fi · готов к приёму"'),
                        body.index("directWifi.available()"))
        self.assertIn("nextDirectRoute();",body)
        self.assertIn("directWifi.close();hotspot.stop();resetDirect();resetHotspot();",body)

    def test_watcher_migrates_active_direct_to_shared_lan(self):
        watcher=self.service.split("private final Runnable networkWatch=",1)[1].split(
            "private final ExecutorService work=",1)[0]
        self.assertIn("WifiState.clientConnected(TransferService.this)&&",watcher)
        self.assertIn("(directReady||directStarting||hotspotReady||hotspotStarting)",watcher)
        self.assertIn("establishNetworkRoute();",watcher)

    def test_delayed_direct_and_hotspot_callbacks_do_not_steal_lan(self):
        hosted=self.service.split("directWifi.host(new DirectWifi.HostListener(){",1)[1].split(
            "private void startHotspotFallback(",1)[0]
        self.assertIn("if(WifiState.clientConnected(TransferService.this))",hosted)
        self.assertIn("establishNetworkRoute();return;",hosted)
        fallback=self.service.split("private void startHotspotFallback(String reason){",1)[1].split(
            "private void resolveHotspotAddress(",1)[0]
        self.assertIn("if(!forceHotspot&&WifiState.clientConnected(this)){establishNetworkRoute();return;}",fallback)

    def test_refresh_rotates_key_but_not_route(self):
        self.assertIn('if(ROTATE.equals(action)||modeChange){engine.stop();isReceiving=false;receiveKey="";}',self.service)
        self.assertIn("establishNetworkRoute();",self.service)
        self.assertIn('outlineButton(qrPanel,"scan","ОБНОВИТЬ QR-КОД",()->{lastQr="";start(TransferService.ROTATE);});',
                      self.main)
        render=self.main.split("private void renderQr(){",1)[1].split("private Bitmap makeQr(",1)[0]
        self.assertIn("String lanAddress=WifiState.clientAddress(this);",render)
        self.assertIn("boolean direct=!onLan&&TransferService.directReady;",render)
        self.assertIn("String host=onLan?lanAddress:direct?TransferService.directHost:",render)
        self.assertIn("onLan?\"ОБЩАЯ СЕТЬ WI-FI\":",render)
        self.assertNotIn("externalAp?TransferService.systemApHost:Util.ip()",render)


if __name__=="__main__":unittest.main()
