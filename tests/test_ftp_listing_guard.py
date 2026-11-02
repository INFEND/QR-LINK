"""FTP directory listings are bounded and reject dangerous remote file names."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "app/src/main/java/dev/xarkon/link"
HARNESS = r'''package dev.xarkon.link;
import java.io.*;
public final class FtpListingReaderCheck {
    static void badLine(String line) throws Exception {
        try { FtpListingReader.readLine(new StringReader(line)); throw new AssertionError("Accepted unsafe listing line"); }
        catch(IOException expected) {}
    }
    static void check(boolean condition) { if(!condition) throw new AssertionError(); }
    public static void main(String[] args) throws Exception {
        StringReader input = new StringReader("drwxr-xr-x owner 4 Jan 01 2026 folder\\r\\nfile without final newline");
        check(FtpListingReader.readLine(input).endsWith("folder"));
        check(FtpListingReader.readLine(input).equals("file without final newline"));
        check(FtpListingReader.readLine(input) == null);
        check(FtpListingReader.readLine(new StringReader("")) == null);
        check(FtpListingReader.readLine(new StringReader("x".repeat(4096) + "\\n")).length() == 4096);
        badLine("x".repeat(4097) + "\\n");
        badLine("file\\0name\\n");
        badLine("file\\u0001name\\n");
        check(FtpListingReader.safeName("Новый файл 2026.jpg"));
        for (String name : new String[]{"", ".", "..", "../file", "sub\\\\file", "bad\\rname", "bad\\u202ename", "bad\\u2066name"})
            check(!FtpListingReader.safeName(name));
        FtpListingReader.requireCapacity(99999);
        try { FtpListingReader.requireCapacity(100000); throw new AssertionError("No limit"); }
        catch(IOException expected) {}
    }
}
'''

class FtpListingGuardTests(unittest.TestCase):
    def test_bounded_ftp_listing_jvm(self):
        with tempfile.TemporaryDirectory() as work:
            harness = Path(work) / "FtpListingReaderCheck.java"
            harness.write_text(HARNESS, encoding="utf-8")
            subprocess.run(["javac", "-encoding", "UTF-8", "-d", work,
                str(JAVA / "FtpListingReader.java"), str(harness)],
                check=True, capture_output=True, text=True)
            subprocess.run(["java", "-cp", work, "dev.xarkon.link.FtpListingReaderCheck"],
                check=True, capture_output=True, text=True)

    def test_listing_and_download_use_guard(self):
        source = (JAVA / "FtpBridge.java").read_text(encoding="utf-8")
        self.assertIn("while((line=FtpListingReader.readLine(r))!=null)", source)
        self.assertGreaterEqual(source.count("FtpListingReader.requireCapacity(result.size())"), 2)
        self.assertIn("if(!FtpListingReader.safeName(name))continue;", source)
        self.assertIn("if(FtpListingReader.safeName(name)){", source)
        self.assertIn('if(!FtpListingReader.safeName(file))throw new IOException("Неверное имя файла FTP");', source)
        self.assertIn('if(!FtpListingReader.safeName(segment))throw new IOException("Некорректный путь");', source)

if __name__ == "__main__":
    unittest.main()
