"""Regression: automatic LAN-first routing and user-visible transfer copy."""
from pathlib import Path
import unittest

JAVA=Path(__file__).resolve().parents[1]/"app/src/main/java/dev/xarkon/link"

class AutoNetworkUiTests(unittest.TestCase):
    def test_manual_network_buttons_removed(self):
        source=(JAVA/"MainActivity.java").read_text(encoding="utf-8")
        self.assertNotIn('"СОЗДАТЬ СЕТЬ ДЛЯ ДРУГОГО WI-FI"',source)
        self.assertNotIn('"ВОЗВРАТ К ОБЫЧНОМУ WI-FI"',source)
        self.assertIn('boolean onLan=!lanAddress.isEmpty();',source)
        self.assertIn('start(TransferService.ROTATE)',source)
        self.assertNotIn('start(TransferService.USE_HOTSPOT)',source)

    def test_legacy_forced_hotspot_does_not_override_lan(self):
        source=(JAVA/"TransferService.java").read_text(encoding="utf-8")
        self.assertIn('saved.edit().remove("force_hotspot").apply();',source)
        self.assertIn('forceHotspot=false; // Legacy network-mode intents now use automatic routing.',source)
        self.assertIn('if(!lan.isEmpty()){',source)
        self.assertIn('String external=WifiState.hostedApAddress(this);',source)
        self.assertIn('startHotspotFallback("Нет общей Wi-Fi-сети")',source)

    def test_transfer_status_and_separator(self):
        source=(JAVA/"MainActivity.java").read_text(encoding="utf-8")
        self.assertIn('"Идёт передача файлов…"',source)
        self.assertIn('"Файлов: "+jobs.size()+"  |  "+Util.readable(size)',source)
        self.assertIn('next.add(sign+file.name+" | "+Util.readable(',source)
        self.assertIn('" | "+(status.isEmpty()?',source)

if __name__=="__main__":
    unittest.main()
