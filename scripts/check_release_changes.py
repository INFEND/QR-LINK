#!/usr/bin/env python3
"""Future-release gate: each OTA note needs distinct changed product-code evidence.

This gate verifies concrete changed lines, not the semantic independence of a
feature. Human review must still reject artificially split changes.
Historical versions through v0.3.80 are deliberately unaffected.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

from make_manifest import load_release_notes

MIN_EVIDENCE_VERSION = (0, 3, 81)
PREFIXES = ("[+] ", "[-] ", "[=] ")


def version_tuple(version):
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){2}", version):
        raise ValueError("Некорректная версия для проверки изменений")
    return tuple(int(part) for part in version.split("."))


def required(version):
    return version_tuple(version) >= MIN_EVIDENCE_VERSION


def previous_tag(version):
    tags = subprocess.check_output(["git", "tag", "--list", "v*"], text=True).splitlines()
    candidates = []
    for tag in tags:
        try:
            parsed = version_tuple(tag.removeprefix("v"))
            if parsed < version_tuple(version):
                candidates.append((parsed, tag))
        except ValueError:
            continue
    if not candidates:
        raise ValueError("Не найден предыдущий тег релиза для сравнения")
    return max(candidates)[1]


def product_path(path):
    return isinstance(path, str) and path.startswith("app/src/main/") and (
        ".." not in Path(path).parts and "\\" not in path
    ) and not path.endswith("/")


def changed_lines(base_tag, path):
    diff = subprocess.check_output(
        ["git", "diff", "--unified=0", base_tag, "HEAD", "--", path], text=True
    )
    return {line[1:].strip() for line in diff.splitlines()
            if line.startswith(("+", "-")) and
            not line.startswith(("+++", "---")) and len(line[1:].strip()) >= 12}


def validate_evidence(notes, evidence, lookup):
    if len(notes) < 10:
        raise ValueError("Релиз требует минимум 10 реальных изменений")
    entries = evidence.get("entries") if isinstance(evidence, dict) else None
    if not isinstance(entries, list) or len(entries) != len(notes):
        raise ValueError("Для каждой строки OTA требуется отдельное доказательство")
    used = set()
    for index, (note, item) in enumerate(zip(notes, entries), 1):
        if not isinstance(item, dict) or item.get("note") != note:
            raise ValueError(f"Доказательство {index} не соответствует строке OTA")
        path, anchor = item.get("path"), item.get("changed_line")
        if not product_path(path) or not isinstance(anchor, str) or len(anchor.strip()) < 12:
            raise ValueError(f"Недопустимое доказательство изменения {index}")
        key = (path, anchor.strip())
        if key in used:
            raise ValueError("Одна строка кода не может доказывать две разные правки")
        used.add(key)
        if anchor.strip() not in lookup(path):
            raise ValueError(f"Изменение {index} не найдено в diff: {path}")
    return len(used)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    if not required(args.version):
        print("Исторический релиз: новый контроль diff не применяется")
        return
    notes = [line for line in load_release_notes(args.version).splitlines()
             if line.startswith(PREFIXES)]
    path = Path("release_notes") / f"v{args.version}.evidence.json"
    if not path.is_file():
        raise SystemExit("Отсутствуют доказательства реальных изменений: " + str(path))
    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
        base = previous_tag(args.version)
        if evidence.get("base_tag") != base:
            raise ValueError("Базовый тег доказательств не совпадает с предыдущим релизом")
        count = validate_evidence(notes, evidence, lambda file: changed_lines(base, file))
    except (ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        raise SystemExit("Проверка независимых изменений не пройдена: " + str(error))
    print(f"Подтверждено {count} отдельных строк кода для {count} записей OTA; база {base}")
    print("Смысловую независимость каждой функции дополнительно проверяет ревью кода.")


if __name__ == "__main__":
    main()
