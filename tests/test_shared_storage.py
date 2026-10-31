"""Source-level safeguards for the opt-in shared storage browser.

These checks catch accidental removal of permission gating and path traversal
protection; they are not Android instrumentation or device tests.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BROWSER = ROOT / "app/src/main/java/dev/xarkon/link/FileBrowserActivity.java"
CATALOG = ROOT / "app/src/main/java/dev/xarkon/link/FileCatalog.java"
MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"

class SharedStorageContract(unittest.TestCase):
    def test_explicit_permission_gate(self):
        browser = BROWSER.read_text(encoding="utf-8")
        manifest = MANIFEST.read_text(encoding="utf-8")
        self.assertIn("Environment.isExternalStorageManager()", browser)
        self.assertIn("ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION", browser)
        self.assertIn("РАЗРЕШИТЬ ДОСТУП К ВНУТРЕННЕЙ ПАМЯТИ", browser)
        self.assertIn("android.permission.MANAGE_EXTERNAL_STORAGE", manifest)

    def test_local_folder_boundary_and_symlink_protection(self):
        browser = BROWSER.read_text(encoding="utf-8")
        catalog = CATALOG.read_text(encoding="utf-8")
        self.assertIn("Files.isSymbolicLink(child)", browser)
        self.assertIn("Files.isSymbolicLink(child)", catalog)
        self.assertIn("rootPath+File.separator", browser)
        self.assertIn("base.getPath()+File.separator", catalog)
        self.assertIn("MAX_FOLDER_FILES", catalog)
        self.assertIn("DirectoryStream<Path>", browser)
        self.assertIn("DirectoryStream<Path>", catalog)

    def test_local_folder_selection_and_saf_fallback(self):
        browser = BROWSER.read_text(encoding="utf-8")
        self.assertIn("FileCatalog.fromLocalFolder(this,e.localFile,e.path)", browser)
        self.assertIn("FileCatalog.fromDocumentFolder(", browser)
        self.assertIn("getPersistedUriPermissions()", browser)

if __name__ == "__main__":
    unittest.main()
