"""Stale FTP requests must not replace the newest directory or its error."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "app/src/main/java/dev/xarkon/link"
HARNESS = r'''package dev.xarkon.link;
public final class FtpRequestGuardCheck {
    static void check(boolean value) { if (!value) throw new AssertionError(); }
    public static void main(String[] args) {
        FtpRequestGuard guard = new FtpRequestGuard();
        long first = guard.begin();
        check(guard.isCurrent(first));
        long second = guard.begin();
        check(!guard.isCurrent(first));
        check(guard.isCurrent(second));
        guard.invalidate();
        check(!guard.isCurrent(second));
        long third = guard.begin();
        check(guard.isCurrent(third));
        check(!guard.isCurrent(first));
    }
}
'''

class FtpRequestGuardTests(unittest.TestCase):
    def test_request_generation_jvm(self):
        with tempfile.TemporaryDirectory() as work:
            harness = Path(work) / "FtpRequestGuardCheck.java"
            harness.write_text(HARNESS, encoding="utf-8")
            subprocess.run(["javac", "-encoding", "UTF-8", "-d", work,
                str(JAVA / "FtpRequestGuard.java"), str(harness)],
                check=True, capture_output=True, text=True)
            subprocess.run(["java", "-cp", work, "dev.xarkon.link.FtpRequestGuardCheck"],
                check=True, capture_output=True, text=True)

    def test_activity_checks_both_success_and_failure_callbacks(self):
        source = (JAVA / "MainActivity.java").read_text(encoding="utf-8")
        block = source[source.index("private void browseFtp(String dir)"):
                       source.index("private void updateQueue()")]
        self.assertIn("final long request=ftpRequests.begin();", block)
        self.assertEqual(block.count("ftpRequests.isCurrent(request)"), 2)
        self.assertIn("if(previous==FTP)ftpRequests.invalidate();", source)
        self.assertIn("ftpRequests.invalidate();\n        queueReader.shutdownNow();", source)

if __name__ == "__main__":
    unittest.main()
