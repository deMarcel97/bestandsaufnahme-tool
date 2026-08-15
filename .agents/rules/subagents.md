# Agent & Subagent Guidelines

- **Subagents Auto-Approve**: Subagents must always be launched with `--auto-approve` / non-interactive execution mode enabled to prevent interactive permission prompt timeouts on tool/command executions.
- **Workflow & Testing**: Every change must be verified with `PYTHONPATH=. venv/bin/pytest` and documented in `CHANGELOG.md`, `README.md`, and `TODO.md`.
