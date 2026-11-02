"""FTP LIST with DOS/Windows dates must not fabricate file names."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "app/src/main/java/dev/xarkon/link"
HARNESS = r'''package dev.xarkon.link;
public final class FtpDosListingCheck {
    static void check(boolean ok) { if (!ok) throw new AssertionError(); }
    public static void main(String[] args) {
        FtpListingReader.ListedEntry folder =
            FtpListingReader.parseDosEntry("11-02-26  03:12PM       <DIR>          Camera Roll");
        check(folder != null && folder.directory && folder.size == -1 &&
              folder.name.equals("Camera Roll"));
        FtpListingReader.ListedEntry file =
            FtpListingReader.parseDosEntry("11-02-2026  03:12AM       12345          image file.jpg");
        check(file != null && !file.directory && file.size == 12345 &&
              file.name.equals("image file.jpg"));
        check(FtpListingReader.parseDosEntry("11-02-26 03:12PM <DIR> ../bad") == null);
        check(FtpListingReader.parseDosEntry("11-02-26 03:12PM 999999999999999999999 file") == null);
        check(FtpListingReader.parseDosEntry("11-02-26 03:12PM <DIR>") == null);
        check(FtpListingReader.looksLikeDosLine("11-02-26 03:12PM <DIR>"));
        check(!FtpListingReader.looksLikeDosLine("ordinary file.jpg"));
    }
}
'''

class FtpDosListingTests(unittest.TestCase):
    def test_dos_list_jvm(self):
        with tempfile.TemporaryDirectory() as work:
            harness = Path(work) / "FtpDosListingCheck.java"
            harness.write_text(HARNESS, encoding="utf-8")
            subprocess.run(["javac", "-encoding", "UTF-8", "-d", work,
                str(JAVA / "FtpListingReader.java"), str(harness)],
                check=True, capture_output=True, text=True)
            subprocess.run(["java", "-cp", work, "dev.xarkon.link.FtpDosListingCheck"],
                check=True, capture_output=True, text=True)

    def test_android_list_uses_dos_parser_before_unix_fallback(self):
        source = (JAVA / "FtpBridge.java").read_text(encoding="utf-8")
        self.assertLess(source.index("FtpListingReader.parseDosEntry(line)"),
                        source.index("String[]fields=line.trim().split"))
        self.assertIn("FtpListingReader.requireCapacity(result.size());", source)
        self.assertIn("if(FtpListingReader.looksLikeDosLine(line))continue;", source)

if __name__ == "__main__":
    unittest.main()
