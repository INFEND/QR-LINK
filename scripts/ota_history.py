"""Build a versionCode-indexed, customer-facing history for cumulative OTA notes."""
from pathlib import Path
import re
import subprocess

PREFIXES = ("[+] ", "[=] ", "[-] ", "[–] ")
BANNED = ("scoped storage", "jvm", "github", "chatgpt", "openai",
          "регрессион", "тестирован", "тесты", "аппаратн",
          "не проверен", "не готов", "требуют испытан",
          "лимит 30000", "ci success", "versioncode")
MAX_HISTORY_CHARS = 1_000_000  # Bounded payload, no fixed limit on skipped release count


def clean_notes(source):
    """Mirror ReleaseNotes.visible: never leak historical developer footnotes."""
    lines = []
    for raw in source.splitlines():
        line = raw.strip()
        if not (5 <= len(line) <= 260 and line.startswith(PREFIXES)):
            continue
        if any(word in line.casefold() for word in BANNED):
            continue
        lines.append(line)
    return "\n".join(lines)


def version_parts(name):
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){2}", name):
        raise ValueError("Invalid release version: " + name)
    return tuple(map(int, name.split(".")))


def tagged_version_code(tag):
    """Read the actual historical versionCode from each published tag."""
    result = subprocess.run(["git", "show", tag + ":app/build.gradle"],
                            capture_output=True, text=True)
    if result.returncode:
        raise ValueError("Cannot read historical versionCode: " + tag)
    match = re.search(r"\bversionCode\s*(?:=\s*)?(\d+)\b", result.stdout)
    if not match:
        raise ValueError("Historical versionCode missing: " + tag)
    return int(match.group(1))


def build_history(version, version_code, current_notes):
    """Include all tagged releases before the new one, then the new release."""
    current = version_parts(version)
    result = subprocess.run(["git", "tag", "--list", "v*"],
                            capture_output=True, text=True)
    # Offline fixture tests have no Git metadata; they still get current notes.
    tags = result.stdout.splitlines() if result.returncode == 0 else []
    entries = []
    for tag in tags:
        try:
            parsed = version_parts(tag.removeprefix("v"))
        except ValueError:
            continue
        if parsed >= current or parsed < (0, 3, 39):
            continue
        path = Path("release_notes") / (tag + ".txt")
        if not path.is_file():
            if parsed >= (0, 3, 85):
                raise ValueError("Missing historical release notes: " + tag)
            continue
        code = tagged_version_code(tag)
        if code >= version_code:
            raise ValueError("Historical versionCode is not lower: " + tag)
        notes = clean_notes(path.read_text(encoding="utf-8"))
        if not notes:
            if parsed >= (0, 3, 85):
                raise ValueError("No customer-facing notes in: " + tag)
            continue
        entries.append({"versionCode": code, "versionName": tag[1:], "notes": notes})
    entries.append({"versionCode": version_code, "versionName": version,
                    "notes": clean_notes(current_notes)})
    entries.sort(key=lambda entry: entry["versionCode"])
    if not entries[-1]["notes"]:
        raise ValueError("Latest release has no customer-facing notes")
    codes = [entry["versionCode"] for entry in entries]
    if len(codes) != len(set(codes)):
        raise ValueError("Duplicate historical versionCode")
    names = [version_parts(entry["versionName"]) for entry in entries]
    if names != sorted(names):
        raise ValueError("Historical version names are not monotonic")
    # Every 0.3.x version since 0.3.85 was released; missing one means
    # that the history is incomplete and must not be advertised as complete.
    patches = {name[2] for name in names if name[:2] == (0, 3) and name[2] >= 85}
    if current[:2] == (0, 3) and current[2] >= 85 and len(tags) > 0:
        missing = set(range(85, current[2] + 1)) - patches
        if missing:
            raise ValueError("Missing published OTA history: " + str(sorted(missing)))
    if sum(len(entry["notes"]) for entry in entries) > MAX_HISTORY_CHARS:
        raise ValueError("OTA cumulative history exceeds size limit")
    return entries
