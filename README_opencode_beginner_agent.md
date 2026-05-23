# OpenCode AI Agent Python Sample

This project includes `opencode_beginner_agent.py`, a small Python client that talks to a real local OpenCode server.

## How It Works

OpenCode runs the AI agent. The Python file only sends requests to OpenCode and prints the result.

The flow is:

1. Start the OpenCode server.
2. Python checks that the server is healthy.
3. Python lists available OpenCode agents.
4. Python creates a new OpenCode session.
5. Python sends your prompt to the selected agent.
6. OpenCode runs the agent and sends the response back.

## Requirements

- Python installed.
- OpenCode installed.
- OpenCode configured with an AI provider/model.

## Run The Example

Open one terminal and start the OpenCode server:

```powershell
opencode serve --port 4096
```

Open a second terminal in this project folder and run:

```powershell
python .\opencode_beginner_agent.py --prompt "Explain this project in one sentence. Do not edit files."
```

## Choose An Agent

You can pass an OpenCode agent name with `--agent`:

```powershell
python .\opencode_beginner_agent.py --agent plan --prompt "Look at this project and describe the files."
```

Common examples are `plan`, `build`, `general`, or `explore`, depending on your OpenCode configuration.

## Use A Different Server URL

The default server URL is `http://127.0.0.1:4096`.

To use another URL:

```powershell
python .\opencode_beginner_agent.py --base-url "http://127.0.0.1:5000" --prompt "Explain this project."
```

## Use A Server Password

If you started OpenCode with `OPENCODE_SERVER_PASSWORD`, set the same password before running the Python script:

```powershell
$env:OPENCODE_SERVER_PASSWORD = "your-password"
python .\opencode_beginner_agent.py --prompt "Explain this project."
```

If you also changed the username, set `OPENCODE_SERVER_USERNAME`:

```powershell
$env:OPENCODE_SERVER_USERNAME = "my-user"
$env:OPENCODE_SERVER_PASSWORD = "your-password"
python .\opencode_beginner_agent.py --prompt "Explain this project."
```
