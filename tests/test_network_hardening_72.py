"""Release 0.3.72: network lifecycle, HTTP framing and large-transfer regressions."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
J=ROOT/"app/src/main/java/dev/xarkon/link"
S=(J/"TransferService.java").read_text(encoding="utf-8")
E=(J/"TransferEngine.java").read_text(encoding="utf-8")
U=(J/"Util.java").read_text(encoding="utf-8")
class NetworkHardening72(unittest.TestCase):
    def test_new_pairing_and_reconnect_cancel_previous_upload(self):
        self.assertIn('String raw=in.getStringExtra("qr");\n            // A new invitation must never leave an upload running to the old peer.\n            engine.cancelSending();',S)
        self.assertIn('private void reconnectSavedPeer(){\n        // Switching routes cancels the previous outbound upload, not the queue.\n        engine.cancelSending();',S)
    def test_failed_old_upload_cannot_invalidate_new_peer(self):
        self.assertIn('final int sendAttempt=peerAttempts.snapshot();',S)
        self.assertIn('if(peerAttempts.current(sendAttempt)&&!WifiState.localTransferReady(this))',S)
        # A local file error must not invalidate a healthy, newer authenticated peer.
        body=S.split("final int sendAttempt=peerAttempts.snapshot();",1)[1].split("},true);",1)[0]
        self.assertNotIn('if(peerAttempts.current(sendAttempt))peerVerified=false;',body)
    def test_shutdown_interrupts_uploads(self):
        self.assertIn('engine.cancelSending();engine.shutdown();',S.split('public void onDestroy()',1)[1])
    def test_executor_rejection_cannot_crash_network_watcher(self):
        self.assertIn('}catch(RejectedExecutionException ignored){peerHealthBusy=false;}',S)
        self.assertIn('}catch(RejectedExecutionException ignored){peerReconnectBusy=false;}',S)
    def test_http_framing_is_bounded_and_unambiguous(self):
        for fragment in ('"HTTP/1.1".equals(pieces[2])','headerBytes>16384',
                         'matches("[A-Za-z0-9-]+")','heads.containsKey("transfer-encoding")',
                         'if(contentLength<0)'):
            self.assertIn(fragment,E)
    def test_authentication_memory_bounded(self):
        self.assertIn('lastBadPin.size()>=4096',E)
        self.assertIn('lastBadPin.entrySet().removeIf',E)
        self.assertIn('block.lastSeen=now;',E)
    def test_streams_large_files_without_boxed_pending_list(self):
        self.assertIn('while(nextIndex<blocks||active>0)',E)
        self.assertIn('if(completed.get(ix))continue;',E)
        self.assertIn('if(active==0)continue;',E)
        self.assertNotIn('ArrayList<Integer>todo=',E)
    def test_errors_are_localized_and_deep_paths_fail_loudly(self):
        self.assertIn('String readable=ErrorText.human(e);',E)
        self.assertIn('throw new IllegalArgumentException("Слишком длинный путь вложенной папки")',U)
    def test_http_errors_display_server_message_without_raw_http(self):
        harness='''package dev.xarkon.link;
public final class ErrorTextCheck72 {
  public static void main(String[] args) {
    String a=ErrorText.human("HTTP 409: {\\"error\\":\\"Неверный ключ сеанса\\"}");
    if(!a.equals("Неверный ключ сеанса"))throw new AssertionError(a);
    String b=ErrorText.human("HTTP 503: internal error");
    if(!b.equals("Сервер временно недоступен. Повторите попытку позже."))throw new AssertionError(b);
  }
}'''
        with tempfile.TemporaryDirectory() as d:
            h=Path(d)/"ErrorTextCheck72.java"
            h.write_text(harness,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",d,
                            str(J/"ErrorText.java"),str(h)],check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",d,"dev.xarkon.link.ErrorTextCheck72"],
                           check=True,capture_output=True,text=True)
if __name__=="__main__":unittest.main()
