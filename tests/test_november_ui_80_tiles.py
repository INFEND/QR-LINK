"""Follow-up UI safeguards for the user-requested file browser tile and preview flows."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"

class TileAndPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser=(JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
        cls.provider=(JAVA/"PreviewProvider.java").read_text(encoding="utf-8")
        cls.manifest=(ROOT/"app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")

    def test_per_category_mode_and_default_media_tiles(self):
        self.assertIn('"browser_tile_"+tab,tab==0||tab==1',self.browser)
        self.assertIn('putBoolean("browser_tile_"+tab,tiles)',self.browser)

    def test_grid_is_bounded_to_two_through_five_columns(self):
        self.assertIn('Math.max(2,Math.min(5,',self.browser)
        self.assertIn('int columns=progress+2;',self.browser)

    def test_folder_stays_list_and_tile_checkbox_is_inside(self):
        self.assertIn('if(tileMode()&&!entry.folder)drawTile(entry);',self.browser)
        self.assertIn('tile.addView(check,checkLp);',self.browser)
        self.assertIn('Gravity.TOP|Gravity.END',self.browser)

    def test_list_size_persists_per_category(self):
        self.assertIn('putInt("browser_list_scale_"+tab,value)',self.browser)
        self.assertIn('row.setPadding(dp(12+Math.min(7,depth)*10),dp(11*scale/100f)',self.browser)

    def test_preview_is_separate_from_selection(self):
        self.assertIn('frame.setOnClickListener(v->openPreview(entry))',self.browser)
        self.assertIn('if(e==null||e.folder||tab==3||e.uri==null)return;',self.browser)
        self.assertIn('Intent.FLAG_GRANT_READ_URI_PERMISSION',self.browser)

    def test_local_preview_provider_is_private_and_read_only(self):
        self.assertIn('android:exported="false" android:grantUriPermissions="true"',self.manifest)
        self.assertIn('android:name=".PreviewProvider"',self.manifest)
        self.assertIn('target.getPath().startsWith(root.getPath()+File.separator)',self.provider)
        self.assertIn('if(!"r".equals(mode))',self.provider)

if __name__=="__main__":
    unittest.main()
