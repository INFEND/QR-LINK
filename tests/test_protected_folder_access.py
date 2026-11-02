"""Regression: protected Android folders must fail honestly, never invent totals."""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"

class ProtectedFolderAccessTests(unittest.TestCase):
    def test_android_data_error_is_localized_and_not_a_false_bypass(self):
        harness=r"""package dev.xarkon.link;
import java.nio.file.AccessDeniedException;
import java.io.IOException;
public final class ProtectedFolderCheck {
    static void yes(boolean value){if(!value)throw new AssertionError("Folder access policy");}
    public static void main(String[] args){
        Throwable denied=new AccessDeniedException("/storage/emulated/0/Android/data");
        yes(BrowserFolderAccess.denied(denied));
        yes(BrowserFolderAccess.protectedAndroidPath("Android/data"));
        yes(BrowserFolderAccess.protectedAndroidPath("Android/data/com.example"));
        yes(BrowserFolderAccess.protectedAndroidPath("Android\\obb"));
        yes(!BrowserFolderAccess.protectedAndroidPath("Download/data"));
        yes(!BrowserFolderAccess.protectedAndroidPath("Android/database"));
        yes(!BrowserFolderAccess.protectedAndroidPath("data"));
        String protectedMessage=BrowserFolderAccess.message("Android/data",denied);
        yes(protectedMessage.contains("Android/data")&&protectedMessage.contains("«Все файлы»"));
        yes(!BrowserFolderAccess.message("Download/data",denied).contains("Android/obb"));
        yes(!BrowserFolderAccess.denied(new IOException("disk read error")));
        yes(!BrowserFolderAccess.message("Android/data",new IOException("disk read error"))
            .contains("ограничивает доступ"));
    }
}
"""
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"ProtectedFolderCheck.java"
            source.write_text(harness,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",temp,
                str(JAVA/"BrowserFolderAccess.java"),str(source)],
                check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",temp,"dev.xarkon.link.ProtectedFolderCheck"],
                check=True,capture_output=True,text=True)

    def test_async_failure_and_permission_change_refresh(self):
        source=(JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
        self.assertIn("if(!Files.isReadable(folder.toPath()))",source)
        self.assertIn("showBanner(BrowserFolderAccess.message(e.path,error),true);",source)
        self.assertIn('return "Файлов: нет доступа | Размер: нет доступа";',source)
        self.assertIn("invalidateFolderStats();",source)
        self.assertIn("if(epoch!=folderStatsEpoch)return;",source)
        self.assertIn("folderSizeSnapshots.clear();",source)
        self.assertIn("folderAccessErrors.clear();",source)
        self.assertIn("folderStatsIo=Executors.newFixedThreadPool(2)",source)

if __name__=="__main__":
    unittest.main()
