"""Regression checks for visible queue status and safe system hotspot priority."""
from pathlib import Path
import unittest

JAVA=Path(__file__).resolve().parents[1]/"app/src/main/java/dev/xarkon/link"

class QueueMarqueeTests(unittest.TestCase):
    def test_marquee_and_file_status(self):
        src=(JAVA/"MainActivity.java").read_text(encoding="utf-8")
        self.assertIn("row.setEllipsize(android.text.TextUtils.TruncateAt.MARQUEE)",src)
        self.assertIn("row.setMarqueeRepeatLimit(-1);",src)
        self.assertIn("row.setSelected(true);",src)
        self.assertIn('status.isEmpty()?"В очереди":ErrorText.human(status)',src)
        self.assertIn("transferQueueRows.set(i,next.get(i));",src)

    def test_system_hotspot_invalidates_direct_attempt(self):
        src=(JAVA/"TransferService.java").read_text(encoding="utf-8")
        fragment=src[src.index("if(!external.isEmpty()){"):src.index("systemApHost=external;")]
        self.assertIn("nextDirectRoute();",fragment)
        self.assertIn("directWifi.close();hotspot.stop();resetDirect();resetHotspot();",fragment)

if __name__=="__main__":
    unittest.main()
