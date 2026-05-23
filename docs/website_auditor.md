# Website Auditor Agent

This sample uses two parts:

1. `website_audit_collect.py` collects facts from the website.
2. `.opencode/agents/website-auditor.md` reviews those facts and writes the final report.

The collector checks login, pages, extracted text, and link status codes. The agent focuses on spelling issues and content improvement suggestions.

## Environment Variables

If the website requires login, set these in PowerShell:

```powershell
$env:AUDIT_WEBSITE_USERNAME = "your-user-name"
$env:AUDIT_WEBSITE_PASSWORD = "your-password"
```

The default website is:

```text
https://dbmissionyelagiri.org/
```

To use another website:

```powershell
$env:AUDIT_WEBSITE_URL = "https://example.com/"
```

## Step 1: Collect Website Data

Run:

```powershell
python .\website_audit_collect.py
```

This creates:

```text
website_audit_data.json
```

You can also control the crawl size:

```powershell
python .\website_audit_collect.py --max-pages 30
```

## Step 2: Ask OpenCode Agent To Review

Start OpenCode from this project folder:

```powershell
cd C:\AI_Projects\FundTree\Website
& "C:\Users\user\AppData\Roaming\npm\node_modules\opencode-ai\bin\opencode.exe" --log-level DEBUG serve --port 4096
```

Start OpenCode from this project folder so it can load:

```text
.opencode/agents/website-auditor.md
```

If you add or change an agent file, stop and restart the OpenCode server.

Then ask the custom agent to review the collected JSON:

```powershell
python .\opencode_beginner_agent.py --agent website-auditor --prompt "Read website_audit_data.json and create the website audit report."
```

The Python client automatically asks the agent to save the report with this filename pattern:

```text
website_audit_report_MMM-DD_hhmmss.md
```

Example:

```text
website_audit_report_May-23_213045.md
```

To choose your own filename:

```powershell
python .\opencode_beginner_agent.py --agent website-auditor --report-file "website_audit_report_custom.md" --prompt "Read website_audit_data.json and create the website audit report."
```

## Expected Report

The agent should report issues grouped by page:

```markdown
## Page Name
URL: https://example.com/page

### Spelling Issues
- Issue:
  Suggestion:

### Broken Links
- Link:
  Status:
  Source:

### Content Improvements
- Issue:
  Suggestion:
```

The report should not include passwords, cookies, tokens, or session values.
