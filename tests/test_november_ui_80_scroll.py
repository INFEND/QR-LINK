"""Regression guards for scrollable breadcrumbs and readable looping file names."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
class BrowserScrollingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser=(JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
        cls.names=(JAVA/"LoopingNameView.java").read_text(encoding="utf-8")
    def test_breadcrumbs_scroll_to_last_segment(self):
        self.assertIn('pathScroller=new HorizontalScrollView(this)',self.browser)
        self.assertIn('pathScroller.fullScroll(View.FOCUS_RIGHT)',self.browser)
        self.assertIn('subtitle.setEllipsize(null)',self.browser)
    def test_names_are_animated_in_both_views(self):
        self.assertGreaterEqual(self.browser.count('new LoopingNameView(this)'),2)
        self.assertIn('ValueAnimator.ofFloat(0f,0f,1f,1f,0f)',self.names)
        self.assertIn('motion.setRepeatCount(ValueAnimator.INFINITE)',self.names)
    def test_animation_stops_on_detach_and_avoids_restart(self):
        self.assertIn('if(overflow==previousWidth&&motion!=null&&motion.isRunning())return;',self.names)
        self.assertIn('onDetachedFromWindow()',self.names)
        self.assertIn('motion.cancel()',self.names)
if __name__=="__main__":unittest.main()
