"""FTP replies must be bounded and remote diagnostic text must not leak to UI."""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"

HARNESS=r'''package dev.xarkon.link;
import java.io.*;
public final class FtpReplyReaderCheck {
 static FtpReplyReader.Reply read(String s)throws Exception {
  return FtpReplyReader.read(new BufferedReader(new StringReader(s)));
 }
 static void fails(String s)throws Exception {
  try{read(s);throw new AssertionError("Accepted invalid reply");}
  catch(IOException expected){}
 }
 public static void main(String[] args)throws Exception {
  if(read("220 Service ready\r\n").code!=220)throw new AssertionError("Single line");
  FtpReplyReader.Reply multi=read("220-First\r\ntext\r\n221 other\r\n220 Final\r\n");
  if(multi.code!=220||!multi.lastLine.equals("220 Final"))throw new AssertionError("Multiline");
  fails("garbage\r\n");
  fails("220?No separator\r\n");
  fails("220-First\r\n221 End\r\n");
  fails("220 "+"x".repeat(4097)+"\r\n");
  StringBuilder b=new StringBuilder("220-First\r\n");
  for(int i=0;i<64;i++)b.append("220-Continue\r\n");
  fails(b.toString());
  fails("220 ok\0unsafe\r\n");
 }
}
'''

class FtpReplyGuardTests(unittest.TestCase):
    def test_strict_bounded_ftp_replies(self):
        with tempfile.TemporaryDirectory() as work:
            source=Path(work)/"FtpReplyReaderCheck.java"
            source.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",work,
                str(JAVA/"FtpReplyReader.java"),str(source)],
                check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",work,"dev.xarkon.link.FtpReplyReaderCheck"],
                check=True,capture_output=True,text=True)

    def test_ftp_ui_does_not_show_remote_server_banner(self):
        source=(JAVA/"FtpBridge.java").read_text(encoding="utf-8")
        self.assertIn("FtpReplyReader.read(reader)",source)
        self.assertIn("throw serverFailure(code)",source)
        self.assertIn("throw serverFailure(n)",source)
        self.assertNotIn('+" "+last',source)
        self.assertNotIn('": "+last',source)

if __name__=="__main__":
    unittest.main()
