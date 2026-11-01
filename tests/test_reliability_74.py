"""Regression checks for independent QR LINK 0.3.74 reliability fixes."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
SERVICE=(JAVA/"TransferService.java").read_text(encoding="utf-8")
ENGINE=(JAVA/"TransferEngine.java").read_text(encoding="utf-8")
DIRECT=(JAVA/"DirectWifi.java").read_text(encoding="utf-8")
WIFI=(JAVA/"WifiState.java").read_text(encoding="utf-8")

class Reliability74(unittest.TestCase):
    def test_reconnects_hotspot_by_qr_not_stale_ip(self):
        method=SERVICE.split("private void reconnectSavedPeer(){",1)[1].split("/** A /pair",1)[0]
        self.assertIn("Pairing.Info savedRoute=Pairing.parse(invitation);",method)
        self.assertIn("if(savedRoute.hotspot){",method)
        self.assertIn('.setAction(CONNECT)',method)
        self.assertLess(method.index("if(savedRoute.hotspot){"),method.index("if(!QrInputValidation.isLocalIpv4(host)"))

    def test_peer_health_ignores_one_timeout(self):
        method=SERVICE.split("private void monitorPeer(){",1)[1].split("private interface Work",1)[0]
        self.assertIn("if(ok){failedPeerHealthChecks=0;}",method)
        self.assertIn("else if(++failedPeerHealthChecks>=2){",method)
        self.assertLess(method.index("else if(++failedPeerHealthChecks>=2){"),method.index("peerAttempts.next();peerVerified=false;reverseVerified=false;"))
        self.assertIn("autoReconnectLan=false;failedPeerHealthChecks=0;",SERVICE)

    def test_resume_checks_source_size_before_skip(self):
        method=ENGINE.split("private void sendOne(",1)[1].split("private void sendChunk(",1)[0]
        self.assertIn("long actual=Util.size(context,sourceUri);",method)
        self.assertIn("if(actual>=0&&actual!=job.size)",method)
        self.assertLess(method.index("if(actual>=0&&actual!=job.size)"),method.index("if(completed.cardinality()==blocks){"))

    def test_sender_rejects_unverified_receiver(self):
        method=ENGINE.split("public void send(",1)[1].split("private void sendOne(",1)[0]
        self.assertIn('if(!verifySha)throw new IOException(',method)
        self.assertIn("Приёмник не подтверждает SHA-256",method)
        self.assertLess(method.index("if(!verifySha)"),method.index("for(FileCatalog.Item job:jobs)"))

    def test_direct_uses_strict_mac_validation(self):
        self.assertIn("!QrInputValidation.validP2pMac(mac)",DIRECT)
        self.assertIn("!QrInputValidation.validP2pMac(desiredMac)",DIRECT)
        self.assertIn("!QrInputValidation.validP2pMac(mac)",SERVICE)
        java="""package dev.xarkon.link;
public class ValidateP2p74 {
  public static void main(String[] args) {
    if(!QrInputValidation.validP2pMac("12:34:56:78:9a:bc")) throw new AssertionError("valid");
    for(String mac:new String[]{"01:00:5e:00:00:01","02:00:00:00:00:00",
      "00:00:00:00:00:00","zz:zz:zz:zz:zz:zz"}) {
      if(QrInputValidation.validP2pMac(mac)) throw new AssertionError(mac);
    }
  }
}"""
        with tempfile.TemporaryDirectory() as directory:
            src=Path(directory)/"ValidateP2p74.java"
            src.write_text(java,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",directory,
                            str(JAVA/"QrInputValidation.java"),str(src)],
                           check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",directory,"dev.xarkon.link.ValidateP2p74"],
                           check=True,capture_output=True,text=True)

    def test_system_hotspot_hint_takes_precedence(self):
        method=WIFI.split("public static String receiveHint(Context c){",1)[1]
        self.assertLess(method.index("if(!hostedApAddress(c).isEmpty())"),method.index("if(!radioOn(c))"))
        self.assertIn("Системная точка доступа включена",method)

    def test_release_metadata_has_at_least_five_user_changes(self):
        notes=(ROOT/"release_notes/v0.3.74.txt").read_text(encoding="utf-8")
        lines=[s for s in notes.splitlines() if s.startswith(("[+]","[-]","[=]"))]
        self.assertGreaterEqual(len(lines),5)
        self.assertTrue(all(len(line.strip())>5 for line in lines))
        gradle=(ROOT/"app/build.gradle").read_text(encoding="utf-8")
        import re
        version_code=int(re.search(r"versionCode\\s*=\\s*(\\d+)",gradle).group(1))
        version_name=re.search(r"versionName\\s*=\\s*'([^']+)'",gradle).group(1)
        self.assertGreaterEqual(version_code,79)
        self.assertGreaterEqual(tuple(map(int,version_name.split("."))),(0,3,74))
        self.assertIn("applicationId = 'dev.xarkon.link'",gradle)

if __name__=="__main__":
    unittest.main()
