#!/usr/bin/env python3
"""Produce OTA update.json from an already signed APK."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import quote

from release_exceptions import declared_completions
from ota_history import build_history

MAX_RELEASE_NOTES_CHARS = 100_000
MIN_NEW_RELEASE_CHANGES = 10  # History only: v0.3.78 through v0.3.84
MIN_POLICY_VERSION = (0, 3, 78)

def requires_ten_changes(version):
    """Historical release-size rule; no minimum for v0.3.85 onward."""
    try:
        parts = tuple(int(part) for part in version.split("."))
    except ValueError:
        raise SystemExit("Invalid release notes version: " + version)
    return MIN_POLICY_VERSION <= parts < (0, 3, 85)

def load_release_notes(version):
    filename = Path("release_notes") / f"v{version}.txt"
    if not filename.is_file():
        raise SystemExit("Missing release notes: " + str(filename))
    notes = filename.read_text(encoding="utf-8").strip()
    if not notes:
        raise SystemExit("Empty release notes: " + str(filename))
    if len(notes) > MAX_RELEASE_NOTES_CHARS:
        raise SystemExit("Release notes too long: " + str(filename))
    # Release notes are customer-facing. A CI/QA report must never leak into OTA.
    entries = []
    heading = ""
    banned = ("scoped storage", "jvm", "github", "chatgpt", "openai",
              "регрессион", "тестирован", "тесты", "аппаратн",
              "не проверен", "не готов", "требуют испытан",
              "лимит 30000", "ci success", "versioncode")
    for line in notes.splitlines():
        line = line.strip()
        if not line:
            continue
        if not heading and not entries and line.startswith("QR LINK "):
            if not re.fullmatch(r"QR LINK\s+" + re.escape(version) +
                                r"(?:\s*[·:]\s*[^\n]{1,90})?", line):
                raise SystemExit("Wrong release notes heading: " + line)
            heading = line
            continue
        if not re.match(r"^\[(?:\+|-|–|=)\]\s+\S", line):
            raise SystemExit("Non-changelog text in release notes: " + line[:100])
        if len(line) > 260 or any(word in line.casefold() for word in banned):
            raise SystemExit("Internal or excessively long release note: " + line[:100])
        if line in entries:
            raise SystemExit("Duplicate release note: " + line[:100])
        entries.append(line)
    if not entries:
        raise SystemExit("No user-visible release changes: " + str(filename))
    if requires_ten_changes(version) and len(entries) < MIN_NEW_RELEASE_CHANGES:
        # A shorter release is possible ONLY for completion of one of the
        # eleven historically unfinished priority tasks. Its completion,
        # source diff and QA transition are strictly checked by the next CI
        # step (check_release_changes.py), before anything is published.
        evidence_file = Path("release_notes") / f"v{version}.evidence.json"
        try:
            evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
            completed = declared_completions(evidence)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise SystemExit("Short release requires valid priority-task evidence: " + str(error))
        if not completed:
            raise SystemExit("New release requires at least 10 changes, or one completed priority task")
    return "\n".join(([heading, ""] if heading else []) + entries)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", required=True)
    parser.add_argument("--aapt", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--github-output", required=True)
    args = parser.parse_args()

    if args.repo.casefold() not in ("antiferment/qr-link", "infend/qr-link"):
        raise SystemExit("Unexpected repository: " + args.repo)
    apk = Path(args.apk)
    if not apk.is_file():
        raise SystemExit("APK missing: " + str(apk))
    details = subprocess.check_output([args.aapt, "dump", "badging", str(apk)], text=True)
    match = re.search(r"^package: name='([^']+)' versionCode='([0-9]+)' versionName='([^']+)'", details, re.MULTILINE)
    if not match:
        raise SystemExit("Unable to parse APK version using aapt")
    package_name, code, version = match.groups()
    if package_name != "dev.xarkon.link":
        raise SystemExit("Unexpected applicationId: " + package_name)
    if int(code) <= 0:
        raise SystemExit("Invalid versionCode: " + code)
    if not re.fullmatch(r"[A-Za-z0-9._-]+", version):
        raise SystemExit("Invalid versionName for a Git tag")
    tag = "v" + version
    sha = hashlib.sha256(apk.read_bytes()).hexdigest()
    data = {
        "schema": 1,
        "packageName": package_name,
        "versionCode": int(code),
        "versionName": version,
        # Keep the legacy release URL for already-installed versions that pin its path.
        # GitHub redirects the old repository slug after an owner rename.
        "apkUrl": f"https://github.com/ANTIFERMENT/QR-LINK/releases/download/{quote(tag)}/QR-LINK.apk",
        "sha256": sha,
        "sizeBytes": apk.stat().st_size,
        "publishedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "notes": load_release_notes(version),
        "history": build_history(version, int(code), load_release_notes(version))
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with open(args.github_output, "a", encoding="utf-8") as f:
        f.write("tag=" + tag + "\n")
        f.write("version=" + version + "\n")
        f.write("version_code=" + code + "\n")
    print("OTA metadata created:", package_name, version, code)

if __name__ == "__main__":
    main()
