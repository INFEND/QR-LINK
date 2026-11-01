"""End-to-end digest and independent safety regressions for 0.3.75."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
ENGINE=(JAVA/"TransferEngine.java").read_text(encoding="utf-8")
CATALOG=(JAVA/"FileCatalog.java").read_text(encoding="utf-8")
MAIN=(JAVA/"MainActivity.java").read_text(encoding="utf-8")

class Integrity75(unittest.TestCase):
    def test_strict_metadata_validation_executes_in_jvm(self):
        source="""package dev.xarkon.link;
public final class CheckIdentity75 {
 public static void main(String[] args) {
  if(!TransferFileIdentity.validId("12345678-abcd-1234-ABCD-123456789abc"))throw new AssertionError();
  if(TransferFileIdentity.validId("------------------------------------"))throw new AssertionError();
  if(TransferFileIdentity.validId("12345678-abcd-1234-ABCD-123456789abZ"))throw new AssertionError();
  if(!TransferFileIdentity.validMime("image/svg+xml"))throw new AssertionError();
  if(!"application/octet-stream".equals(TransferFileIdentity.safeMime("*/*")))throw new AssertionError();
  if(TransferFileIdentity.validMime("image/png\\r\\nInjected: true"))throw new AssertionError();
  if(!TransferFileIdentity.validSha256("a".repeat(64)))throw new AssertionError();
  if(TransferFileIdentity.validSha256("a".repeat(63)+"z"))throw new AssertionError();
 }
}"""
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"CheckIdentity75.java"
            p.write_text(source,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",d,str(JAVA/"TransferFileIdentity.java"),str(p)],check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",d,"dev.xarkon.link.CheckIdentity75"],check=True,capture_output=True,text=True)

    def test_receiver_advertises_full_file_sha(self):
        self.assertIn('.put("fileSha256",true)',ENGINE)
        self.assertIn('String fileHash=j.optString("fileSha256","");',ENGINE)
        self.assertIn('if(verifyFileSha)offer.put("fileSha256",sourceHash);',ENGINE)
        self.assertIn('TransferFileIdentity.safeMime(job.mime)',ENGINE)
        self.assertIn('if(!TransferFileIdentity.validId(job.id))',ENGINE)

    def test_sender_fingerprints_before_offer_and_after_send(self):
        body=ENGINE.split("private void sendOne(",1)[1].split("private void sendChunk(",1)[0]
        self.assertLess(body.index("hashSource(sourceUri,job.size)"),body.index('"/offer"'))
        self.assertIn('if(verifyFileSha&&!sourceHash.equalsIgnoreCase(hashSource(sourceUri,job.size)))',body)

    def test_receiver_persists_fingerprint_and_rejects_same_size_mutation(self):
        self.assertIn('.put("fileSha256",inc.fileSha256)',ENGINE)
        self.assertIn('in.fileSha256=j.optString("fileSha256","");',ENGINE)
        self.assertIn('!inc.fileSha256.equalsIgnoreCase(fileHash)',ENGINE)
        self.assertIn('!inc.fileSha256.equalsIgnoreCase(hashReceivedFile(inc))',ENGINE)

    def test_receiver_verifies_whole_file_before_publication(self):
        body=ENGINE.split("private void complete(",1)[1].split("public void send(",1)[0]
        self.assertLess(body.index("hashReceivedFile(inc)"),body.index("IS_PENDING,0"))
        self.assertIn('throw new IOException("Контрольная сумма файла не совпала.',body)
        self.assertIn('if(n==0)throw new IOException("Не удалось прочитать содержимое файла")',ENGINE)
        self.assertIn('if(n==0)throw new IOException("Исходный файл не отвечает при чтении")',ENGINE)

    def test_queue_rejects_duplicate_ids_across_different_uris(self):
        body=CATALOG.split("public static synchronized void append(",1)[1].split("public static synchronized void setStatus(",1)[0]
        self.assertIn("HashSet<String> seenIds=new HashSet<>();",body)
        self.assertIn("if(!seenIds.add(item.id))",body)
        self.assertLess(body.index("if(!seenIds.add(item.id))"),body.index("save(c,all)"))

    def test_raw_exceptions_are_not_rendered_in_main_activity(self):
        self.assertNotIn("e.getMessage()",MAIN)
        self.assertIn("ErrorText.human(e)",MAIN)
        self.assertIn('events.note("Поиск устройств: "+ErrorText.human(e));',ENGINE)

    def test_bind_failure_closes_socket_and_clears_key(self):
        start=ENGINE.split("public synchronized void start(",1)[1].split("public synchronized void stop(",1)[0]
        self.assertIn("catch(Exception bindFailure)",start)
        self.assertIn('socket=null;sessionKey="";',start)

    def test_version_and_release_policy(self):
        gradle=(ROOT/"app/build.gradle").read_text(encoding="utf-8")
        self.assertIn("versionCode = 80",gradle)
        self.assertIn("versionName = '0.3.75'",gradle)
        notes=(ROOT/"release_notes/v0.3.75.txt").read_text(encoding="utf-8")
        self.assertGreaterEqual(sum(line.startswith(("[+]","[-]","[=]")) for line in notes.splitlines()),5)

if __name__=="__main__":
    unittest.main()
