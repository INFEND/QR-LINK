"""Regression guards for the November browser and diagnostics improvements."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"

class NovemberUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser=(JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
        cls.main=(JAVA/"MainActivity.java").read_text(encoding="utf-8")
        cls.recovery=(JAVA/"RecoveryActivity.java").read_text(encoding="utf-8")
        cls.breadcrumbs=(JAVA/"BrowserBreadcrumbs.java").read_text(encoding="utf-8")

    def test_folder_icons_never_use_media_covers(self):
        self.assertIn('String glyph=e.folder?"folder":',self.browser)
        self.assertIn('View centeredContent=e.uri!=null&&!e.folder?',self.browser)
        self.assertIn('if(!e.folder&&(tab==0||tab==1||tab==2||tab==3))addPreview',self.browser)

    def test_only_first_media_folder_opens_and_selection_survives(self):
        self.assertIn('Collections.sort(grouped.folders',self.browser)
        self.assertIn('Entry first=grouped.folders.get(0)',self.browser)
        self.assertIn('expandedFolders.add(first.key())',self.browser)
        self.assertIn('if(e.mediaFolder){',self.browser)
        self.assertIn('expandedFolders.remove(previous)',self.browser)
        self.assertIn('openedFolders.remove(previous)',self.browser)
        self.assertIn('selected.put(folder.key(),folder)',self.browser)

    def test_file_metadata_no_mime_and_accent_size(self):
        self.assertIn('"Размер: "+(e.size<0?"неизвестен":Util.readable(e.size))',self.browser)
        self.assertIn('if(!e.folder){\n                SpannableStringBuilder rich=',self.browser)
        self.assertIn('new ForegroundColorSpan(accent)',self.browser)

    def test_device_title_not_filesystem_root(self):
        self.assertIn('new StringBuilder("Устройство")',self.breadcrumbs)
        self.assertIn('if(focus==null)return "Устройство"',self.browser)
        self.assertNotIn('ПОКАЗАТЬ КОРЕНЬ /0',self.browser)

    def test_selection_labels_and_immediate_queue_clear(self):
        self.assertIn('action=label("ПОДТВЕРДИТЬ"',self.browser)
        self.assertIn('action.setText("ПОДТВЕРДИТЬ")',self.browser)
        self.assertIn('СНЯТЬ ВЫДЕЛЕННОЕ',self.browser)
        self.assertIn('FileCatalog.save(this,new ArrayList<>())',self.main)
        self.assertNotIn('setTitle("Очистить очередь?")',self.main)
        self.assertIn('if(TransferService.isSending)',self.main)

    def test_about_dynamic_version_and_accent(self):
        self.assertIn('section("about","О приложении"',self.main)
        self.assertIn('text("QR LINK v"+getAppVersion()',self.main)
        self.assertIn('versionStyle.setSpan(',self.main)
        self.assertNotIn('Информация и безопасность',self.main)

    def test_recovery_uses_red_and_short_label(self):
        self.assertIn('accent=0xffd65a63',self.recovery)
        self.assertIn('button(c,"Безопасный запуск",false',self.recovery)
        self.assertNotIn('тема без анимаций',self.recovery)

    def test_palette_has_no_variant_count(self):
        self.assertIn('text("АКЦЕНТНЫЙ ЦВЕТ",11,muted,true)',self.main)
        self.assertNotIn('+" ВАРИАНТА"',self.main)

if __name__=="__main__":
    unittest.main()
