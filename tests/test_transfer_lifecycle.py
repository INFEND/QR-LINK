from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
HARNESS=r'''package dev.xarkon.link;
public final class TransferLabelCheck {
  static void eq(String a,String b){if(!a.equals(b))throw new AssertionError(a+" != "+b);}
  public static void main(String[] args){
    eq(TransferLabel.direction("Приём: file.zip"),"Приём");
    eq(TransferLabel.direction("Получено: file.zip"),"Приём");
    eq(TransferLabel.direction("Отправка: file.zip"),"Отправка");
    eq(TransferLabel.direction("Готово: file.zip"),"Отправка");
    eq(TransferLabel.file("Готово: file.zip"),"file.zip");
    eq(TransferLabel.direction("Ошибка: file.zip"),"");
  }
}
'''
class TransferLifecycleTests(unittest.TestCase):
    def test_transfer_direction_java(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"TransferLabelCheck.java"
            source.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,str(JAVA/"TransferLabel.java"),
                str(source)],check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.TransferLabelCheck"],
                check=True,capture_output=True,text=True)

    def test_disconnect_and_radio_loss_cancel_sender(self):
        code=(JAVA/"TransferService.java").read_text(encoding="utf-8")
        self.assertIn('if(DISCONNECT_PEER.equals(action)){\n            engine.cancelSending();',code)
        self.assertIn('if(STOP.equals(action)){\n            engine.cancelSending();',code)
        self.assertIn('if(isSending&&!senderWifiLost&&!WifiState.localTransferReady',code)
        self.assertIn('peerAttempts.next();peerVerified=false;',code)

    def test_worker_rejection_recovers_ui_state(self):
        code=(JAVA/"TransferService.java").read_text(encoding="utf-8")
        self.assertIn('catch(RejectedExecutionException rejected)',code)
        self.assertIn('isSending=false;isBusy=false;busy.set(false);',code)

    def test_queue_serialization_is_all_or_nothing(self):
        code=(JAVA/"FileCatalog.java").read_text(encoding="utf-8")
        self.assertIn('throw new IllegalStateException("Не удалось сохранить очередь целиком"',code)
        self.assertIn('.putString("list",snapshot).putString("list_mirror",snapshot).commit()',code)
        self.assertIn('JSONArray j=new JSONArray(mirror)',code)
        self.assertIn('if(!Files.isReadable(child))',code)

if __name__=="__main__":unittest.main()
