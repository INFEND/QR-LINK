"""Regression guards for stale network callbacks and receiver socket lifetime."""
from pathlib import Path
import unittest
J=Path(__file__).resolve().parents[1]/"app/src/main/java/dev/xarkon/link"
S=(J/"TransferService.java").read_text(encoding="utf-8")
E=(J/"TransferEngine.java").read_text(encoding="utf-8")
class NetworkSessionGuards(unittest.TestCase):
    def test_destroy_invalidates_all_network_callbacks(self):
        body=S.split("@Override public void onDestroy()",1)[1]
        for item in ("destroyed=true","peerAttempts.next()","autoReconnectLan=false",
                     "wantReceive=false","networkHandler.removeCallbacksAndMessages(null)",
                     "peerHealth.shutdownNow()"):
            self.assertIn(item,body)
        self.assertIn("if(!destroyed)networkHandler.postDelayed(this,1700L)",S)
    def test_direct_probe_has_route_guard(self):
        self.assertIn("final int probeRoute=directRouteAttempt;",S)
        self.assertIn("if(!routeActive(probeRoute))return;",S)
        self.assertIn("private void resetDirect(){groupProbeRunning=false;",S)
    def test_hotspot_callbacks_and_address_poll_have_route_guard(self):
        b=S.split("private void startHotspotFallback(",1)[1].split("private void fallbackWifi(",1)[0]
        self.assertIn("final int route=++directRouteAttempt;",b)
        self.assertGreaterEqual(b.count("if(!routeActive(route))return;"),2)
        self.assertIn("resolveHotspotAddress(attempt+1,route)",b)
        self.assertIn("QrInputValidation.isLocalIpv4(ip)",b)
    def test_reconnect_requires_unchanged_invitation(self):
        self.assertIn('final String pairedQr=saved.getString("pair_qr","");',S)
        self.assertIn('!pairedQr.equals(saved.getString("pair_qr",""))',S)
    def test_restart_isolates_receiver_sockets(self):
        for item in ("private volatile long receiveEpoch;","final ServerSocket listening=socket;",
                     "while(alive&&epoch==receiveEpoch)","handlers.execute(()->serve(s,epoch));",
                     "private void serve(Socket sock,long epoch)","++receiveEpoch;alive=false;",
                     "if(!alive||epoch!=receiveEpoch)throw new IOException"):
            self.assertIn(item,E)
    def test_rejected_handler_closes_socket(self):
        b=E.split("final ServerSocket listening=socket;",1)[1].split('},"xarkon-accept")',1)[0]
        self.assertIn("catch(Exception rejected)",b)
        self.assertIn("s.close()",b)
    def test_discovery_is_scoped_to_receiver_epoch(self):
        self.assertIn("new Thread(()->discoveryLoop(epoch)",E)
        self.assertIn("private void discoveryLoop(long epoch)",E)
    def test_benchmark_disconnects_on_failure(self):
        self.assertIn("finally{if(conn!=null)conn.disconnect();}",E)
if __name__=="__main__":unittest.main()
