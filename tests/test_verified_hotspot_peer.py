"""Regression for R11/R12: a hotspot gateway is not proof of a QR LINK receiver.

Android release CI compiles the network-specific /hello probe; these source
contracts ensure the offline route never reports an unverified candidate.
"""
from pathlib import Path
import unittest

JAVA = Path(__file__).resolve().parents[1] / "app/src/main/java/dev/xarkon/link"


class VerifiedHotspotPeerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.connector = (JAVA / "WifiPeerConnector.java").read_text(encoding="utf-8")
        cls.service = (JAVA / "TransferService.java").read_text(encoding="utf-8")

    def test_candidate_is_authenticated_before_reporting_connection(self):
        block = self.connector.split("private void deliver(Network n,LinkProperties lp){", 1)[1].split(
            "@Override public void onUnavailable()", 1
        )[0]
        self.assertIn("verifyReceiverOnNetwork(n,candidate,info)?candidate:", block)
        self.assertIn("if(confirmed.isEmpty())", block)
        self.assertLess(block.index("verifyReceiverOnNetwork(n,candidate,info)"),
                        block.index("listener.connected(confirmed)"))
        self.assertNotIn("listener.connected(host)", block)
        self.assertNotIn("listener.connected(found)", block)

    def test_authenticated_discovery_is_used_when_advertised_ip_fails(self):
        block = self.connector.split("private void deliver(Network n,LinkProperties lp){", 1)[1].split(
            "@Override public void onUnavailable()", 1
        )[0]
        self.assertIn("discoverPeer(n,properties,info.key,info.port)", block)
        self.assertIn("verifyReceiverOnNetwork(n,discovered,info)", block)
        self.assertLess(block.index("verifyReceiverOnNetwork(n,candidate,info)"),
                        block.index("discoverPeer(n,properties,info.key)"))
        self.assertIn("if(!active()||failed.get())return;", block)
        self.assertIn("synchronized(delivered){if(delivered[0])return;delivered[0]=true;}", block)

    def test_discovery_rejects_reply_for_a_different_session_port(self):
        self.assertIn("String key,int expectedPort", self.connector)
        self.assertIn("DiscoveryAuth.verifies(answer,nonce,key,expectedPort)", self.connector)
        self.assertNotIn("DiscoveryAuth.verifies(answer,nonce,key,Util.PORT)", self.connector)

    def test_probe_uses_selected_wifi_not_vpn_or_default_cellular(self):
        probe = self.connector.split("private static boolean verifyReceiverOnNetwork(", 1)[1].split(
            "private static String discoverPeer(", 1
        )[0]
        self.assertIn("network.openConnection(url)", probe)
        self.assertIn('new URL("http",host,info.port,"/hello")', probe)
        self.assertIn('connection.setRequestProperty("X-Xarkon-Key",info.key);', probe)
        self.assertIn("connection.getResponseCode()!=200", probe)
        self.assertIn("PeerIdentity.compatible(", probe)
        self.assertIn("connection.setInstanceFollowRedirects(false)", probe)
        self.assertIn("finally{if(connection!=null)connection.disconnect();}", probe)
        self.assertIn("QrInputValidation.isLocalIpv4(host)", probe)
        self.assertNotIn("new URL(host).openConnection()", probe)

    def test_service_also_checks_session_before_persisting_peer(self):
        verify = self.service.split("private void verifyReceiver(", 1)[1].split(
            "private void monitorPeer()", 1
        )[0]
        self.assertIn('Util.http(host,info.port,info.key,"/hello","GET",null)', verify)
        self.assertIn("PeerIdentity.compatible(", verify)
        self.assertIn('putString("host",host)', verify)


if __name__ == "__main__":
    unittest.main()
