"""Regression tests for the independent reliability fixes in 0.3.73."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
J = ROOT / "app/src/main/java/dev/xarkon/link"
S = (J / "TransferService.java").read_text(encoding="utf-8")
E = (J / "TransferEngine.java").read_text(encoding="utf-8")
F = (J / "FileCatalog.java").read_text(encoding="utf-8")
D = (J / "DirectWifi.java").read_text(encoding="utf-8")

class NetworkIntegrity73(unittest.TestCase):
    def test_failed_reverse_pair_does_not_invalidate_verified_session(self):
        section = S.split("@Override public boolean reversePair(", 1)[1].split(
            "private void verifyReceiver(", 1)[0]
        self.assertIn("final int expectedAttempt=peerAttempts.snapshot();", section)
        self.assertLess(section.index('"/hello","GET"'),
                        section.index("peerAttempts.advanceIfCurrent(expectedAttempt)"))
        self.assertNotIn("peerAttempts.next()", section)
        java = """package dev.xarkon.link;
public final class PeerGuard73 {
    public static void main(String[] args) {
        PeerAttemptGuard guard = new PeerAttemptGuard();
        int first = guard.snapshot();
        if (!guard.current(first)) throw new AssertionError("initial");
        int second = guard.advanceIfCurrent(first);
        if (second != first + 1 || !guard.current(second))
            throw new AssertionError("advance");
        if (guard.advanceIfCurrent(first) != -1 || guard.current(first))
            throw new AssertionError("stale attempt accepted");
        if (guard.next() != second + 1)
            throw new AssertionError("next");
    }
}"""
        with tempfile.TemporaryDirectory() as directory:
            harness = Path(directory) / "PeerGuard73.java"
            harness.write_text(java, encoding="utf-8")
            subprocess.run(["javac", "-encoding", "UTF-8", "-d", directory,
                            str(J / "PeerAttemptGuard.java"), str(harness)],
                           check=True, capture_output=True, text=True)
            subprocess.run(["java", "-cp", directory, "dev.xarkon.link.PeerGuard73"],
                           check=True, capture_output=True, text=True)

    def test_confirmed_peer_requires_durable_preferences(self):
        section = S.split("private void verifyReceiver(", 1)[1].split(
            "private void monitorPeer()", 1)[0]
        self.assertIn('.putString("peer_name",PeerIdentity.displayName', section)
        self.assertIn('.commit())', section)
        self.assertIn("Не удалось сохранить подтверждённое соединение", section)
        self.assertLess(section.index(".commit())"), section.index("peerVerified=true;"))

    def test_http_rejects_incomplete_headers(self):
        self.assertIn('throw new EOFException("Незавершённая строка HTTP-заголовка")', E)
        self.assertIn("boolean headersFinished=false;", E)
        self.assertIn("if(ln.isEmpty()){headersFinished=true;break;}", E)
        self.assertIn('if(!headersFinished){', E)
        self.assertLess(E.index("if(!headersFinished){"),
                        E.index('heads.containsKey("transfer-encoding")'))

    def test_control_requests_have_shorter_timeouts_than_chunks(self):
        self.assertIn('path.startsWith("/chunk/")||path.equals("/bench")', E)
        self.assertIn("s.setSoTimeout(streaming?90000:10000);", E)

    def test_status_journal_survives_failed_merge(self):
        self.assertIn("boolean statusesMerged=!mergePendingStatuses||items.isEmpty();", F)
        self.assertIn("statusesMerged=true;", F)
        self.assertIn("if(statusesMerged&&mergePendingStatuses)", F)
        self.assertNotIn('try{statusDb(c).delete("item_status",null,null);}catch(Exception ignored){}\n        QueueRevision.changed();', F)

    def test_destroyed_direct_cannot_restart_radio(self):
        self.assertGreaterEqual(D.count('if(closed){listener.failure("Wi-Fi Direct уже остановлен");return;}'), 2)
        self.assertIn("if(closed||id!=serial||!hosting", D)
        self.assertIn("if(closed||id!=serial||!joining", D)

    def test_receiver_requires_valid_ip_for_ready_state(self):
        self.assertIn("boolean networkReady=WifiState.localTransferReady(this);", S)
        self.assertIn("QrInputValidation.isLocalIpv4(listenIp)?", S)
        self.assertIn("Ожидание IP-адреса для приёма", S)

    def test_fully_resumed_sender_still_checks_source(self):
        send = E.split("private void sendOne(", 1)[1].split("private void sendChunk(", 1)[0]
        self.assertIn("if(completed.cardinality()==blocks){", send)
        self.assertIn("openInputStream(sourceUri)", send)
        self.assertIn("actual!=job.size", send)

    def test_completed_destination_rechecked_before_resume_ack(self):
        offer = E.split("private JSONObject offer(", 1)[1].split("private static class Incoming", 1)[0]
        self.assertIn("if(inc.completed){", offer)
        self.assertIn('openFileDescriptor(inc.uri,"r")', offer)
        self.assertIn("actual!=inc.size", offer)
        self.assertLess(offer.index("if(inc.completed){"), offer.index("return r;"))

if __name__ == "__main__":
    unittest.main()
