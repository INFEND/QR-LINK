"""FTP SIZE may be unsupported, but a declared size must be checked."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
HARNESS=r'''package dev.xarkon.link;
import java.io.IOException;
public final class FtpSizeCheck {
    static void ok(boolean v){if(!v)throw new AssertionError();}
    static void bad(String s)throws Exception{
        try{FtpSizeReply.expectedBytes(213,s);throw new AssertionError();}
        catch(IOException expected){}
    }
    public static void main(String[] args)throws Exception{
        ok(FtpSizeReply.expectedBytes(213,"213 0")==0);
        ok(FtpSizeReply.expectedBytes(213,"213 123456789")==123456789L);
        ok(FtpSizeReply.expectedBytes(500,"500 Unsupported")==-1);
        ok(FtpSizeReply.expectedBytes(502,"502 Unsupported")==-1);
        bad(null);bad("213 -1");bad("213 10 bytes");
        bad("213 9223372036854775808");
    }
}
'''

class FtpSizeTests(unittest.TestCase):
    def test_parser_jvm(self):
        with tempfile.TemporaryDirectory() as work:
            harness=Path(work)/"FtpSizeCheck.java"
            harness.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",work,
                str(JAVA/"FtpSizeReply.java"),str(harness)],
                check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",work,"dev.xarkon.link.FtpSizeCheck"],
                check=True,capture_output=True,text=True)

    def test_download_checks_before_publishing(self):
        src=(JAVA/"FtpBridge.java").read_text(encoding="utf-8")
        body=src[src.index("public Uri download("):src.index("@Override public void close()")]
        self.assertLess(body.index('send("SIZE "+file)'),body.index("MediaStore.Downloads.IS_PENDING,1"))
        self.assertLess(body.index("if(expectedBytes>=0&&total!=expectedBytes)"),body.index("success=true;"))
        self.assertIn("context.getContentResolver().delete(dst,null,null)",body)

if __name__=="__main__":
    unittest.main()
