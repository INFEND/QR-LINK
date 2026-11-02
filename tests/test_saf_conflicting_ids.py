"""SAF provider IDs cannot refer to both a file and a directory."""
import subprocess
import tempfile
import unittest
from pathlib import Path

JAVA=Path(__file__).resolve().parents[1]/"app/src/main/java/dev/xarkon/link"
HARNESS=r'''package dev.xarkon.link;
import java.io.*;
import java.util.*;
public final class SafConflictingIdsCheck {
    static void reject(List<String> order)throws Exception{
        BrowserFolderCardStats.DocumentChildReader reader=(parent,visit)->{
            if(parent.equals("root")){
                for(String kind:order)
                    visit.accept(kind.equals("root")?"root":"same",
                        kind.equals("dir"),kind.equals("file")?7:0);
            }
        };
        boolean rejected=false;
        try{BrowserFolderCardStats.scanDocuments("root",reader);}
        catch(IOException expected){rejected=true;}
        if(!rejected)throw new AssertionError("Conflicting SAF document IDs accepted: "+order);
    }
    public static void main(String[] args)throws Exception{
        reject(Arrays.asList("dir","file"));
        reject(Arrays.asList("file","dir"));
        reject(Arrays.asList("root"));
    }
}'''
class SafConflictingIdsTests(unittest.TestCase):
    def test_conflicting_provider_types_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/"SafConflictingIdsCheck.java"
            file.write_text(HARNESS,encoding="utf-8")
            subprocess.run(["javac","-encoding","UTF-8","-d",tmp,
                str(JAVA/"BrowserFolderCardStats.java"),str(file)],
                check=True,capture_output=True,text=True)
            subprocess.run(["java","-cp",tmp,"dev.xarkon.link.SafConflictingIdsCheck"],
                check=True,capture_output=True,text=True)
