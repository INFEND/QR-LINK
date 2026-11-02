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
        self.assertNotIn('на приёмнике выберите «СОЗДАТЬ СЕТЬ ДЛЯ ДРУГОГО WI-FI»',source)
        self.assertIn('откройте получение на приёмнике, дождитесь нового QR',source)

    def test_transfer_status_and_separator(self):
        source=(JAVA/"MainActivity.java").read_text(encoding="utf-8")
        self.assertIn('"Идёт передача файлов…"',source)
        self.assertIn('"Файлов: "+jobs.size()+"  |  "+Util.readable(size)',source)
        self.assertIn('next.add(sign+file.name+" | "+Util.readable(',source)
        self.assertIn('" | "+(status.isEmpty()?',source)


    def test_ota_settings_have_no_last_check_or_available_version_footer(self):
        source=(JAVA/"MainActivity.java").read_text(encoding="utf-8")
        # Remove the entire footer, not just the status text. No empty space.
        for obsolete in ('backgroundCheckStatus', 'updateBackgroundCheckStatus()',
                         'Последняя проверка:', 'Ожидается первая проверка по расписанию'):
            self.assertNotIn(obsolete,source)
        self.assertIn('otaSwitch(parent,"history","Проверка обновлений в фоне"',source)
        self.assertIn('OtaUpdateSchedule.configure(this);',source)
        self.assertIn('selectedLabel.setText(labels[value]);',source)
        self.assertIn('putLong(OtaUpdateSchedule.PREF_AVAILABLE_CODE,r.versionCode)',source)

if __name__=="__main__":
    unittest.main()
