# Website Auditor

This repository contains a Python + OpenCode AI website audit project.

- `website_audit_collect.py` collects website text, titles, and link status.
- `.opencode/agents/website-auditor.md` defines the OpenCode agent prompt.
- `opencode_beginner_agent.py` sends goals to a running OpenCode server.
- `src/website_auditor/collector.py` contains the reusable website audit collector implementation.

## Quick start

1. Install Python 3.10+.
2. Run the collector:
   ```powershell
   python .\website_audit_collect.py
   ```
3. Start the OpenCode server from the repo root.
4. Run the OpenCode client:
   ```powershell
   python .\opencode_beginner_agent.py --agent website-auditor --prompt "Read website_audit_data.json and create the website audit report."
   ```

## Structure

- `src/website_auditor/` - reusable Python audit logic
- `website_audit_collect.py` - root wrapper to collect website data
- `.opencode/agents/website-auditor.md` - OpenCode agent definition
- `opencode_beginner_agent.py` - OpenCode client wrapper
- `docs/` - project documentation

## Notes

- Generated output files like `website_audit_data.json` and `website_audit_report*.md` should remain untracked unless you want sample data in Git.
- If the website requires login, set `AUDIT_WEBSITE_USERNAME` and `AUDIT_WEBSITE_PASSWORD` before running the collector.
