#!/usr/bin/env python3
"""
approvals/approve.py

Usage: approve.py PATH/TO/PENDING.json

This script will:
- Load a pending task JSON (created by run.py)
- Show the task and ask for explicit confirmation before executing
- Execute a small set of supported task types (currently: github.create_repo)
- Log the result under orchestrator/logs/

Security: the script prompts for confirmation and supports --yes to force. It is intentionally conservative.
"""
import sys, json, subprocess
from pathlib import Path

WORKDIR = Path(__file__).resolve().parent.parent
APPROVALS = WORKDIR / "approvals"
LOGS = WORKDIR / "logs"
LOGS.mkdir(exist_ok=True)

SUPPORTED = ["github.create_repo"]


def run_github_create_repo(payload):
    name = payload.get("name")
    private = payload.get("private", True)
    readme = payload.get("readme","")
    if not name:
        print("Missing repo name in payload")
        return 2
    # call gh to create repo
    cmd = ["gh","repo","create",name,"--private" if private else "--public","--description",readme,"--confirm"]
    print("Running:"," ".join(cmd))
    r = subprocess.run(cmd)
    return r.returncode


def main(pending_path, assume_yes=False):
    p = Path(pending_path)
    if not p.exists():
        print("Pending file not found:",p)
        return 2
    task = json.loads(p.read_text())
    print("Task:",json.dumps(task,indent=2))
    if task.get("type") not in SUPPORTED:
        print("Unsupported task type:",task.get("type"))
        return 3
    if not assume_yes:
        ans = input('Type APPROVE to run this task: ').strip()
        if ans != 'APPROVE':
            print('Aborted by user')
            return 4
    # execute
    rc = 1
    if task["type"] == "github.create_repo":
        rc = run_github_create_repo(task["payload"])
    # log
    lpath = LOGS / f"{task['id']}.approve.log"
    lpath.write_text(f"Task {task['id']} executed with return code {rc}\n")
    # move pending to done
    done = p.with_suffix('.done.json')
    p.rename(done)
    print('Done. Log:',lpath)
    return rc

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: approve.py PATH/TO/PENDING.json [--yes]')
        sys.exit(1)
    path = sys.argv[1]
    yes = '--yes' in sys.argv
    sys.exit(main(path, assume_yes=yes))
