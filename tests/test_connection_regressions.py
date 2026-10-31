"""Regression checks for LAN QR, stale peers and immediate transfer cancellation."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
SERVICE=(JAVA/"TransferService.java").read_text(encoding="utf-8")
ENGINE=(JAVA/"TransferEngine.java").read_text(encoding="utf-8")
UTIL=(JAVA/"Util.java").read_text(encoding="utf-8")

HARNESS=r'''package dev.xarkon.link;
public class ChunkIndexCheck {
  private static void ok(boolean b){if(!b)throw new AssertionError("Bad chunk index");}
  public static void main(String[] args){
    ok(ChunkIndex.parse("0",1)==0);
    ok(ChunkIndex.parse("12",13)==12);
    ok(ChunkIndex.parse("12",12)==-1);
    ok(ChunkIndex.parse("-1",10)==-1);
    ok(ChunkIndex.parse("+1",10)==-1);
    ok(ChunkIndex.parse("1/2",10)==-1);
    ok(ChunkIndex.parse("99999999999999999",10)==-1);
    ok(ChunkIndex.parse("4294967295",10)==-1);
    ok(ChunkIndex.parse("0",0)==-1);
    ok(ChunkIndex.parse("",2)==-1);
  }
}
'''
class ConnectionRegressionTests(unittest.TestCase):
    def test_lan_qr_reaches_receiver(self):
        self.assertRegex(SERVICE,r'if\(!info\.hotspot\)\s*\{[^}]*verifyReceiver\(info\.host,info,false,raw,attempt\)')
        self.assertIn('peerState="Подключаемся через общую сеть Wi-Fi"',SERVICE)

    def test_new_qr_invalidates_previous_receiver(self):
        self.assertIn('.remove("port").remove("peer_name").putString("pair_qr",raw).commit()',SERVICE)
        self.assertLess(SERVICE.index('.putString("pair_qr",raw).commit()'),
                        SERVICE.index('if(!info.hotspot){'))

    def test_invalid_qr_and_idle_wifi_loss_are_visible(self):
        self.assertIn('peerState="Ошибка QR: "+ErrorText.human(e)',SERVICE)
        self.assertIn('.remove("pair_qr").commit();\n                peerState="Ошибка QR:',SERVICE)
        self.assertIn('if(peerVerified&&!WifiState.localTransferReady(TransferService.this))',SERVICE)
        self.assertIn('peerAttempts.next();peerVerified=false;',SERVICE)
        self.assertIn('throw new java.io.IOException("Локальная сеть отключилась во время подключения")',SERVICE)

    def test_cancel_before_worker_and_disconnect_inflight_uploads(self):
        self.assertIn('if(sending)engine.prepareSending();',SERVICE)
        self.assertNotIn('sendingCancelled=false;\n        JSONObject hello=',ENGINE)
        self.assertIn('if(sendingCancelled){events.note("Передача остановлена до начала отправки.");return;}',ENGINE)
        self.assertIn('private final Set<HttpURLConnection> activeUploads=ConcurrentHashMap.newKeySet()',ENGINE)
        self.assertIn('for(HttpURLConnection connection:activeUploads)connection.disconnect()',ENGINE)
        self.assertIn('activeUploads.add(con);',ENGINE)
        self.assertIn('activeUploads.remove(con);',ENGINE)
        self.assertIn('if(sendingCancelled||e instanceof ChecksumMismatchException)break;',ENGINE)

    def test_http_connection_always_disconnected(self):
        segment=UTIL.split('public static String http(',1)[1].split('public static String id()',1)[0]
        self.assertRegex(segment,r'HttpURLConnection conn=.*?\n        try\{')
        self.assertIn('}finally{conn.disconnect();}',segment)

    def test_chunk_index_rejects_invalid_input_in_jvm(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/"ChunkIndexCheck.java"
            file.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,
                str(JAVA/"ChunkIndex.java"),str(file)],check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.ChunkIndexCheck"],
                check=True,capture_output=True,text=True)
        self.assertIn('int index=ChunkIndex.parse(segments[3],inc.count)',ENGINE)

if __name__=="__main__":unittest.main()
