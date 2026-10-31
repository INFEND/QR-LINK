"""Bidirectional pairing protocol and service lifecycle regression checks."""
from pathlib import Path
import re
import unittest
ROOT=Path(__file__).resolve().parents[1]
J=ROOT/"app/src/main/java/dev/xarkon/link"
ENGINE=(J/"TransferEngine.java").read_text(encoding="utf-8")
SERVICE=(J/"TransferService.java").read_text(encoding="utf-8")
MAIN=(J/"MainActivity.java").read_text(encoding="utf-8")
class BidirectionalPairingTests(unittest.TestCase):
    def test_pair_endpoint_authenticated_and_bounded(self):
        self.assertLess(ENGINE.index('sessionKey.equals(heads.get("x-xarkon-key"))'),
                        ENGINE.index('path.equals("/pair")'))
        section=ENGINE.split('path.equals("/pair")',1)[1].split('path.equals("/offer")',1)[0]
        for needle in ("contentLength>2048","QrInputValidation.isLocalIpv4(from)",
                       'reverseKey.matches("[0-9a-f]{64}")',
                       "events.reversePair(from,reverseKey)"):
            self.assertIn(needle,section)
        self.assertNotIn('request.optString("host"',section)
    def test_reverse_server_is_started_before_pair_request(self):
        method=SERVICE.split("private boolean registerReverse(",1)[1].split("private void reconnectSavedPeer(",1)[0]
        self.assertLess(method.index("ensureReverseListener()"),method.index('"/pair","POST"'))
        self.assertIn("engine.start(key.toString())",SERVICE)
        self.assertIn("new SecureRandom().nextBytes(secret)",SERVICE)
        self.assertIn('answer.optBoolean("ok",false)',method)
    def test_reverse_peer_is_verified_before_persisting(self):
        body=SERVICE.split("@Override public boolean reversePair(",1)[1].split("private void verifyReceiver(",1)[0]
        self.assertIn('Util.http(host,Util.PORT,key,"/hello","GET",null)',body)
        self.assertIn("PeerIdentity.compatible",body)
        self.assertLess(body.index("if(!PeerIdentity.compatible"),body.index('.putString("host",host)'))
        self.assertIn("peerAttempts.current(attempt)",body)
        self.assertIn("if(!editor.commit())",body)
    def test_lan_reconnect_renews_reverse_route(self):
        body=SERVICE.split("private void monitorPeer()",1)[1].split("private interface Work",1)[0]
        self.assertIn("registerReverse(info.host,info.port,info.key)",body)
        self.assertIn('pairedQr.equals(saved.getString("pair_qr",""))',body)
    def test_manual_reconnect_handles_reverse_pair_without_qr(self):
        self.assertIn('RECONNECT_PEER="dev.xarkon.link.RECONNECT_PEER"',SERVICE)
        self.assertIn("start(TransferService.RECONNECT_PEER);",MAIN)
        self.assertIn("reconnectSavedPeer();",SERVICE)
    def test_wifi_loss_and_disconnect_stop_passive_server(self):
        self.assertIn("if(!wantReceive&&engine.receiving()&&!WifiState.localTransferReady",SERVICE)
        disconnect=SERVICE.split("if(DISCONNECT_PEER.equals(action))",1)[1].split("if(CANCEL_SEND.equals(action))",1)[0]
        self.assertIn("engine.stop();isReceiving=false;receiveKey=\"\";",disconnect)
    def test_send_requires_verified_session(self):
        send=SERVICE.split("}else if(SEND.equals(action))",1)[1].split("else if(BENCH.equals(action))",1)[0]
        self.assertIn("if(!peerVerified)",send)
        self.assertIn("engine.send(host,port,pin,todo,lanes)",send)
    def test_release_identity(self):
        build=(ROOT/"app/build.gradle").read_text()
        self.assertIn("applicationId = 'dev.xarkon.link'",build)
        self.assertIn("versionCode = 77",build)
        self.assertIn("versionName = '0.3.72'",build)
if __name__=="__main__":unittest.main()
