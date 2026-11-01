"""A receiver must authenticate UDP discovery before a sender sends its QR session key."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"

HARNESS="""package dev.xarkon.link;
public final class DiscoveryAuthHarness {
    private static void check(boolean condition){if(!condition)throw new AssertionError();}
    public static void main(String[] args){
        String key="a".repeat(64),wrong="b".repeat(64);
        String nonce=DiscoveryAuth.newNonce();
        check(nonce.matches("[0-9a-f]{32}"));
        String query=DiscoveryAuth.request(nonce);
        String answer=DiscoveryAuth.reply(query,key,43567);
        check(answer!=null&&DiscoveryAuth.verifies(answer,nonce,key,43567));
        check(!DiscoveryAuth.verifies(answer,nonce,wrong,43567));
        check(!DiscoveryAuth.verifies(answer,DiscoveryAuth.newNonce(),key,43567));
        check(!DiscoveryAuth.verifies(answer,nonce,key,43568));
        check(!DiscoveryAuth.verifies("XARKON_LINK_1|spoofed|43567",nonce,key,43567));
        check(!DiscoveryAuth.verifies(answer+"|injected",nonce,key,43567));
        check(DiscoveryAuth.reply("XARKON_DISCOVER_1",key,43567)==null);
        check(DiscoveryAuth.reply("XARKON_DISCOVER_2|invalid",key,43567)==null);
        check(DiscoveryAuth.reply(query,"not-a-key",43567)==null);
        String tampered=answer.substring(0,answer.length()-6)+"0"+answer.substring(answer.length()-5);
        check(!DiscoveryAuth.verifies(tampered,nonce,key,43567));
    }
}
"""

class DiscoveryAuthTests(unittest.TestCase):
    def test_sender_and_receiver_use_authenticated_v2_discovery(self):
        sender=(JAVA/"WifiPeerConnector.java").read_text(encoding="utf-8")
        receiver=(JAVA/"TransferEngine.java").read_text(encoding="utf-8")
        self.assertIn("DiscoveryAuth.request(nonce)",sender)
        self.assertIn("DiscoveryAuth.verifies(answer,nonce,key,Util.PORT)",sender)
        self.assertIn("DiscoveryAuth.reply(msg,sessionKey,Util.PORT)",receiver)
        self.assertNotIn('answer.startsWith("XARKON_LINK_1|")',sender)
        self.assertIn("network.bindSocket(socket)",sender)

    @unittest.skipUnless(shutil.which("javac") and shutil.which("java"),"Java 17 is required")
    def test_hmac_challenge_response_rejects_spoofing(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"DiscoveryAuthHarness.java"
            source.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-d",tmp,str(JAVA/"DiscoveryAuth.java"),str(source)],
                           check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.DiscoveryAuthHarness"],
                           check=True,capture_output=True,text=True)

if __name__=="__main__":unittest.main()
