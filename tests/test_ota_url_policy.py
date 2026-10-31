"""Executable JVM checks for exact trusted OTA release paths after repository rename."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"app/src/main/java/dev/xarkon/link/OtaUrlPolicy.java"
HARNESS="""package dev.xarkon.link;
public final class OtaUrlPolicyCheck {
 public static void main(String[] args) {
  for(String owner:new String[]{"ANTIFERMENT","INFEND"}){
   String url="https://github.com/"+owner+"/QR-LINK/releases/download/v0.3.61/QR-LINK.apk";
   if(!OtaUrlPolicy.trustedApk(url,"0.3.61"))throw new AssertionError("Trusted repo rejected");
  }
  for(String bad:new String[]{
   "http://github.com/INFEND/QR-LINK/releases/download/v0.3.61/QR-LINK.apk",
   "https://github.com/attacker/QR-LINK/releases/download/v0.3.61/QR-LINK.apk",
   "https://github.com/INFEND/QR-LINK/releases/download/v0.3.60/QR-LINK.apk",
   "https://github.com/INFEND/QR-LINK/releases/download/v0.3.61/QR-LINK.apk?x=1",
   "https://github.com.evil/INFEND/QR-LINK/releases/download/v0.3.61/QR-LINK.apk"
  })if(OtaUrlPolicy.trustedApk(bad,"0.3.61"))throw new AssertionError("Untrusted URL accepted: "+bad);
 }
}
"""
class OtaUrlPolicyTests(unittest.TestCase):
 def test_exact_release_paths(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/"OtaUrlPolicyCheck.java"
   p.write_text(HARNESS,encoding="utf-8")
   subprocess.run(["javac","-encoding","UTF-8","-d",tmp,str(SRC),str(p)],check=True)
   subprocess.run(["java","-cp",tmp,"dev.xarkon.link.OtaUrlPolicyCheck"],check=True)
 def test_fallback_is_pinned_and_errors_are_localized(self):
  updater=(SRC.parent/"UpdateManager.java").read_text(encoding="utf-8")
  self.assertIn("readManifest(OtaUrlPolicy.CANONICAL_MANIFEST)",updater)
  self.assertIn("OtaUrlPolicy.trustedApk(apkUrl,versionName)",updater)
  self.assertIn("return ErrorText.human(s);",updater)
if __name__=="__main__":unittest.main()
