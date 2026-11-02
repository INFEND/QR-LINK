from pathlib import Path
import unittest
SRC=Path(__file__).resolve().parents[1]/"app/src/main/java/dev/xarkon/link/FtpBridge.java"
class FtpSocketCleanupTests(unittest.TestCase):
    def test_failed_login_closes_control_socket(self):
        code=SRC.read_text(encoding="utf-8")
        section=code[code.index("public FtpBridge("):code.index("private String last;")]
        self.assertIn("}catch(Exception failure){",section)
        self.assertIn("try{control.close();}catch(IOException ignored){}",section)
        self.assertLess(section.index("expectResult(send(\"TYPE I\"));"),section.index("}catch(Exception failure){"))
if __name__=="__main__":
    unittest.main()
