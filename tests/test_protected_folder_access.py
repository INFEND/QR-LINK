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
        // Canonicalized relative and absolute paths must agree.
        yes(BrowserFolderAccess.protectedAndroidPath("Android/./data"));
        yes(BrowserFolderAccess.protectedAndroidPath("Android/media/../data"));
        yes(BrowserFolderAccess.protectedAndroidPath("Android/data/../obb"));
        yes(BrowserFolderAccess.protectedAndroidPath("/storage/emulated/0/Android/data"));
        yes(BrowserFolderAccess.protectedAndroidPath("/0/Android/obb/com.example"));
        yes(BrowserFolderAccess.protectedAndroidPath("/sdcard/Android/data"));
        yes(!BrowserFolderAccess.protectedAndroidPath("Android/data/../media"));
        yes(!BrowserFolderAccess.protectedAndroidPath("Android/data/../../Download/data"));
        yes(!BrowserFolderAccess.protectedAndroidPath("../Android/data"));
        yes(!BrowserFolderAccess.protectedAndroidPath("/storage/emulated/10/Android/data"));
        yes(!BrowserFolderAccess.protectedAndroidPath("DCIM/data"));
        yes(!BrowserFolderAccess.protectedAndroidPath("Documents/data/subfolder"));
        yes(!BrowserFolderAccess.protectedAndroidPath("Android/databases"));
        String protectedMessage=BrowserFolderAccess.message("Android/data",denied);
        yes(protectedMessage.equals("Нет доступа к системной папке Android. Android ограничивает просмотр её содержимого."));
        yes(BrowserFolderAccess.message("Android/obb",denied).equals(protectedMessage));
        yes(BrowserFolderAccess.denied(new SecurityException("Permission denied")));
        yes(BrowserFolderAccess.denied(new IOException("Permission denied")));
        yes(BrowserFolderAccess.denied(new IOException("Недоступный элемент папки")));
        yes(BrowserFolderAccess.denied(new IOException("Нет доступа к дочернему файлу")));
        yes(BrowserFolderAccess.denied(new IOException("Каталог недоступен")));
        yes(BrowserFolderAccess.denied(new IOException("provider failure",
            new SecurityException("access blocked"))));
        yes(BrowserFolderAccess.message("Android/./data",
            new IOException("Недоступный элемент папки")).equals(protectedMessage));
        yes(BrowserFolderAccess.message("Android/data/../media",
            new SecurityException("permission denied")).startsWith("Нет доступа к папке."));
        try{BrowserFolderAccess.requireVisibleEvidence("Android/./data",35,0);
            throw new AssertionError("Dot segment bypassed protected storage");
        }catch(AccessDeniedException expected){}
        try{BrowserFolderAccess.requireVisibleEvidence("Android/data/../media",35,0);
            BrowserFolderAccess.requireVisibleEvidence("Documents/data",35,0);
        }catch(AccessDeniedException unexpected){throw new AssertionError(unexpected);}
        try{BrowserFolderAccess.requireVisibleEvidence("Android/data",30,0);
            throw new AssertionError("Protected empty listing was trusted");
        }catch(AccessDeniedException expected){}
        try{BrowserFolderAccess.requireVisibleEvidence("Android/obb",35,0);
            throw new AssertionError("Protected obb listing was trusted");
        }catch(AccessDeniedException expected){}
        try{BrowserFolderAccess.requireVisibleEvidence("Download/data",35,0);
            BrowserFolderAccess.requireVisibleEvidence("Android/database",35,0);
            BrowserFolderAccess.requireVisibleEvidence("Android/data",29,0);
            BrowserFolderAccess.requireVisibleEvidence("Android/data",35,1);
        }catch(AccessDeniedException unexpected){throw new AssertionError(unexpected);}
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

    def test_recursive_transfer_rejects_silent_android_data_filtering(self):
        source=(JAVA/"FileCatalog.java").read_text(encoding="utf-8")
        self.assertIn("int observedChildren=0;",source)
        self.assertIn("observedChildren++;",source)
        self.assertIn("BrowserFolderAccess.requireVisibleEvidence(relative,Build.VERSION.SDK_INT,observedChildren);",source)
        # Selection must fail closed even when Android returns an empty listing,
        # not send an empty/partial queue as a successful transfer.
        self.assertLess(source.index("observedChildren++;"),
                        source.index("BrowserFolderAccess.requireVisibleEvidence(relative,Build.VERSION.SDK_INT,observedChildren);"))

    def test_async_failure_and_permission_change_refresh(self):
        source=(JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
        self.assertIn("if(!Files.isReadable(folder.toPath()))",source)
        self.assertIn("showBanner(BrowserFolderAccess.message(e.path,error),true);",source)
        self.assertIn('return "Файлов: Нет доступа | Размер: Нет доступа";',source)
        self.assertIn("BrowserFolderAccess.requireVisibleEvidence(parent,Build.VERSION.SDK_INT,scanned);",source)
        self.assertIn("BrowserFolderAccess.requireVisibleEvidence(folder.path,Build.VERSION.SDK_INT,stats.fileCount);",source)
        self.assertGreaterEqual(source.count("BrowserFolderAccess.requireVisibleEvidence(folder.path,Build.VERSION.SDK_INT,stats.fileCount);"),2)
        self.assertIn("BrowserFolderCardStats stats=BrowserFolderCardStats.scanDocuments(",source)
        self.assertIn('UiConfirmDialog.showInfo(this,"Нет доступа к папке"',source)
        dialog=(JAVA/"UiConfirmDialog.java").read_text(encoding="utf-8")
        self.assertIn('return showInternal(a,title,message,"ПОНЯТНО",null,true);',dialog)
        self.assertIn("if(!infoOnly)buttons.addView(cancel",dialog)
        self.assertIn('infoOnly?new UiIcon(a,"close",accent)',dialog)
        self.assertIn("invalidateFolderStats();",source)
        self.assertIn("if(epoch!=folderStatsEpoch)return;",source)
        self.assertIn("folderSizeSnapshots.clear();",source)
        self.assertIn("folderAccessErrors.clear();",source)
        self.assertIn("folderStatsIo=Executors.newFixedThreadPool(2)",source)

if __name__=="__main__":
    unittest.main()
