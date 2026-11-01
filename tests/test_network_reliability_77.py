"""v0.3.77: reject unsafe P2P endpoints, bound DHCP wait, preserve pairings."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
DIRECT=(JAVA/"DirectWifi.java").read_text(encoding="utf-8")
WIFI=(JAVA/"WifiPeerConnector.java").read_text(encoding="utf-8")
ENGINE=(JAVA/"TransferEngine.java").read_text(encoding="utf-8")
SERVICE=(JAVA/"TransferService.java").read_text(encoding="utf-8")

class NetworkReliability77(unittest.TestCase):
    def test_address_policy_jvm(self):
        source='''package dev.xarkon.link;
import java.net.InetAddress;
public final class AddressPolicyCheck {
 public static void main(String[] args)throws Exception{
  for(String ip:new String[]{"192.168.49.1","10.0.0.2","172.16.5.1","169.254.1.2"}){
   if(!PeerAddressPolicy.localIpv4(InetAddress.getByName(ip)))throw new AssertionError(ip);
  }
  for(String ip:new String[]{"127.0.0.1","0.0.0.0","8.8.8.8","224.0.0.1","::1"}){
   if(PeerAddressPolicy.localIpv4(InetAddress.getByName(ip)))throw new AssertionError(ip);
  }
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"AddressPolicyCheck.java"
            p.write_text(source,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",folder,
                            str(JAVA/"PeerAddressPolicy.java"),str(p)],check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",folder,"dev.xarkon.link.AddressPolicyCheck"],
                           check=True,capture_output=True,text=True)

    def test_join_rejects_self_group_owner_and_unsafe_ip(self):
        self.assertIn("info.isGroupOwner||!PeerAddressPolicy.localIpv4(info.groupOwnerAddress)",DIRECT)
        self.assertLess(DIRECT.index("info.isGroupOwner||!PeerAddressPolicy.localIpv4"),
                        DIRECT.index("l.connected(info.groupOwnerAddress.getHostAddress())"))

    def test_host_confirm_requires_live_interface_address(self):
        self.assertIn("!localIp(group.getInterface()).isEmpty()",DIRECT)
        self.assertIn("localIp(group.getInterface()).equals(advertisedHost)",DIRECT)
        self.assertIn("directWifi.confirmHosting(directSsid,directHost,valid->{",SERVICE)

    def test_driver_errors_are_localized(self):
        self.assertNotIn("e.getMessage()",DIRECT)
        self.assertIn("ErrorText.human(e)",DIRECT)

    def test_dhcp_wait_has_bounded_timeout(self):
        self.assertIn("ipDeadlineScheduled.compareAndSet(false,true)",WIFI)
        self.assertIn("},12000L);",WIFI)
        self.assertIn("if(delivered[0])return;",WIFI)

    def test_stale_wifi_link_properties_cannot_replace_bound_route(self):
        self.assertIn("n.equals(propertiesNetwork)?latestProperties:null",WIFI)
        self.assertIn("if(bound&&n.equals(boundNetwork))deliver(n,lp);",WIFI)
        self.assertIn("if(boundNetwork==null||n.equals(boundNetwork))",WIFI)

    def test_receiver_rejects_zero_byte_reads(self):
        self.assertIn('if(n==0)throw new IOException("Приём данных остановился")',ENGINE)
        self.assertIn('if(n==0)throw new IOException("Тест сети не получает данные")',ENGINE)
        self.assertIn('if(n==0)throw new IOException("Не удалось прочитать запрос")',ENGINE)

    def test_local_file_failure_does_not_unpair_receiver(self):
        body=SERVICE.split("final int sendAttempt=peerAttempts.snapshot();",1)[1].split("},true);",1)[0]
        self.assertIn("if(peerAttempts.current(sendAttempt)&&!WifiState.localTransferReady(this))",body)
        self.assertNotIn("if(peerAttempts.current(sendAttempt))peerVerified=false;",body)

    def test_release_version_and_notes(self):
        build=(ROOT/"app/build.gradle").read_text(encoding="utf-8")
        code=int(build.split("versionCode = ",1)[1].splitlines()[0])
        version=build.split("versionName = '",1)[1].split("'",1)[0]
        self.assertGreaterEqual(code,82)
        self.assertTrue((ROOT/"release_notes/v0.3.77.txt").exists())
        self.assertTrue((ROOT/f"release_notes/v{version}.txt").exists())

if __name__=="__main__":unittest.main()
