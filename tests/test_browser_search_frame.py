"""Search refresh must be frame-coalesced and cancel on Activity destruction."""
from pathlib import Path
import unittest

SOURCE=(Path(__file__).resolve().parents[1]/
        "app/src/main/java/dev/xarkon/link/FileBrowserActivity.java")

class SearchFrameTests(unittest.TestCase):
    def test_search_is_frame_coalesced(self):
        text=SOURCE.read_text(encoding="utf-8")
        block=text.split("search.addTextChangedListener(new TextWatcher()",1)[1].split(
            "scroll=new ScrollView",1)[0]
        self.assertIn("list.removeCallbacks(searchRefresh)",block)
        self.assertIn("list.postOnAnimation(searchRefresh)",block)
        self.assertNotIn("postDelayed(searchRefresh,45)",block)

    def test_search_callbacks_cancelled_on_destroy(self):
        text=SOURCE.read_text(encoding="utf-8")
        block=text.split("@Override protected void onDestroy()",1)[1]
        self.assertIn("list.removeCallbacks(searchRefresh)",block)
        self.assertIn("io.shutdownNow()",block)
