"""Regression for a router reconnecting during hotspot startup and false AP IPs."""
from pathlib import Path
import subprocess
import tempfile
import unittest

JAVA = Path(__file__).resolve().parents[1] / "app/src/main/java/dev/xarkon/link"
HARNESS = """
package dev.xarkon.link;
public final class HotspotAddressCheck {
    private static void yes(boolean condition) {
        if (!condition) throw new AssertionError("Unsafe hotspot interface");
    }
    public static void main(String[] args) {
        yes(!HotspotAddressPolicy.isCandidateInterface("wlan0"));
        yes(!HotspotAddressPolicy.isCandidateInterface("WLAN0"));
        yes(!HotspotAddressPolicy.isCandidateInterface("rmnet_data0"));
        yes(!HotspotAddressPolicy.isCandidateInterface(null));
        yes(HotspotAddressPolicy.isCandidateInterface("ap0"));
        yes(HotspotAddressPolicy.isCandidateInterface("swlan0"));
        yes(HotspotAddressPolicy.isCandidateInterface("softap0"));
        yes(HotspotAddressPolicy.isCandidateInterface("wlan1"));
        yes(HotspotAddressPolicy.isCandidateInterface("wlan0.1"));
    }
}
"""


class HotspotRouteSafetyTests(unittest.TestCase):
    def test_delayed_hotspot_callback_cannot_override_reconnected_lan(self):
        service = (JAVA / "TransferService.java").read_text(encoding="utf-8")
        callback = service.split("hotspot.start(new HotspotSupport.Listener(){", 1)[1]
        ready = callback.split("@Override public void failure(", 1)[0]
        self.assertIn("if(!routeActive(route))return;", ready)
        self.assertIn("if(!forceHotspot&&WifiState.clientConnected(TransferService.this)){", ready)
        self.assertIn("establishNetworkRoute();return;", ready)
        self.assertLess(ready.index("WifiState.clientConnected(TransferService.this)"),
                        ready.index("hotspotReady=true;"))

    def test_primary_wifi_station_cannot_be_advertised_as_hotspot(self):
        hotspot = (JAVA / "HotspotSupport.java").read_text(encoding="utf-8")
        self.assertIn("if(!HotspotAddressPolicy.isCandidateInterface(name))continue;", hotspot)
        self.assertNotIn("else if(candidate.isEmpty())candidate=a.getHostAddress();", hotspot)
        self.assertIn("if(accessPoint)return a.getHostAddress();", hotspot)

    def test_interface_policy_jvm(self):
        with tempfile.TemporaryDirectory() as folder:
            harness = Path(folder) / "HotspotAddressCheck.java"
            harness.write_text(HARNESS, encoding="utf-8")
            subprocess.run(["javac", "-encoding", "UTF-8", "-d", folder,
                            str(JAVA / "HotspotAddressPolicy.java"), str(harness)],
                           check=True, capture_output=True, text=True)
            subprocess.run(["java", "-cp", folder, "dev.xarkon.link.HotspotAddressCheck"],
                           check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
