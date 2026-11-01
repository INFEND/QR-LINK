"""U25: all app-owned confirmations and notifications are themed."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]/"app/src/main/java/dev/xarkon/link"

class ThemedMessages(unittest.TestCase):
    def test_main_has_no_platform_confirmation_dialogs(self):
        source=(ROOT/"MainActivity.java").read_text(encoding="utf-8")
        self.assertNotIn("new AlertDialog.Builder",source)
        self.assertIn('UiConfirmDialog.show(this,"Скачать из ShareMe?"',source)
        self.assertIn('UiConfirmDialog.show(this,"Доступ к камере"',source)
        self.assertIn("if(actionDialog!=null){actionDialog.dismiss();actionDialog=null;}",source)

    def test_dialog_is_animated_accessible_and_themed(self):
        source=(ROOT/"UiConfirmDialog.java").read_text(encoding="utf-8")
        for expected in ("theme_mode","accent","motion",'new UiIcon(a,"info"',
                         'new UiIcon(a,"close"','new UiIcon(a,"check"',
                         "setContentDescription","setOnClickListener",
                         "card.animate().alpha(1f)","card.animate().alpha(0f)",
                         "dialog.dismiss()","isDestroyed()"):
            self.assertIn(expected,source)

    def test_installer_notice_does_not_use_platform_toast(self):
        source=(ROOT/"UpdateManager.java").read_text(encoding="utf-8")
        self.assertNotIn("Toast.makeText",source)
        self.assertIn('notice.show(a,"Разрешите установку',source)
        self.assertIn("if(a.isFinishing()||a.isDestroyed())return;",source)

if __name__=="__main__":
    unittest.main()
