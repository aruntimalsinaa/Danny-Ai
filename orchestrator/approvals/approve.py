#!/usr/bin/env python3
"""
approvals/approve.py - extended

Supports task types:
- github.create_repo (existing)
- file.write
- git.commit_push
- github.create_issue
- web.fetch
- run.shell

Safety: tasks are still recorded as pending and require APPROVE or --yes to run.
Only run.shell is allowed with explicit allow_run in payload.

Logs are written to orchestrator/logs/<taskid>.approve.log
Pending files are renamed to .done.json after execution.
"""
import sys, json, subprocess, shlex
from pathlib import Path
import requests

WORKDIR = Path(__file__).resolve().parent.parent
APPROVALS = WORKDIR / "approvals"
LOGS = WORKDIR / "logs"
LOGS.mkdir(exist_ok=True)

SUPPORTED = [
    "github.create_repo",
    "file.write",
    "git.commit_push",
    "github.create_issue",
    "web.fetch",
    "run.shell",
]


def run_cmd(cmd, cwd=None, capture=True):
    try:
        if capture:
            p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return p.returncode, p.stdout, p.stderr
        else:
            p = subprocess.run(cmd, cwd=cwd)
            return p.returncode, None, None
    except Exception as e:
        return 255, "", str(e)


def handle_github_create_repo(payload):
    name = payload.get("name")
    private = payload.get("private", True)
    readme = payload.get("readme", "")
    if not name:
        return 2, "Missing name", ""
    cmd = ["gh","repo","create",name,"--private" if private else "--public","--description",readme]
    # gh deprecated --confirm; pass any arg to skip interactive
    cmd.append("--confirm")
    return run_cmd(cmd)


def handle_file_write(payload):
    path = payload.get("path")
    content = payload.get("content","")
    if not path:
        return 2, "Missing path", ""
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return 0, f"Wrote {p}", ""
    except Exception as e:
        return 3, "", str(e)


def handle_git_commit_push(payload):
    paths = payload.get("paths", [])
    message = payload.get("message","Automated commit")
    branch = payload.get("branch","main")
    cwd = Path(payload.get("cwd","/root/.openclaw/workspace"))
    # stage
    if not paths:
        return 2, "No paths provided", ""
    cmd = ["git","add"] + paths
    rc,out,err = run_cmd(cmd, cwd=cwd)
    if rc != 0:
        return rc, out, err
    rc,out,err = run_cmd(["git","commit","-m",message], cwd=cwd)
    if rc != 0:
        # git commit returns non-zero if no changes; treat as ok with message
        if "nothing to commit" in (err or ""):
            out = "Nothing to commit"
            rc = 0
        else:
            return rc,out,err
    # push
    rc,out,err = run_cmd(["git","push","origin",f"HEAD:{branch}"], cwd=cwd)
    return rc,out,err


def handle_github_create_issue(payload):
    repo = payload.get("repo")
    title = payload.get("title")
    body = payload.get("body","")
    if not repo or not title:
        return 2, "Missing repo or title", ""
    cmd = ["gh","issue","create","--repo",repo,"--title",title,"--body",body]
    return run_cmd(cmd)


def handle_web_fetch(payload):
    url = payload.get("url")
    save_path = payload.get("save_path")
    if not url or not save_path:
        return 2, "Missing url or save_path", ""
    try:
        r = requests.get(url, timeout=15)
        p = Path(save_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(r.content)
        return 0, f"Saved {len(r.content)} bytes to {p}", ""
    except Exception as e:
        return 3, "", str(e)


def handle_run_shell(payload):
    cmd = payload.get("command")
    cwd = payload.get("cwd")
    allow = payload.get("allow_run", False)
    if not allow:
        return 4, "run.shell not allowed without allow_run=true", ""
    if not cmd:
        return 2, "Missing command", ""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    return run_cmd(cmd, cwd=cwd)


DISPATCH = {
    "github.create_repo": handle_github_create_repo,
    "file.write": handle_file_write,
    "git.commit_push": handle_git_commit_push,
    "github.create_issue": handle_github_create_issue,
    "web.fetch": handle_web_fetch,
    "run.shell": handle_run_shell,
}


def main(pending_path, assume_yes=False):
    p = Path(pending_path)
    if not p.exists():
        print("Pending file not found:",p)
        return 2
    task = json.loads(p.read_text())
    print("Task:",json.dumps(task,indent=2))
    ttype = task.get("type")
    if ttype not in SUPPORTED:
        print("Unsupported task type:",ttype)
        return 3
    if not assume_yes:
        ans = input('Type APPROVE to run this task: ').strip()
        if ans != 'APPROVE':
            print('Aborted by user')
            return 4
    handler = DISPATCH.get(ttype)
    if not handler:
        print("No handler for type",ttype)
        return 5
    rc,out,err = handler(task.get('payload',{}))
    lpath = LOGS / f"{task['id']}.approve.log"
    with lpath.open('w') as fh:
        fh.write(f"Return code: {rc}\n")
        fh.write("--- STDOUT ---\n")
        fh.write((out or '') + "\n")
        fh.write("--- STDERR ---\n")
        fh.write((err or '') + "\n")
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
