#!/usr/bin/env python3
"""Strictly scoped exception for a completed QR LINK priority requirement.

The exception changes release size only, not the test, signing or OTA gates.
A claim alone never proves completion: CI must also verify the QA transition
and an independently changed line of real Android product source.
"""
import re

PRIORITY_TASK_IDS = frozenset((
    "T07", "T08", "T15", "T16",
    "F17", "F18", "O14", "O17",
    "U02", "U06", "U25",
))
MIN_STANDARD_CHANGES = 10


def declared_completions(evidence):
    """Return valid, unique priority IDs claimed by the release evidence."""
    if not isinstance(evidence, dict):
        raise ValueError("Некорректный формат доказательств релиза")
    ids = evidence.get("completed_tasks", [])
    if not isinstance(ids, list):
        raise ValueError("completed_tasks должен быть списком идентификаторов")
    if len(ids) != len(set(map(str, ids))):
        raise ValueError("Повторные идентификаторы завершённых задач недопустимы")
    for task_id in ids:
        if not isinstance(task_id, str) or task_id not in PRIORITY_TASK_IDS:
            raise ValueError("Исключение не применяется к задаче: " + str(task_id))
    return tuple(ids)


def qa_status(content, task_id):
    """Read the row status, regardless of the 4- or 5-column QA table."""
    if task_id not in PRIORITY_TASK_IDS:
        raise ValueError("Неизвестная приоритетная задача: " + str(task_id))
    matched = []
    for line in content.splitlines():
        if re.match(r"^\|\s*" + re.escape(task_id) + r"\s*\|", line):
            statuses = re.findall(r"\*\*(Готово|Не готово)\*\*", line)
            if len(statuses) != 1:
                raise ValueError("Неверная метка статуса QA: " + task_id)
            matched.append(statuses[0])
    if len(matched) != 1:
        raise ValueError("В QA должен быть ровно один пункт: " + task_id)
    return matched[0]


def require_new_completion(before_qa, after_qa, ids):
    """Allow only an actual Not ready -> Ready transition since the prior tag."""
    for task_id in ids:
        if qa_status(before_qa, task_id) != "Не готово":
            raise ValueError("Задача уже была готова в предыдущем релизе: " + task_id)
        if qa_status(after_qa, task_id) != "Готово":
            raise ValueError("Задача ещё не завершена в текущем QA: " + task_id)
    return len(ids)
