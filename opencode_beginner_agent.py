"""
Beginner OpenCode AI agent example in Python.

This file talks to a local OpenCode server started with:

    opencode serve --port 4096

An AI agent is usually a loop:

    user goal -> model thinks -> agent may use tools -> agent sees results -> reply

OpenCode provides the agent, sessions, tools, permissions, and project context.
Your Python code is a small client that sends a goal and reads the answer.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:4096"


class OpenCodeClient:
    """Small HTTP client for the local OpenCode server."""

    def __init__(self, base_url: str, username: str | None, password: str | None):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> Any:
        data = None
        headers = {"Accept": "application/json"}

        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        if self.password:
            username = self.username or "opencode"
            token = base64.b64encode(f"{username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {token}"

        request = Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )

        with urlopen(request, timeout=120) as response:
            content = response.read().decode("utf-8")
            if not content:
                return None
            return json.loads(content)

    def health(self) -> dict[str, Any]:
        return self.request("GET", "/global/health")

    def list_agents(self) -> list[dict[str, Any]]:
        return self.request("GET", "/agent")

    def create_session(self, title: str) -> dict[str, Any]:
        return self.request("POST", "/session", {"title": title})

    def send_message(self, session_id: str, prompt: str, agent: str | None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "parts": [
                {
                    "type": "text",
                    "text": prompt,
                }
            ]
        }

        if agent:
            body["agent"] = agent

        return self.request("POST", f"/session/{session_id}/message", body)


def extract_text(message_response: dict[str, Any]) -> str:
    """Collect readable text parts from an OpenCode message response."""
    parts = message_response.get("parts", [])
    text_parts = [
        part.get("text", "")
        for part in parts
        if part.get("type") in {"text", "reasoning"} and part.get("text")
    ]
    return "\n".join(text_parts).strip()


def build_report_filename() -> str:
    """Create a report filename like website_audit_report_May-23_213045.md."""
    timestamp = datetime.now().strftime("%b-%d_%H%M%S")
    return f"website_audit_report_{timestamp}.md"


def prepare_prompt(args: argparse.Namespace) -> str:
    if args.agent != "website-auditor":
        return args.prompt

    report_file = args.report_file or build_report_filename()
    args.report_file = report_file
    return (
        f"{args.prompt}\n\n"
        f"Important: write the final markdown report to `{report_file}`. "
        "Do not write to `website_audit_report.md`."
    )


def run_agent(args: argparse.Namespace) -> int:
    client = OpenCodeClient(
        base_url=args.base_url,
        username=os.getenv("OPENCODE_SERVER_USERNAME"),
        password=os.getenv("OPENCODE_SERVER_PASSWORD"),
    )

    print("Connecting to OpenCode...")
    health = client.health()
    print(f"Server is healthy: {health.get('healthy')} | version: {health.get('version')}")

    print("\nListing available agents...")
    agents = client.list_agents()
    agent_names = [agent.get("name") or agent.get("id") for agent in agents]
    print("Agents:", ", ".join(str(name) for name in agent_names if name) or "(none returned)")

    if args.agent and args.agent not in agent_names:
        print(
            f"\nAgent '{args.agent}' is not loaded by OpenCode.",
            file=sys.stderr,
        )
        print(
            "Restart the OpenCode server from this project folder, then run this command again.",
            file=sys.stderr,
        )
        return 1

    print("\nCreating a new session...")
    session = client.create_session("Python beginner OpenCode agent")
    session_id = session["id"]
    print(f"Session created: {session_id}")

    prompt = prepare_prompt(args)
    if args.report_file:
        print(f"Report file: {args.report_file}")

    print("\nSending your goal to OpenCode...")
    response = client.send_message(session_id, prompt, args.agent)

    print("\nOpenCode response:")
    print(extract_text(response) or json.dumps(response, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Beginner Python client for an OpenCode AI agent."
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENCODE_BASE_URL", DEFAULT_BASE_URL),
        help=f"OpenCode server URL. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--agent",
        default=None,
        help="Optional OpenCode agent name, for example: build, plan, general, explore.",
    )
    parser.add_argument(
        "--prompt",
        default="Explain this project in one sentence. Do not edit files.",
        help="Goal to send to the OpenCode agent.",
    )
    parser.add_argument(
        "--report-file",
        default=None,
        help=(
            "Optional report filename for the website-auditor agent. "
            "Default: website_audit_report_MMM-DD_hhmmss.md"
        ),
    )
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args()

    try:
        return run_agent(args)
    except HTTPError as error:
        print(f"OpenCode returned HTTP {error.code}: {error.reason}", file=sys.stderr)
        print(error.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1
    except URLError as error:
        print("Could not connect to OpenCode.", file=sys.stderr)
        print(f"Details: {error.reason}", file=sys.stderr)
        print("\nStart OpenCode first:", file=sys.stderr)
        print("  opencode serve --port 4096", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
