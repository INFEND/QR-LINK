"""Service owns QR validation, background health and automatic LAN recovery."""
from pathlib import Path
import unittest
JAVA=Path(__file__).resolve().parents[1]/"app/src/main/java/dev/xarkon/link"
MAIN=(JAVA/"MainActivity.java").read_text(encoding="utf-8")
SERVICE=(JAVA/"TransferService.java").read_text(encoding="utf-8")
class PeerLifecycleTests(unittest.TestCase):
    def test_all_qr_handshakes_are_service_owned(self):
        block=MAIN.split("private void connectQr(String raw){",1)[1].split("private void validatePaired()",1)[0]
        self.assertIn('request.putExtra("qr",raw);launchService(request);',block)
        self.assertNotIn("new Thread(",block)
        self.assertNotIn("TransferService.peerVerified=true",block)
        self.assertIn("verifyReceiver(info.host,info,false,raw,attempt)",SERVICE)
    def test_health_and_reconnect_use_attempt_guard(self):
        self.assertIn("private void monitorPeer()",SERVICE)
        self.assertIn("peerAttempts.snapshot()",SERVICE)
        self.assertIn("if(!peerAttempts.current(attempt)||!peerVerified||isSending||isBusy)return;",SERVICE)
        self.assertIn('if(info.hotspot||!info.key.equals(saved.getString("key","")))return;',SERVICE)
        self.assertIn("if(!autoReconnectLan||peerReconnectBusy",SERVICE)
        self.assertIn("peerHealth.shutdownNow()",SERVICE)
    def test_manual_reconnect_reuses_saved_qr(self):
        block=MAIN.split("private void validatePaired(){",1)[1].split("private void probeSavedPeer(",1)[0]
        self.assertIn('request.putExtra("qr",raw);launchService(request);',block)
        self.assertNotIn("invitation.hotspot&&",block)
if __name__=="__main__":unittest.main()
