"""v0.3.76: bounded receiver, durable completion, safe restoration and route generations."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
ENGINE=(JAVA/"TransferEngine.java").read_text(encoding="utf-8")
SERVICE=(JAVA/"TransferService.java").read_text(encoding="utf-8")

class Reliability76(unittest.TestCase):
    def test_session_key_policy_on_jvm(self):
        harness='''package dev.xarkon.link;
public final class CheckSessionKey76 {
 public static void main(String[] args) {
  String key="a".repeat(64);
  if(!SessionKeyPolicy.valid(key))throw new AssertionError("valid");
  if(!SessionKeyPolicy.matches(key,key))throw new AssertionError("equal");
  if(SessionKeyPolicy.matches(key,"b".repeat(64)))throw new AssertionError("different");
  if(SessionKeyPolicy.matches(key,null))throw new AssertionError("missing");
  if(SessionKeyPolicy.matches(key,""))throw new AssertionError("empty");
  if(SessionKeyPolicy.valid("A".repeat(64)))throw new AssertionError("case");
  if(SessionKeyPolicy.valid("a".repeat(63)+"!"))throw new AssertionError("invalid");
  if(SessionKeyPolicy.valid("a".repeat(65)))throw new AssertionError("length");
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"CheckSessionKey76.java"
            p.write_text(harness,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",folder,
                            str(JAVA/"SessionKeyPolicy.java"),str(p)],check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",folder,"dev.xarkon.link.CheckSessionKey76"],
                           check=True,capture_output=True,text=True)

    def test_receiver_backlog_is_bounded(self):
        self.assertIn("new ThreadPoolExecutor(16,16,0L,TimeUnit.MILLISECONDS",ENGINE)
        self.assertIn("new ArrayBlockingQueue<Runnable>(64)",ENGINE)
        self.assertIn("activeConnections.add(s)",ENGINE)
        self.assertIn("activeConnections.remove(s)",ENGINE)

    def test_stop_closes_inflight_sockets(self):
        stop=ENGINE.split("public synchronized void stop()",1)[1].split("public void shutdown()",1)[0]
        self.assertIn("for(Socket active:activeConnections)",stop)
        self.assertIn("active.close()",stop)

    def test_receiver_key_never_uses_plain_string_equals(self):
        self.assertIn('SessionKeyPolicy.matches(sessionKey,heads.get("x-xarkon-key"))',ENGINE)
        self.assertIn("SessionKeyPolicy.valid(chosenKey)",ENGINE)
        self.assertIn("SessionKeyPolicy.valid(reverseKey)",ENGINE)

    def test_completed_state_is_durable(self):
        self.assertIn('.put("completed",inc.completed)',ENGINE)
        self.assertIn('in.completed=j.optBoolean("completed",false)&&in.done.cardinality()==count;',ENGINE)
        self.assertIn('try{persist(inc);}catch(IOException failure){inc.completed=false;throw failure;}',ENGINE)

    def test_restore_rejects_untrusted_metadata(self):
        self.assertIn('MediaStore.AUTHORITY.equals(restoredUri.getAuthority())',ENGINE)
        self.assertIn('restoredName.equals(Util.safeName(restoredName))',ENGINE)
        self.assertIn('restoredPath.equals(Util.safePath(restoredPath))',ENGINE)
        self.assertIn('if(inc.completed)throw new IOException("Сохранённый файл повреждён.',ENGINE)

    def test_direct_route_resets_stale_probe(self):
        self.assertIn('private synchronized int nextDirectRoute(){groupProbeRunning=false;return ++directRouteAttempt;}',SERVICE)
        self.assertIn('final int route=nextDirectRoute();',SERVICE)
        self.assertIn('final int probeRoute=directRouteAttempt;',SERVICE)
        self.assertIn('if(!routeActive(probeRoute))return;',SERVICE)

    def test_receiver_startup_error_is_localized(self):
        self.assertIn('note("Не удалось запустить приём: "+ErrorText.human(e))',SERVICE)
        self.assertNotIn('note("Не удалось запустить приём: "+e.getMessage())',SERVICE)

if __name__=="__main__":
    unittest.main()
