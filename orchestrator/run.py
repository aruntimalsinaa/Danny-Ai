#!/usr/bin/env python3
"""
Minimal orchestrator engine (stub).

Usage: python3 run.py path/to/task.json

This stub validates the task JSON against tasks.schema.json, logs the task, and prints actions it would take.
It intentionally does NOT perform privileged host or network actions; instead it writes a pending approval file under approvals/.

Extend this file to integrate with approvals, logging, and actual runners.
"""
import sys, json, os
from pathlib import Path

WORKDIR = Path(__file__).resolve().parent
APPROVALS = WORKDIR / "approvals"
LOGS = WORKDIR / "logs"
SCHEMA = WORKDIR / "tasks.schema.json"

APPROVALS.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)


def main(task_path):
    task_path = Path(task_path)
    task = json.loads(task_path.read_text())
    # very small validation
    for k in ("id","type","payload"):
        if k not in task:
            print(f"Task missing required key: {k}")
            return 2
    # write pending approval
    apath = APPROVALS / f"{task['id']}.pending.json"
    apath.write_text(json.dumps(task, indent=2))
    print(f"Task {task['id']} recorded as pending approval: {apath}")
    # log
    lpath = LOGS / f"{task['id']}.log"
    lpath.write_text(f"Task recorded: {task['id']}\nType: {task['type']}\nRequires approval: {task.get('requires_approval', True)}\n")
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: run.py path/to/task.json")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
