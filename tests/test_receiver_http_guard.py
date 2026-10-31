"""Source-level checks for slow-client and duplicate-header hardening."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]/"app/src/main/java/dev/xarkon/link"
class HttpGuardTests(unittest.TestCase):
 def test_authenticated_timeout_and_unique_headers(self):
  server=(ROOT/"TransferEngine.java").read_text(encoding="utf-8")
  self.assertIn("s.setSoTimeout(5000);",server)
  self.assertIn("s.setSoTimeout(90000);",server)
  self.assertLess(server.index("s.setSoTimeout(5000);"),server.index("s.setSoTimeout(90000);"))
  self.assertIn("heads.putIfAbsent(field",server)
  self.assertIn("Повторяющийся заголовок",server)
 def test_all_hello_paths_validate_version(self):
  for filename in ("MainActivity.java","TransferService.java","TransferEngine.java"):
   src=(ROOT/filename).read_text(encoding="utf-8")
   self.assertIn("PeerIdentity.compatible(",src)
if __name__=="__main__":unittest.main()
