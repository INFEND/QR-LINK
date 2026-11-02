"""Unix FTP listings must exclude symlinks, pipes and device nodes."""
from pathlib import Path
import subprocess
import tempfile
import unittest

JAVA=Path(__file__).resolve().parents[1]/"app/src/main/java/dev/xarkon/link"
HARNESS=r'''package dev.xarkon.link;
public final class FtpUnixTypesCheck {
    static void check(boolean ok){if(!ok)throw new AssertionError("FTP type");}
    public static void main(String[] args){
        check(FtpListingReader.supportedUnixType("-rw-r--r--"));
        check(FtpListingReader.supportedUnixType("drwxr-xr-x+"));
        check(FtpListingReader.supportedUnixType("-rwxr-Sr-T@"));
        check(FtpListingReader.supportedUnixType("----------"));
        for(String s:new String[]{"lrwxrwxrwx","crw-rw----","brw-rw----",
            "prw-------","srwxrwxrwx","garbage","","drwxr-xr?"})
            check(!FtpListingReader.supportedUnixType(s));
        check(!FtpListingReader.supportedUnixType(null));
    }
}
'''

class FtpUnixTypesTests(unittest.TestCase):
    def test_unix_type_jvm(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness=Path(tmp)/"FtpUnixTypesCheck.java"
            harness.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,
                str(JAVA/"FtpListingReader.java"),str(harness)],
                check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.FtpUnixTypesCheck"],
                check=True,capture_output=True,text=True)

    def test_ftp_browser_uses_type_guard(self):
        src=(JAVA/"FtpBridge.java").read_text(encoding="utf-8")
        self.assertIn("if(!FtpListingReader.supportedUnixType(fields[0]))continue;",src)
        self.assertLess(src.index("supportedUnixType(fields[0])"),
                        src.index("result.add(new Entry(name,isDir,size));"))
