"""November browser regression checks for the next bundled release."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"

class November79Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser=(JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
        cls.main=(JAVA/"MainActivity.java").read_text(encoding="utf-8")
        cls.icons=(JAVA/"UiIcon.java").read_text(encoding="utf-8")
        cls.notes=(JAVA/"ReleaseNotes.java").read_text(encoding="utf-8")

    def test_sort_is_saved_per_category(self):
        self.assertIn('"browser_sort_"+tab',self.browser)
        self.assertIn('"browser_sort_"+index',self.browser)
        self.assertIn('getInt("browser_sort_"+index,0)',self.browser)

    def test_sort_button_in_header_not_search_bar(self):
        start=self.browser.index("private void buildUi()")
        top=self.browser.index("root.addView(top)",start)
        tools=self.browser.index("LinearLayout tools=",top)
        self.assertIn("top.addView(sortButton",self.browser[start:top])
        self.assertNotIn("tools.addView(sortButton",self.browser[tools:])

    def test_hidden_items_filtered_in_all_browsers(self):
        self.assertIn('"browser_show_hidden",false',self.browser)
        self.assertIn('"browser_show_hidden",false',self.main)
        self.assertIn("previousHiddenPreference!=showHiddenFiles()",self.browser)
        self.assertIn("hiddenPath(name)||hiddenPath(path)",self.browser)
        self.assertIn("hiddenPath(e.name)",self.browser)

    def test_folder_summary_has_real_size_and_accent(self):
        self.assertIn("folder.mediaBytes=unknown?-1:bytes",self.browser)
        self.assertIn('"Файлов: "+(e.mediaFolder&&!mediaTruncated?',self.browser)
        self.assertIn('" | Размер: "+(e.mediaFolder&&!mediaTruncated&&e.mediaBytes>=0?',self.browser)
        self.assertIn("int countStart=",self.browser)

    def test_breadcrumb_and_long_names(self):
        self.assertIn('breadcrumb().replace(" › "," > ")',self.browser)
        self.assertIn("crumb.setSpan(new ForegroundColorSpan(accent)",self.browser)
        self.assertIn("new LoopingNameView(this)",self.browser)
        scrolling=(JAVA/"LoopingNameView.java").read_text(encoding="utf-8")
        self.assertIn("ValueAnimator.ofFloat(0f,0f,1f,1f,0f)",scrolling)
        self.assertIn("ValueAnimator.INFINITE",scrolling)

    def test_animated_folder_chevrons(self):
        self.assertIn('new UiIcon(this,"chevron",accent)',self.browser)
        self.assertIn("arrow.animate().rotation(target)",self.browser)
        self.assertNotIn('?"⌄":"›"',self.browser)

    def test_selection_plural_and_unknown_size(self):
        self.assertIn("private static String russianCount(",self.browser)
        self.assertIn('russianCount(files,"файл","файла","файлов")',self.browser)
        self.assertIn('russianCount(folders,"папка","папки","папок")',self.browser)
        self.assertIn("BrowserSelectionTotals.sum(entries,folderSizeSnapshots)",self.browser)
        self.assertIn("if(e.folder&&selected.containsKey(key))requestFolderSize(e);",self.browser)
        self.assertIn('total.provisional?"≈ ":"',self.browser)
        self.assertNotIn('folders>0||unknown>0?"неизвестен"',self.browser)

    def test_settings_icon_and_about_screen(self):
        self.assertIn('String[] glyphs={"file","image","text_image"}',self.main)
        self.assertIn('case "text_image":',self.icons)
        self.assertIn("Передавайте фотографии, видео, музыку и документы",self.main)
        self.assertIn("Передача не зашифрована",self.main)
        self.assertNotIn("Нативные протоколы SHAREit",self.main)

    def test_release_notes_not_cut_off(self):
        self.assertNotIn("out.length()+line.length()+1>6000",self.notes)
        script=(ROOT/"scripts/make_manifest.py").read_text(encoding="utf-8")
        self.assertIn("MIN_NEW_RELEASE_CHANGES = 10",script)
        self.assertIn("MAX_RELEASE_NOTES_CHARS = 100_000",script)
        manager=(JAVA/"UpdateManager.java").read_text(encoding="utf-8")
        self.assertIn("notes.length()>100_000",manager)
        self.assertIn("memory.size()+n>512*1024",manager)

if __name__=="__main__":unittest.main()
