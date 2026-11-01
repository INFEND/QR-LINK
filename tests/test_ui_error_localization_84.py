"""User-visible errors must not concatenate raw Java/OEM exception messages."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
HARNESS=r'''package dev.xarkon.link;
import java.io.IOException;
public class ErrorTextUiCheck {
    public static void main(String[] args){
        String generic=ErrorText.human(new IOException("OEM driver HAL 0x0ab failure"));
        if(generic.contains("HAL")||generic.contains("0x0ab"))
            throw new AssertionError("Raw OEM message leaked");
        String denied=ErrorText.human(new IOException("permission denied"));
        if(!denied.contains("разрешен"))throw new AssertionError("Permissions not localized");
        String russian=ErrorText.human(new IOException("Папка недоступна"));
        if(!russian.equals("Папка недоступна"))
            throw new AssertionError("Useful Russian error lost");
    }
}
'''

class ErrorLocalization84(unittest.TestCase):
    def test_ui_catches_use_sanitized_errors(self):
        browser=(JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
        scanner=(JAVA/"QrScannerActivity.java").read_text(encoding="utf-8")
        background=(JAVA/"BackgroundUpdateJob.java").read_text(encoding="utf-8")
        self.assertIn("showBanner(ErrorText.human(e),true)",browser)
        self.assertNotIn('ErrorText.human("Ошибка: "+e.getMessage())',browser)
        self.assertIn('"Камера недоступна. "+ErrorText.human(e)',scanner)
        self.assertIn('"Неверный QR: "+ErrorText.human(e)',scanner)
        self.assertNotIn('notice.setText("Неверный QR: "+e.getMessage())',scanner)
        self.assertIn("String message=ErrorText.human(error);",background)
        self.assertNotIn("String message=error.getMessage();",background)

    def test_error_mapper_rejects_oem_details(self):
        with tempfile.TemporaryDirectory() as work:
            harness=Path(work)/"ErrorTextUiCheck.java"
            harness.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",work,
                str(JAVA/"ErrorText.java"),str(harness)],
                check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",work,"dev.xarkon.link.ErrorTextUiCheck"],
                check=True,capture_output=True,text=True)
