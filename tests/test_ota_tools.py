import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]

class OtaToolsTests(unittest.TestCase):
    def test_manifest_generation(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            apk = p / "QR-LINK.apk"
            apk.write_bytes(b"not a real APK; only fixture for manifest generator")
            fake_aapt = p / "aapt"
            fake_aapt.write_text(
                "#!/bin/sh\nprintf \"package: name='dev.xarkon.link' versionCode='39' versionName='0.3.9'\\n\"\n")
            fake_aapt.chmod(0o755)
            (p / "release_notes").mkdir()
            (p / "release_notes/v0.3.9.txt").write_text("[+] Проверка настоящего списка изменений",encoding="utf-8")
            out = p / "update.json"
            output = p / "github_output"
            subprocess.run([
                sys.executable, str(ROOT / "scripts/make_manifest.py"),
                "--apk", str(apk), "--aapt", str(fake_aapt),
                "--repo", "ANTIFERMENT/QR-LINK",
                "--output", str(out), "--github-output", str(output)
            ], check=True, cwd=p)
            manifest = json.loads(out.read_text())
            self.assertEqual(manifest["packageName"], "dev.xarkon.link")
            self.assertEqual(manifest["versionCode"], 39)
            self.assertEqual(manifest["sha256"], hashlib.sha256(apk.read_bytes()).hexdigest())
            self.assertEqual(manifest["sizeBytes"], apk.stat().st_size)
            self.assertEqual(manifest["apkUrl"],"https://github.com/ANTIFERMENT/QR-LINK/releases/download/v0.3.9/QR-LINK.apk")
            self.assertIn("настоящего списка изменений",manifest["notes"])
            self.assertIn("tag=v0.3.9", output.read_text())

    def test_renamed_repository_keeps_legacy_ota_compatibility(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            (p/"QR-LINK.apk").write_bytes(b"fixture")
            aapt=p/"aapt"
            aapt.write_text("#!/bin/sh\\nprintf \\"package: name='dev.xarkon.link' versionCode='66' versionName='0.3.61'\\\\n\\"\\n")
            aapt.chmod(0o755)
            (p/"release_notes").mkdir()
            (p/"release_notes/v0.3.61.txt").write_text("[+] Реальные изменения",encoding="utf-8")
            cmd=[sys.executable,str(ROOT/"scripts/make_manifest.py"),"--apk",str(p/"QR-LINK.apk"),
                 "--aapt",str(aapt),"--repo","INFEND/QR-LINK","--output",str(p/"update.json"),
                 "--github-output",str(p/"github_output")]
            result=subprocess.run(cmd,cwd=p,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            data=json.loads((p/"update.json").read_text())
            self.assertIn("/ANTIFERMENT/QR-LINK/releases/download/v0.3.61/",data["apkUrl"])
            self.assertIn("Реальные изменения",data["notes"])
            (p/"release_notes/v0.3.61.txt").unlink()
            result=subprocess.run(cmd,cwd=p,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn("Missing release notes",result.stderr+result.stdout)

    def test_manifest_rejects_wrong_application_id(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            apk = p / "QR-LINK.apk"
            apk.write_bytes(b"fixture")
            fake_aapt = p / "aapt"
            fake_aapt.write_text(
                "#!/bin/sh\nprintf \"package: name='com.example.wrong' versionCode='48' versionName='0.3.43'\\n\"\n"
            )
            fake_aapt.chmod(0o755)
            result = subprocess.run([
                sys.executable, str(ROOT / "scripts/make_manifest.py"),
                "--apk", str(apk), "--aapt", str(fake_aapt),
                "--repo", "ANTIFERMENT/QR-LINK",
                "--output", str(p / "update.json"),
                "--github-output", str(p / "github_output")
            ], capture_output=True, text=True, cwd=p)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unexpected applicationId", result.stderr + result.stdout)
            self.assertFalse((p / "update.json").exists())

    def test_versioned_archive_name_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "scripts").mkdir()
            (base / "scripts/import_source_zip.py").write_bytes(
                (ROOT / "scripts/import_source_zip.py").read_bytes())
            with zipfile.ZipFile(base / "QR_LINK_v0.3.9_FIXED_OTA_CodeOnTheGo.zip", "w") as z:
                root = "QR_LINK_Project/"
                z.writestr(root + "settings.gradle", "include ':app'\\n")
                z.writestr(root + "app/build.gradle",
                           "android { namespace 'dev.xarkon.link' }\\n")
                z.writestr(root + "app/src/main/AndroidManifest.xml",
                           '<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application/></manifest>')
            subprocess.run([sys.executable, "scripts/import_source_zip.py"], cwd=base, check=True)
            self.assertTrue((base / "app/build.gradle").is_file())

    def test_import_zip_and_integrate_engine(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "scripts").mkdir()
            (base / "ota").mkdir()
            (base / "scripts/import_source_zip.py").write_bytes(
                (ROOT / "scripts/import_source_zip.py").read_bytes())
            (base / "ota/QrLinkOta.java.template").write_bytes(
                (ROOT / "ota/QrLinkOta.java.template").read_bytes())
            with zipfile.ZipFile(base / "QR_LINK_SOURCE.zip", "w") as z:
                root = "QR_LINK_v0.3.8/"
                z.writestr(root + "settings.gradle", "include ':app'\n")
                z.writestr(root + "app/build.gradle",
                           'android { namespace "com.example.qrlink" }\n')
                z.writestr(root + "app/src/main/AndroidManifest.xml",
                           '<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application/></manifest>')
                z.writestr(root + "app/src/main/java/com/example/qrlink/MainActivity.java",
                           "package com.example.qrlink;")
                z.writestr(root + ".github/workflows/evil.yml", "fake")
                z.writestr(root + "app/build/old.apk", "old")
                z.writestr(root + "app/release-key.jks", "sensitive")
            subprocess.run(
                [sys.executable, "scripts/import_source_zip.py"], cwd=base, check=True)
            java = base / "app/src/main/java/com/example/qrlink/QrLinkOta.java"
            self.assertTrue(java.is_file())
            self.assertIn("package com.example.qrlink;", java.read_text())
            manifest = (base / "app/src/main/AndroidManifest.xml").read_text()
            self.assertIn("android.permission.INTERNET", manifest)
            self.assertIn("android.permission.REQUEST_INSTALL_PACKAGES", manifest)
            self.assertFalse((base / ".github/workflows/evil.yml").exists())
            self.assertFalse((base / "app/build/old.apk").exists())
            self.assertFalse((base / "app/release-key.jks").exists())

if __name__ == "__main__":
    unittest.main()
