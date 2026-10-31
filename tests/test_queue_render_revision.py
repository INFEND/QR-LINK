"""Executable JVM regressions for queue invalidation and nested browser search."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
HARNESS="""package dev.xarkon.link;
import java.util.*;
public final class QueueBrowserCheck {
  private static void ok(boolean b){if(!b)throw new AssertionError("queue/browser regression");}
  private static final class Row {
    final String name;final int depth;
    Row(String name,int depth){this.name=name;this.depth=depth;}
  }
  public static void main(String[] args)throws Exception {
    long before=QueueRevision.current();
    Thread[] workers=new Thread[6];
    for(int i=0;i<workers.length;i++){
      workers[i]=new Thread(()->{for(int n=0;n<10000;n++)QueueRevision.changed();});
      workers[i].start();
    }
    for(Thread t:workers)t.join();
    ok(QueueRevision.current()-before==60000);
    List<Row> tree=Arrays.asList(new Row("Pictures",0),new Row("Trip",1),
        new Row("IMG_001.JPG",2),new Row("Other",1),new Row("note.txt",2),
        new Row("Downloads",0),new Row("clip.mp4",1));
    List<Row> found=BrowserSearchTree.filter(tree,r->r.depth,r->r.name,"img_001");
    ok(found.size()==3&&found.get(0)==tree.get(0)&&found.get(1)==tree.get(1)&&found.get(2)==tree.get(2));
    ok(BrowserSearchTree.filter(tree,r->r.depth,r->r.name,"clip").size()==2);
    ok(BrowserSearchTree.filter(tree,r->r.depth,r->r.name,"missing").isEmpty());
    ok(BrowserSearchTree.filter(tree,r->r.depth,r->r.name," ").size()==tree.size());
    ok(BrowserSearchTree.filter(tree,r->r.depth,r->r.name,"trip").size()==2);
  }
}
"""

class QueueBrowserTests(unittest.TestCase):
    def test_executable_java_regressions(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"QueueBrowserCheck.java"
            source.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,
                str(JAVA/"QueueRevision.java"),str(JAVA/"BrowserSearchTree.java"),
                str(source)],check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.QueueBrowserCheck"],
                check=True,capture_output=True,text=True)

    def test_queue_io_is_off_ui_thread(self):
        catalog=(JAVA/"FileCatalog.java").read_text(encoding="utf-8")
        main=(JAVA/"MainActivity.java").read_text(encoding="utf-8")
        browser=(JAVA/"FileBrowserActivity.java").read_text(encoding="utf-8")
        self.assertIn("QueueRevision.changed();",catalog)
        self.assertIn("final long revision=QueueRevision.current();",main)
        self.assertIn("queueReader.execute(()->{",main)
        self.assertIn("FileCatalog.load(getApplicationContext())",main)
        self.assertIn("transferFileAdapter.set(next.get(i),i);",main)
        self.assertIn("BrowserSearchTree.filter(rows,",browser)

if __name__=="__main__":
    unittest.main()
