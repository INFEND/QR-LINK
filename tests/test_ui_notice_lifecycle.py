"""Theme-aware notices in the main and recovery screens."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]/"app/src/main/java/dev/xarkon/link"
class Notices(unittest.TestCase):
 def test_home_uses_theme_and_dismisses_on_destroy(self):
  s=(ROOT/"MainActivity.java").read_text()
  self.assertIn("notices.show(this,message,accent,card,fg,kind);",s)
  self.assertIn("notices.dismiss();",s)
  self.assertNotIn("Toast.makeText(",s)
 def test_recovery_uses_safe_red_theme_and_lifecycle(self):
  s=(ROOT/"RecoveryActivity.java").read_text()
  self.assertIn("notices.show(this,\"Отчёт скопирован\",accent,panel,text,UiNotice.SUCCESS)",s)
  self.assertIn("notices.dismiss();",s)
  self.assertNotIn("Toast.makeText(",s)
 def test_popup_is_nonblocking_and_bounded(self):
  s=(ROOT/"UiNotice.java").read_text()
  self.assertIn("notice.setTouchable(false)",s)
  self.assertIn("handler.postDelayed(timeout",s)
  self.assertIn("if(popup!=null){popup.dismiss();popup=null;}",s)
if __name__=="__main__":unittest.main()
