"""Executable tests for peer identity validation and display-name safety."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"app/src/main/java/dev/xarkon/link/PeerIdentity.java"
HARNESS=r"""package dev.xarkon.link;
public final class PeerIdentityCheck {
 public static void main(String[] args){
  if(!PeerIdentity.compatible("XARKON LINK",1))throw new AssertionError("Expected protocol rejected");
  if(PeerIdentity.compatible("XARKON LINK",2)||PeerIdentity.compatible("Fake",1)
      ||PeerIdentity.compatible(null,1))throw new AssertionError("Unverified peer accepted");
  String unsafe="  Galaxy"+(char)10+"S24"+(char)0x202E+"  Ultra  ";
  String safe=PeerIdentity.displayName(unsafe);
  if(safe.indexOf(10)>=0||safe.indexOf(0x202E)>=0||safe.length()>48)
      throw new AssertionError("Control/bidi characters retained: "+safe);
  if(!"Устройство".equals(PeerIdentity.displayName(""+(char)0x202E+(char)10)))
      throw new AssertionError("Empty identity should use fallback");
  if(PeerIdentity.displayName("x".repeat(100)).length()!=48)
      throw new AssertionError("Peer name is not bounded");
 }
}
"""
class PeerIdentityTests(unittest.TestCase):
 def test_identity_contract(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/"PeerIdentityCheck.java"
   p.write_text(HARNESS,encoding="utf-8")
   subprocess.run(["javac","-encoding","UTF-8","-d",tmp,str(SOURCE),str(p)],check=True)
   subprocess.run(["java","-cp",tmp,"dev.xarkon.link.PeerIdentityCheck"],check=True)
if __name__=="__main__":unittest.main()
