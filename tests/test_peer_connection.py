"""Executable stale-callback test and source-level pairing UI checks."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
HARNESS="""package dev.xarkon.link;
public final class PeerAttemptGuardCheck {
 public static void main(String[] args) {
  PeerAttemptGuard g=new PeerAttemptGuard();
  int first=g.next();
  if(!g.current(first))throw new AssertionError("Current attempt rejected");
  int second=g.next();
  if(g.current(first)||!g.current(second))throw new AssertionError("Stale callback accepted");
  g.next();
  if(g.current(second))throw new AssertionError("Disconnect did not invalidate");
 }
}
"""
class PeerConnectionContract(unittest.TestCase):
    def test_stale_callbacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/"PeerAttemptGuardCheck.java"
            src.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,
                str(JAVA/"PeerAttemptGuard.java"),str(src)],check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.PeerAttemptGuardCheck"],
                check=True,capture_output=True,text=True)
    def test_card_requires_verified_hello(self):
        src=(JAVA/"MainActivity.java").read_text(encoding="utf-8")
        self.assertIn("private boolean sessionConfirmed()",src)
        self.assertIn("TransferService.peerVerified&&WifiState.localTransferReady(this)",src)
        self.assertIn("displayedPairState=sessionConfirmed()",src)
        self.assertIn('request.putExtra("qr",raw)',src)
        self.assertIn("TransferService.DISCONNECT_PEER",src)
        self.assertIn("if(token!=peerProbeGeneration)return;",src)
    def test_callbacks_and_disconnect_are_guarded(self):
        src=(JAVA/"TransferService.java").read_text(encoding="utf-8")
        self.assertIn("peerAttempts.current(attempt)",src)
        self.assertIn('"/hello","GET",null',src)
        self.assertIn('putString("pair_qr",raw)',src)
        self.assertIn("peerVerified=true;",src)
        self.assertIn("peerAttempts.next();peerVerified=false;",src)
        self.assertIn("peerVerified=false;reverseVerified=false;peerState=\"\";isReceiving=false;",src)
if __name__=="__main__":
    unittest.main()
