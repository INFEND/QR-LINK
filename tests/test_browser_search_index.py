"""Large browser searches reuse their flattened index and animate height changes."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
HARNESS=r'''package dev.xarkon.link;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
public class BrowserSearchIndexCheck {
    static void assertTrue(boolean condition){if(!condition)throw new AssertionError();}
    public static void main(String[] args){
        BrowserSearchIndex<Integer> cache=new BrowserSearchIndex<>();
        AtomicInteger builds=new AtomicInteger();
        java.util.function.Supplier<ArrayList<Integer>> factory=()->{
            builds.incrementAndGet();
            ArrayList<Integer> rows=new ArrayList<>();
            for(int i=0;i<30000;i++)rows.add(i);
            return rows;
        };
        List<Integer> first=cache.get(0,true,factory);
        for(int i=0;i<20;i++)assertTrue(cache.get(0,true,factory)==first);
        assertTrue(builds.get()==1);
        assertTrue(cache.get(0,false,factory)!=first);
        assertTrue(builds.get()==2);
        cache.get(1,false,factory);
        assertTrue(builds.get()==3);
        cache.invalidate();
        cache.get(1,false,factory);
        assertTrue(builds.get()==4);
    }
}
'''

class BrowserSearchIndexTests(unittest.TestCase):
    def test_jvm_cache_reuse_and_invalidation(self):
        with tempfile.TemporaryDirectory() as work:
            harness=Path(work)/"BrowserSearchIndexCheck.java"
            harness.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",work,
                str(JAVA/"BrowserSearchIndex.java"),str(harness)],
                check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",work,"dev.xarkon.link.BrowserSearchIndexCheck"],
                check=True,capture_output=True,text=True)

    def test_activity_invalidates_on_structural_changes(self):
        text=(JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
        self.assertIn("searchIndex.get(sort,searchClosedMedia",text)
        self.assertIn("Entry::foldedName",text)
        self.assertIn("private void expandFolder(Entry e){\n        searchIndex.invalidate();",text)
        self.assertIn("private void load(){\n        searchIndex.invalidate();",text)
        self.assertIn("option.setOnClickListener(v->{sort=choice;searchIndex.invalidate();",text)
        self.assertIn("expandedChildren.put(key,children);searchIndex.invalidate();render();",text)
        self.assertIn("TransitionManager.beginDelayedTransition(scroll,new ChangeBounds().setDuration(150))",text)
        self.assertLess(text.index("BrowserSearchTree.filter(rows,"),text.index("list.removeAllViews();tileStrip=null;tileCount=0;"))
