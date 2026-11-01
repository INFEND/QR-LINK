"""Guards for follow-up browser fixes after the v0.3.79 release."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"

class BrowserFollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser=(JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
        cls.icons=(JAVA/"UiIcon.java").read_text(encoding="utf-8")

    def test_sort_has_real_vector_icon(self):
        self.assertIn('sortButton=new UiIcon(this,"sort",accent)',self.browser)
        self.assertIn('case "sort":',self.icons)
        self.assertNotIn('sortButton=label("≡"',self.browser)

    def test_app_select_all_is_filtered_and_atomic(self):
        self.assertIn('index==3?"✓  ВЫБРАТЬ ВСЕ"',self.browser)
        start=self.browser.index('if(tab==3){\n            String filter=search.getText()')
        end=self.browser.index('Entry folder=focusedFolder()',start)
        block=self.browser[start:end]
        self.assertIn('if(app.folder||!app.name.toLowerCase(Locale.ROOT).contains(filter))continue;',block)
        self.assertIn('if(selected.size()+additions>MAX_QUEUE)',block)
        self.assertIn('for(Entry app:targets)selected.put(app.key(),app)',block)
        self.assertIn('updateCount()',block)

if __name__=="__main__":unittest.main()
