"""Source regression checks for validated Direct hosting and stale callbacks."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]/"app/src/main/java/dev/xarkon/link"

class DirectReadyTests(unittest.TestCase):
    def test_group_must_have_ip_and_mac_before_ready(self):
        src=(ROOT/"DirectWifi.java").read_text(encoding="utf-8")
        self.assertIn('String ip=localIp(group.getInterface());',src)
        self.assertIn('if(ip.isEmpty()||mac==null||',src)
        self.assertIn('!QrInputValidation.validP2pMac(mac))return;',src)
        self.assertIn('validP2pMac(String raw)',(ROOT/"QrInputValidation.java").read_text(encoding="utf-8"))
        self.assertLess(src.index("if(ip.isEmpty()||mac==null||"),src.index("listener.ready(mac==null"))

    def test_service_rejects_stale_and_unroutable_direct(self):
        src=(ROOT/"TransferService.java").read_text(encoding="utf-8")
        self.assertIn("final int route=nextDirectRoute();",src)
        self.assertGreaterEqual(src.count("nextDirectRoute()"),4)
        self.assertIn("if(!routeActive(route))return;",src)
        self.assertIn("route==directRouteAttempt&&wantReceive&&isReceiving",src)
        self.assertIn("!QrInputValidation.isLocalIpv4(host)",src)
        self.assertIn('status="Wi-Fi Direct не предоставил корректные параметры"',src)
        self.assertIn("resetDirect();directWifi.close();",src)
        # Hotspot was already attempted before Direct; do not restart the same loop.
        self.assertNotIn('startHotspotFallback("Wi-Fi Direct не предоставил корректный IP или MAC")',src)

    def test_ui_hides_qr_without_direct_ip(self):
        src=(ROOT/"MainActivity.java").read_text(encoding="utf-8")
        self.assertIn("if(direct&&(host.isEmpty()||!QrInputValidation.isLocalIpv4(host)||",src)
        self.assertIn('receiveHint.setText("Ожидаем IP и адрес устройства Wi-Fi Direct...")',src)

if __name__=="__main__":
    unittest.main()
