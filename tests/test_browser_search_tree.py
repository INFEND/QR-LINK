"""JVM tests for matching expanded folders and preserving ancestor rows."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/"app/src/main/java/dev/xarkon/link"
HARNESS=r'''package dev.xarkon.link;
import java.util.*;
public class BrowserSearchTreeCheck {
    static class Row {
        final String name;final int depth;
        Row(String n,int d){name=n;depth=d;}
    }
    static void equal(List<Row> result,String... expected){
        if(result.size()!=expected.length)throw new AssertionError("Unexpected row count");
        for(int i=0;i<expected.length;i++)
            if(!result.get(i).name.equals(expected[i]))
                throw new AssertionError("Wrong row at "+i);
    }
    public static void main(String[] args){
        List<Row> rows=List.of(
            new Row("Camera",0),new Row("portrait.jpg",1),
            new Row("nested",1),new Row("hidden.jpg",2),
            new Row("Music",0),new Row("track.mp3",1));
        equal(BrowserSearchTree.filter(rows,r->r.depth,r->r.name,"CAMERA"),
            "Camera","portrait.jpg","nested","hidden.jpg");
        equal(BrowserSearchTree.filter(rows,r->r.depth,r->r.name,"hidden"),
            "Camera","nested","hidden.jpg");
        equal(BrowserSearchTree.filter(rows,r->r.depth,r->r.name,"track"),
            "Music","track.mp3");
        equal(BrowserSearchTree.filter(rows,r->r.depth,r->r.name,"absent"));
        // A deep, 30k-item folder tree must keep every descendant and
        // ancestor without repeatedly walking all 24 levels per hit.
        ArrayList<Row> large=new ArrayList<>();
        for(int i=0;i<24;i++)large.add(new Row(i==0?"TARGET":"folder"+i,i));
        for(int i=0;i<30000;i++)large.add(new Row("image"+i+".jpg",24));
        List<Row> matched=BrowserSearchTree.filter(large,r->r.depth,r->r.name,"TARGET");
        if(matched.size()!=large.size())throw new AssertionError("Missing descendants");
        List<Row> leaf=BrowserSearchTree.filter(large,r->r.depth,r->r.name,"image29999");
        if(leaf.size()!=25)throw new AssertionError("Missing nested ancestors");
        equal(BrowserSearchTree.filter(rows,r->r.depth,r->r.name,""),"Camera",
            "portrait.jpg","nested","hidden.jpg","Music","track.mp3");
    }
}
'''

class SearchTreeTests(unittest.TestCase):
    def test_matching_folder_keeps_descendants(self):
        with tempfile.TemporaryDirectory() as work:
            harness=Path(work)/"BrowserSearchTreeCheck.java"
            harness.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",work,
                str(JAVA/"BrowserSearchTree.java"),str(harness)],
                check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",work,"dev.xarkon.link.BrowserSearchTreeCheck"],
                check=True,capture_output=True,text=True)
