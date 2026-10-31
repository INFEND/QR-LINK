"""Verified reverse handshake and queue-integrity regressions."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
J=ROOT/"app/src/main/java/dev/xarkon/link"
E=(J/"TransferEngine.java").read_text()
S=(J/"TransferService.java").read_text()
M=(J/"MainActivity.java").read_text()
C=(J/"FileCatalog.java").read_text()
class PairingAckIntegrity(unittest.TestCase):
    def test_ack_after_verification(self):
        body=E.split('path.equals("/pair")',1)[1].split('path.equals("/offer")',1)[0]
        self.assertLess(body.index("events.reversePair(from,reverseKey)"),body.index('reply(out,200,"OK"'))
        self.assertIn('reply(out,409,"Conflict"',body)
    def test_reverse_peer_persisted_before_ready(self):
        body=S.split("@Override public boolean reversePair(",1)[1].split("private void verifyReceiver(",1)[0]
        self.assertLess(body.index('"/hello","GET"'),body.index("editor.commit()"))
        self.assertLess(body.index("editor.commit()"),body.index("reverseVerified=true"))
        self.assertIn("peerAttempts.current(attempt)",body)
        self.assertIn("peerVerified&&!host.equals",body)
    def test_stale_register_cannot_stop_new_listener(self):
        body=S.split("private boolean registerReverse(",1)[1].split("private void reconnectSavedPeer(",1)[0]
        self.assertIn("peerAttempts.current(attempt)",body)
        self.assertIn("!wantReceive&&engine.receiving()",body)
    def test_reconnect_reports_reverse_ack(self):
        self.assertIn("reverseVerified=ok&&reverseOk",S)
        self.assertIn("reverseVerified=reverseOk",S)
        self.assertIn("TransferService.reverseVerified?",M)
    def test_duplicate_queue_ids_fail_closed(self):
        self.assertIn("HashSet<String> uniqueIds=new HashSet<>()",C)
        self.assertIn("!uniqueIds.add(item.id)",C)
    def test_localized_http_errors(self):
        for text in ('error("bad request")','error("Wrong path")','error("Maximum 16 MiB")'):
            self.assertNotIn(text,E)
        self.assertIn('error(ErrorText.human(e))',E)
if __name__=="__main__":unittest.main()
