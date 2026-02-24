# Orchestrator Workflow Tree

This document describes the high-level workflow tree for Danny's orchestrator and approval flow. It includes a Mermaid diagram (in diagram.mmd) you can render locally or view with Mermaid-compatible renderers.

## Workflow (text tree)

1. Submit Task
   - Source: examples/*.json, CLI, CI webhook, or Chat (assistant-generated)
   - Action: run.py validates and writes pending JSON -> orchestrator/approvals/<id>.pending.json

2. Review Pending
   - Human inspects pending JSON (cat or scripts/list_pending.py)
   - Decide action: approve, edit, or reject

3. Approve (explicit)
   - Command: approvals/approve.py <pending.json>
   - Must type APPROVE or pass --yes

4. Execute Handlers (single approval runs handler)
   - Handlers include:
     - file.write (local file changes)
     - web.fetch (download URL)
     - github.create_repo (gh)
     - git.commit_push (git+push)
     - github.create_issue (gh)
     - run.shell (requires allow_run=true)
     - pr.create_flow (composite: write -> branch -> commit -> push -> create PR -> request review -> optional merge)
     - github.review_pr / github.post_pr_comment / github.merge_pr (review & merge actions)

5. Logging & Audit
   - All runs write logs to orchestrator/logs/<taskid>.approve.log
   - Pending files renamed to .done.json after execution

6. Optional follow-ups
   - Create new tasks from outputs (e.g., create merge task after CI green)
   - Manual or automated CI checks (query GitHub, run local tests)


## Mermaid Diagram (save as diagram.mmd or render via Mermaid)

```mermaid
flowchart TD
  A[Submit Task\n(example JSON / CLI / Chat)] --> B[run.py\nCreate pending file]
  B --> C[Pending Approval\n(orchestrator/approvals/*.pending.json)]
  C --> D[Human Review]
  D --> E{Approve?}
  E -- No --> F[Edit or Reject\n(pending remains or removed)]
  E -- Yes --> G[approve.py\nExecute Handler]
  G --> H[Handler Types]
  H --> H1[file.write]
  H --> H2[web.fetch]
  H --> H3[git.commit_push]
  H --> H4[github.create_repo]
  H --> H5[pr.create_flow]
  H --> H6[run.shell (allow_run)]
  G --> I[Logs & Audit\n(orchestrator/logs/*.approve.log)]
  I --> J[Rename pending -> .done.json]
  J --> K[Optional: new tasks / CI checks / merge requests]
```


