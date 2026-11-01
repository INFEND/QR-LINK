"""Regression: QR LINK must prefer a fast protected hotspot and support cross-router pairing."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
J=ROOT/"app/src/main/java/dev/xarkon/link"
HARNESS="""package dev.xarkon.link;
public final class SubnetCheck {
  static void yes(boolean v){if(!v)throw new AssertionError("Wrong subnet classification");}
  public static void main(String[] args){
    yes(WifiSubnetPolicy.sameSubnet("192.168.1.10","192.168.1.250",24));
    yes(!WifiSubnetPolicy.sameSubnet("192.168.1.10","192.168.2.10",24));
    yes(WifiSubnetPolicy.sameSubnet("192.168.1.10","192.168.2.10",16));
    yes(WifiSubnetPolicy.sameSubnet("10.0.0.2","172.16.4.1",0));
    yes(!WifiSubnetPolicy.sameSubnet("192.168.1.1","192.168.1.1",33));
    yes(!WifiSubnetPolicy.sameSubnet("192.168.1.1","8.8.8.8",24));
    yes(!WifiSubnetPolicy.sameSubnet("192.168.1.1","invalid",24));
  }
}
"""

class CrossNetworkHotspotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service=(J/"TransferService.java").read_text(encoding="utf-8")
        cls.main=(J/"MainActivity.java").read_text(encoding="utf-8")
        cls.hotspot=(J/"HotspotSupport.java").read_text(encoding="utf-8")
        cls.direct=(J/"DirectWifi.java").read_text(encoding="utf-8")
        cls.pairing=(J/"Pairing.java").read_text(encoding="utf-8")
        cls.connector=(J/"WifiPeerConnector.java").read_text(encoding="utf-8")
        cls.wifi=(J/"WifiState.java").read_text(encoding="utf-8")

    def test_fast_hotspot_precedes_direct_without_shared_wifi(self):
        route=self.service.split("private void establishNetworkRoute(){",1)[1].split(
            "private void startDirectFallback(",1)[0]
        self.assertIn('startHotspotFallback("Нет общей Wi-Fi-сети");',route)
        self.assertNotIn("directWifi.host(",route)
        direct=self.service.split("private void startDirectFallback(",1)[1].split(
            "private void startHotspotFallback(",1)[0]
        self.assertIn("directWifi.host(new DirectWifi.HostListener(){",direct)
        self.assertIn("},12000);",self.direct)
        self.assertNotIn("},22000);",self.direct)

    def test_hotspot_survives_qr_refresh(self):
        route=self.service.split("private void establishNetworkRoute(){",1)[1].split(
            "private void startDirectFallback(",1)[0]
        self.assertLess(route.index("if(hotspotReady){"),route.index("if(directReady){"))
        self.assertLess(route.index("if(hotspotReady){"),route.index("startHotspotFallback("))
        self.assertIn("if(ROTATE.equals(action)||modeChange){",self.service)
        self.assertIn("start(TransferService.ROTATE)",self.main)

    def test_manual_hotspot_mode_keeps_hotspot_on_router_wifi(self):
        self.assertIn('USE_HOTSPOT="dev.xarkon.link.USE_HOTSPOT"',self.service)
        self.assertIn('forceHotspot=USE_HOTSPOT.equals(action);',self.service)
        self.assertIn('if(!forceHotspot&&!lan.isEmpty()){',self.service)
        self.assertIn('boolean onLan=!TransferService.forceHotspot&&!lanAddress.isEmpty();',self.main)
        self.assertIn('start(TransferService.USE_HOTSPOT);',self.main)
        self.assertIn('start(TransferService.USE_AUTO);',self.main)
        self.assertIn('if(!forceHotspot&&WifiState.clientConnected(this))',self.service)

    def test_password_is_transmitted_in_qr_and_android_approves(self):
        self.assertIn('.appendQueryParameter("pwd",password)',self.pairing)
        self.assertIn('.setNetworkSpecifier(spec.build()).build()',self.connector)
        self.assertIn('spec.setWpa2Passphrase(info.password);',self.connector)
        self.assertIn('spec.setWpa3Passphrase(info.password);',self.connector)
        self.assertIn('Пароль уже содержится в QR',self.main)
        self.assertIn('if(info.hotspot)',self.main)

    def test_unknown_hotspot_gateway_does_not_hide_qr(self):
        self.assertIn('hotspotHost="";',self.service)
        self.assertIn('status="Точка доступа готова · адрес определится при подключении";',self.service)
        render=self.main.split("private void renderQr(){",1)[1].split("private Bitmap makeQr(",1)[0]
        self.assertIn('if(localAp&&host.isEmpty()){',render)
        self.assertIn('Pairing.buildHotspot(host,key',render)
        block=render.split("if(localAp&&host.isEmpty()){",1)[1].split("}",1)[0]
        self.assertNotIn('qrImage.setImageDrawable(null)',block)
        self.assertNotIn('return;',block)

    def test_station_address_never_advertised_as_hotspot(self):
        self.assertIn('String station="";',self.hotspot)
        self.assertIn('a.getHostAddress().equals(station)',self.hotspot)
        self.assertIn('hotspotIp(context);',self.hotspot)
        self.assertIn('hotspotIp(this);',self.service)

    def test_warn_different_subnet_but_still_attempt_tcp(self):
        self.assertIn("peerOutsideOnLinkSubnet(Context c,String peer)",self.wifi)
        self.assertIn("WifiSubnetPolicy.sameSubnet(station,peer,prefix)",self.wifi)
        self.assertIn("peerOutsideOnLinkSubnet(this,info.host)",self.main)
        self.assertIn("verifyReceiver(info.host,info,false,raw,attempt);",self.service)

    def test_jvm_ipv4_subnet_policy(self):
        with tempfile.TemporaryDirectory() as folder:
            harness=Path(folder)/"SubnetCheck.java"
            harness.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",folder,
                str(J/"WifiSubnetPolicy.java"),str(harness)],check=True,
                capture_output=True,text=True)
            subprocess.run(["java","-cp",folder,"dev.xarkon.link.SubnetCheck"],
                           check=True,capture_output=True,text=True)

if __name__=="__main__":
    unittest.main()
