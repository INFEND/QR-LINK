"""Real JVM regression tests for safe FTP passive-mode responses."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
HARNESS=r'''package dev.xarkon.link;
import java.io.IOException;
public final class FtpPassiveReplyCheck {
    private static void eq(int expected,int actual){
        if(expected!=actual)throw new AssertionError(expected+" != "+actual);
    }
    private static void bad(boolean epsv,String reply){
        try{
            if(epsv)FtpPassiveReply.epsvPort(reply);
            else FtpPassiveReply.pasvPort(reply);
            throw new AssertionError("Malformed passive reply accepted: "+reply);
        }catch(IOException expected){}
    }
    public static void main(String[] args)throws Exception {
        eq(6446,FtpPassiveReply.epsvPort("229 Entering Extended Passive Mode (|||6446|)"));
        eq(12345,FtpPassiveReply.epsvPort("229 (!!!12345!)"));
        eq(1930,FtpPassiveReply.pasvPort("227 Entering Passive Mode (192,168,1,3,7,138)"));
        eq(65535,FtpPassiveReply.pasvPort("227 ( 10, 0, 0, 1, 255, 255 )"));
        for(String x:new String[]{"229 (|||0|)","229 (|||65536|)","229 (|||12x|)",
            "229 (|1|)","229 (|||1)","229 (||||)","229 ()","229 no port"})
            bad(true,x);
        for(String x:new String[]{"227 (1,2,3,4,5)","227 (1,2,3,4,0,0)",
            "227 (1,2,3,4,256,1)","227 (1,2,3,4,-1,2)",
            "227 (1,2,3,4,1,1,9)","227 (1,2,3,4,1,x)","227 ()"})
            bad(false,x);
    }
}
'''

class FtpPassiveReplyTests(unittest.TestCase):
    def test_passive_ports_jvm(self):
        with tempfile.TemporaryDirectory() as work:
            harness=Path(work)/"FtpPassiveReplyCheck.java"
            harness.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",work,
                str(JAVA/"FtpPassiveReply.java"),str(harness)],
                check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",work,"dev.xarkon.link.FtpPassiveReplyCheck"],
                check=True,capture_output=True,text=True)

    def test_ftp_download_requires_android_publication(self):
        source=(JAVA/"FtpBridge.java").read_text(encoding="utf-8")
        self.assertIn("FtpPassiveReply.epsvPort(last)",source)
        self.assertIn("FtpPassiveReply.pasvPort(last)",source)
        self.assertIn("if(context.getContentResolver().update(dst,publish,null,null)!=1)",source)
        self.assertIn("Не удалось опубликовать загруженный FTP-файл",source)

if __name__=="__main__":unittest.main()
