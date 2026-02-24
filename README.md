# Danny-Ai

Danny is a local, safe orchestrator and AI assistant scaffold that helps automate tasks with explicit human approvals.

What this repo contains

- skills/orchestrator-danny/: A bundled skill providing a minimal orchestrator. Includes:
  - scripts/run.py — record tasks as pending approvals
  - scripts/approvals/approve.py — review and run approved tasks
  - scripts/list_pending.py — list pending tasks
  - references/tasks.schema.json — task schema
  - examples/ — example task JSON files
- orchestrator/: Original orchestrator scaffold and logs
- Other workspace files for configuration and experimentation

Why this exists

Danny (the assistant) and this orchestrator let you safely automate routine developer and workspace tasks while keeping an explicit human approval gate. Use it to:

- Automate repo creation, issue filing, or simple file operations
- Run git commits & pushes through an auditable approval flow
- Fetch web resources and save them into the workspace
- Prototype more advanced orchestrations without giving agents unrestricted access

How to use (quick start)

1) Create a task JSON in examples/ (or use the provided examples).
2) Record it as pending:
   /root/.openclaw/workspace/orchestrator/run.py /path/to/task.json
3) Review the pending file under orchestrator/approvals/
4) Approve and run:
   /root/.openclaw/workspace/orchestrator/approvals/approve.py /path/to/pending.json
   (Type APPROVE when prompted, or use --yes to run non-interactively)
5) Check logs in orchestrator/logs/ for stdout/stderr and return codes.

Safety notes

- No task runs without explicit approval.
- Do not store secrets in task JSONs.
- Review git pushes and GitHub actions carefully — use least-privilege tokens.

How to contribute

1. Fork/clone the repo
2. Edit or add new task handlers under skills/orchestrator-danny/scripts/approvals/
3. Add example tasks under skills/orchestrator-danny/examples/
4. Submit a PR describing your changes

Suggested X (Twitter) post

"Meet Danny — a small, safe orchestrator + AI assistant scaffold for auditable automation. Submit JSON tasks, review pending approvals, and run actions only after human OK. See repo: https://github.com/aruntimalsinaa/Danny-Ai #AI #automation #opensource"

Feel free to adapt the post. Want me to tweet/post it for you or just keep it in the README?

