---
name: orchestrator-danny
description: Orchestrator for Danny AI — submit tasks as JSON, record approvals, and run safe, approved actions. Use when needing controlled, auditable automation (GitHub repo creation, file ops, scripted workflows).
---

# Orchestrator Danny Skill

This skill provides a minimal orchestrator that records tasks as pending approvals and runs approved tasks safely.

When to use
- Use this skill when you need to automate actions that must be auditable and require explicit human approval before running.

Included scripts
- scripts/run.py — record tasks as pending approvals
- scripts/approvals/approve.py — review and run pending tasks after approval
- scripts/list_pending.py — list pending tasks (added below)

References
- references/tasks.schema.json — JSON schema for tasks

Examples
- examples/create_repo_task.json — example create-repo task

