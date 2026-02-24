#!/usr/bin/env python3
"""
Extended approvals/approve.py with PR composite handler: pr.create_flow

pr.create_flow payload should include:
{
  "repo": "owner/repo",
  "base_branch": "main",
  "feature_branch": "feature/xyz",
  "files": [{"path":"rel/path","content":"..."}],
  "commit_message": "feat: ...",
  "pr_title": "Add feature",
  "pr_body": "Details...",
  "request_reviewers": ["user1","user2"],
  "merge_method": "merge"  # merge|squash|rebase (optional)
}

This composite flow will:
- write files
- create branch
- commit & push
- create PR
- request reviewers (optional)
- optionally merge if payload.merge_after == true (still requires approval)

Security: Each network/git action requires the overall approval (single APPROVE). Logs include created PR URL/number.
"""
import sys, json, subprocess, shlex, time
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
    "pr.create_flow",
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

# existing handlers (github.create_repo, file.write, git.commit_push, github.create_issue, web.fetch, run.shell)
# For brevity, reuse previous implementations where possible by importing from a shared location would be nicer, but keep inline for now.

def handle_github_create_repo(payload):
    name = payload.get("name")
    private = payload.get("private", True)
    readme = payload.get("readme", "")
    if not name:
        return 2, "Missing name", ""
    cmd = ["gh","repo","create",name,"--private" if private else "--public","--description",readme]
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
    if not paths:
        return 2, "No paths provided", ""
    cmd = ["git","add"] + paths
    rc,out,err = run_cmd(cmd, cwd=cwd)
    if rc != 0:
        return rc, out, err
    rc,out,err = run_cmd(["git","commit","-m",message], cwd=cwd)
    if rc != 0:
        if "nothing to commit" in (err or ""):
            out = "Nothing to commit"
            rc = 0
        else:
            return rc,out,err
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

# New handlers for PR flow

def handle_create_branch(repo_cwd, base_branch, feature_branch):
    # assume repo is already cloned in repo_cwd and git remote origin exists
    rc,out,err = run_cmd(["git","checkout","-b",feature_branch, base_branch], cwd=repo_cwd)
    if rc != 0:
        # try create from base by checking out base first
        run_cmd(["git","checkout",base_branch], cwd=repo_cwd)
        rc,out,err = run_cmd(["git","checkout","-b",feature_branch], cwd=repo_cwd)
    return rc,out,err


def handle_push_branch(repo_cwd, feature_branch):
    rc,out,err = run_cmd(["git","push","--set-upstream","origin",feature_branch], cwd=repo_cwd)
    return rc,out,err


def handle_github_create_pr(payload):
    repo = payload.get("repo")
    head = payload.get("head_branch")
    base = payload.get("base_branch","main")
    title = payload.get("title","PR")
    body = payload.get("body","")
    if not repo or not head:
        return 2, "Missing repo or head branch", ""
    cmd = ["gh","pr","create","--repo",repo,"--head",head,"--base",base,"--title",title,"--body",body]
    rc,out,err = run_cmd(cmd)
    # gh pr create prints URL on stdout; try extract PR number
    pr_url = None
    pr_number = None
    if out:
        for line in out.splitlines():
            if line.startswith("https://") and "/pull/" in line:
                pr_url = line.strip()
                try:
                    pr_number = int(pr_url.rstrip('/').split('/')[-1])
                except:
                    pr_number = None
    return rc, json.dumps({"out":out,"err":err,"pr_url":pr_url,"pr_number":pr_number}), err


def handle_request_review(payload):
    repo = payload.get("repo")
    pr = payload.get("pr_number")
    reviewers = payload.get("reviewers",[])
    if not repo or not pr or not reviewers:
        return 2, "Missing repo/pr/reviewers", ""
    cmd = ["gh","api","repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers" ]
    # Simpler: use gh pr review-request add
    cmd = ["gh","pr","review-request","add",str(pr),"--repo",repo] + reviewers
    return run_cmd(cmd)


def handle_merge_pr(payload):
    repo = payload.get("repo")
    pr = payload.get("pr_number")
    method = payload.get("method","merge")
    if not repo or not pr:
        return 2, "Missing repo/pr", ""
    cmd = ["gh","pr","merge",str(pr),"--repo",repo]
    if method == "squash":
        cmd.append("--squash")
    elif method == "rebase":
        cmd.append("--rebase")
    else:
        cmd.append("--merge")
    return run_cmd(cmd)


def handle_pr_create_flow(payload):
    # high-level composite flow
    repo = payload.get("repo")
    base = payload.get("base_branch","main")
    feature = payload.get("feature_branch")
    files = payload.get("files",[])
    commit_message = payload.get("commit_message","feat: automated change")
    pr_title = payload.get("pr_title","Automated PR")
    pr_body = payload.get("pr_body","")
    reviewers = payload.get("request_reviewers",[])
    merge_after = payload.get("merge_after",False)
    merge_method = payload.get("merge_method","merge")

    if not repo or not feature:
        return 2, "Missing repo or feature branch", ""
    # assume repo is in workspace/<repo-name>
    repo_name = repo.split('/')[-1]
    repo_cwd = Path.cwd() / repo_name
    # if not present, try gh repo clone
    if not repo_cwd.exists():
        rc,out,err = run_cmd(["gh","repo","clone",repo])
        if rc != 0:
            return rc,out,err
    # write files
    written = []
    for f in files:
        p = repo_cwd / f.get("path")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f.get("content",""))
        written.append(str(p))
    # create branch
    rc,out,err = handle_create_branch(repo_cwd, base, feature)
    if rc != 0:
        return rc,out,err
    # commit & push
    rc,out,err = run_cmd(["git","add"] + written, cwd=repo_cwd)
    if rc != 0:
        return rc,out,err
    rc,out,err = run_cmd(["git","commit","-m",commit_message], cwd=repo_cwd)
    if rc != 0:
        if "nothing to commit" in (err or ""):
            out = "Nothing to commit"
            rc = 0
        else:
            return rc,out,err
    rc,out,err = handle_push_branch(repo_cwd, feature)
    if rc != 0:
        return rc,out,err
    # create PR
    rc,out,err = handle_github_create_pr({"repo":repo,"head_branch":feature,"base_branch":base,"title":pr_title,"body":pr_body})
    # out contains pr_url/pr_number JSON encode in handler
    try:
        info = json.loads(out)
        pr_number = info.get('pr_number')
        pr_url = info.get('pr_url')
    except Exception:
        pr_number = None
        pr_url = None
    # request reviewers
    if reviewers:
        rc2,out2,err2 = handle_request_review({"repo":repo,"pr_number":pr_number,"reviewers":reviewers})
    # optionally merge
    merge_result = None
    if merge_after:
        rc3,out3,err3 = handle_merge_pr({"repo":repo,"pr_number":pr_number,"method":merge_method})
        merge_result = {"rc":rc3,"out":out3,"err":err3}
    summary = {"pr_number":pr_number,"pr_url":pr_url,"merge_result":merge_result}
    return 0, json.dumps(summary), ""


DISPATCH = {
    "github.create_repo": handle_github_create_repo,
    "file.write": handle_file_write,
    "git.commit_push": handle_git_commit_push,
    "github.create_issue": handle_github_create_issue,
    "web.fetch": handle_web_fetch,
    "run.shell": handle_run_shell,
    "pr.create_flow": handle_pr_create_flow,
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
