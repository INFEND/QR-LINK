"""Offline receiver route regressions: reject invalid AP/P2P QR credentials."""
from pathlib import Path
import unittest

JAVA=Path(__file__).resolve().parents[1]/"app/src/main/java/dev/xarkon/link"


class OfflineRouteFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service=(JAVA/"TransferService.java").read_text(encoding="utf-8")
        cls.direct=(JAVA/"DirectWifi.java").read_text(encoding="utf-8")
        cls.main=(JAVA/"MainActivity.java").read_text(encoding="utf-8")

    def test_invalid_hotspot_credentials_release_ap_and_try_direct(self):
        ready=self.service.split("private void startHotspotFallback(String reason){",1)[1]
        ready=ready.split("@Override public void failure(String why)",1)[0]
        invalid=ready.split("if(!QrInputValidation.validWifiCredentials(ssid,pass)){",1)[1]
        invalid=invalid.split("return;",1)[0]
        self.assertLess(invalid.index("hotspot.stop();resetHotspot();"),
                        invalid.index("startDirectFallback("))
        self.assertIn("Android не предоставил корректные параметры точки доступа",invalid)

    def test_direct_group_credentials_are_valid_before_ready_callback(self):
        read=self.direct.split("private void readGroup(int id){",1)[1]
        read=read.split("private static String localIp(",1)[0]
        self.assertIn("QrInputValidation.validWifiCredentials(ssid,password)",read)
        self.assertLess(read.index("QrInputValidation.validWifiCredentials(ssid,password)"),
                        read.index("listener.ready("))

    def test_lan_remains_first_and_no_qr_during_fallback_start(self):
        route=self.service.split("private void establishNetworkRoute(){",1)[1]
        route=route.split("private void startDirectFallback(",1)[0]
        self.assertLess(route.index("WifiState.clientAddress(this)"),
                        route.index("startHotspotFallback("))
        self.assertIn('if(directStarting||hotspotStarting)return;',route)
        render=self.main.split("private void renderQr(){",1)[1]
        render=render.split("private Bitmap makeQr(",1)[0]
        self.assertIn("TransferService.directStarting||TransferService.hotspotStarting",render)
        self.assertIn("qrImage.setImageDrawable(null);lastQr=\"\";",render)


if __name__=="__main__":
    unittest.main()
