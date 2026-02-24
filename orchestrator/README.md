# Orchestrator (Danny-Ai)

This directory contains a minimal scaffold for an agent orchestrator that can accept JSON tasks and run them using the available workspace tools. It's a safe, incremental starting point for integrating an orchestrator with Danny (the AI assistant).

Files:
- run.py — orchestrator engine (stub)
- tasks/schema.json — task schema
- approvals/ — (created at runtime) pending approval requests
- logs/ — (created at runtime) task run logs
- examples/create_repo_task.json — example task to create a GitHub repo and push a README

Usage: see run.py docstring. This scaffold does not run privileged actions by itself — approvals are required before host or network operations.
