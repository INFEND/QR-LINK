"""Static regression guardrails for QR LINK's permission-aware in-app browser."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BROWSER = ROOT / "app/src/main/java/dev/xarkon/link/FileBrowserActivity.java"
MAIN = ROOT / "app/src/main/java/dev/xarkon/link/MainActivity.java"


class BrowserUiTests(unittest.TestCase):
    def test_themed_sort_and_system_bars(self):
        src = BROWSER.read_text(encoding="utf-8")
        self.assertIn("showSortDialog()", src)
        self.assertNotIn("new PopupMenu(", src)
        self.assertIn("setDecorFitsSystemWindows(false)", src)
        self.assertIn("WindowInsets.Type.statusBars()", src)
        self.assertIn("WindowInsets.Type.navigationBars()", src)

    def test_inline_expansion_cancels_stale_queries(self):
        src = BROWSER.read_text(encoding="utf-8")
        self.assertIn("row.setOnClickListener(v->{if(e.folder)expandFolder(e)", src)
        self.assertIn("final CancellationSignal signal=new CancellationSignal()", src)
        self.assertIn("if(expansionSignals.get(key)!=signal)return;", src)
        self.assertIn("incompleteFolders.add(key)", src)
        self.assertIn("FileCatalog.fromDocumentFolder(", src)

    def test_search_style_and_apk_metadata(self):
        src = BROWSER.read_text(encoding="utf-8")
        for phrase in ("Поиск по картинкам", "Поиск по видео",
                       "Поиск по музыке", "Поиск по приложениям", "Поиск по файлам"):
            self.assertIn(phrase, src)
        self.assertIn('e.version=pkgInfo.versionName', src)
        self.assertIn('it.name=Util.safeName(tab==3', src)
        self.assertIn('sub="Размер: "+Util.readable(e.size)+" | Версия: "+e.version', src)
        self.assertIn('addWide("СИСТЕМНЫЙ ПРОВОДНИК"', src)
        self.assertIn('if(!filter.isEmpty())rows.removeIf', src)
        settings = MAIN.read_text(encoding="utf-8")
        self.assertIn('"browser_style"', settings)
        self.assertIn('"Текст","Иконки","Текст и иконки"', settings)


if __name__ == "__main__":
    unittest.main()
