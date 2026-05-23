"""
Collect mechanical website audit data for the OpenCode website-auditor agent.

This script handles:
- optional login using environment variables
- same-domain crawling
- page title, text, and link extraction
- broken-link checks

The OpenCode agent should use the generated JSON file to review spelling and
content quality.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import HTTPCookieProcessor, Request, build_opener


DEFAULT_START_URL = "https://dbmissionyelagiri.org/"
DEFAULT_OUTPUT_FILE = "website_audit_data.json"
USER_AGENT = "WebsiteAuditCollector/1.0"


@dataclass
class LinkResult:
    url: str
    text: str
    source_page: str
    status: int | None
    ok: bool
    error: str | None = None


@dataclass
class PageResult:
    url: str
    final_url: str
    title: str
    text: str
    links: list[dict[str, str]]
    status: int
    error: str | None = None


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[dict[str, str]] = []
        self.forms: list[dict[str, Any]] = []
        self._current_link: dict[str, str] | None = None
        self._current_form: dict[str, Any] | None = None
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value or "" for key, value in attrs}

        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return

        if tag == "title":
            self._in_title = True
            return

        if tag == "a" and attrs_dict.get("href"):
            self._current_link = {
                "url": attrs_dict["href"],
                "text": "",
            }
            return

        if tag == "form":
            self._current_form = {
                "method": attrs_dict.get("method", "get").lower(),
                "action": attrs_dict.get("action", ""),
                "inputs": [],
            }
            return

        if tag == "input" and self._current_form is not None:
            self._current_form["inputs"].append(
                {
                    "name": attrs_dict.get("name", ""),
                    "type": attrs_dict.get("type", "text").lower(),
                    "value": attrs_dict.get("value", ""),
                }
            )

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return

        if tag == "title":
            self._in_title = False
            return

        if tag == "a" and self._current_link is not None:
            self._current_link["text"] = normalize_space(self._current_link["text"])
            self.links.append(self._current_link)
            self._current_link = None
            return

        if tag == "form" and self._current_form is not None:
            self.forms.append(self._current_form)
            self._current_form = None

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return

        if self._in_title:
            self.title_parts.append(data)

        if self._current_link is not None:
            self._current_link["text"] += data

        text = normalize_space(data)
        if text:
            self.text_parts.append(text)

    @property
    def title(self) -> str:
        return normalize_space(" ".join(self.title_parts))

    @property
    def text(self) -> str:
        return normalize_space(" ".join(self.text_parts))


class WebsiteAuditCollector:
    def __init__(self, start_url: str, max_pages: int, timeout: int) -> None:
        self.start_url = start_url
        self.max_pages = max_pages
        self.timeout = timeout
        self.cookie_jar = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))
        self.allowed_netloc = urlparse(start_url).netloc

    def fetch(self, url: str, method: str = "GET", data: dict[str, str] | None = None):
        encoded_data = None
        headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}

        if data is not None:
            encoded_data = urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        request = Request(url, data=encoded_data, headers=headers, method=method)
        return self.opener.open(request, timeout=self.timeout)

    def fetch_page(self, url: str) -> tuple[PageResult, PageParser | None]:
        try:
            with self.fetch(url) as response:
                final_url = response.geturl()
                status = response.status
                raw_html = response.read().decode("utf-8", errors="replace")
        except HTTPError as error:
            return (
                PageResult(
                    url=url,
                    final_url=error.url,
                    title="",
                    text="",
                    links=[],
                    status=error.code,
                    error=error.reason,
                ),
                None,
            )
        except URLError as error:
            return (
                PageResult(
                    url=url,
                    final_url=url,
                    title="",
                    text="",
                    links=[],
                    status=0,
                    error=str(error.reason),
                ),
                None,
            )

        parser = PageParser()
        parser.feed(raw_html)

        links = [
            {
                "url": normalize_url(urljoin(final_url, link["url"])),
                "text": link["text"],
            }
            for link in parser.links
            if is_http_url(urljoin(final_url, link["url"]))
        ]

        return (
            PageResult(
                url=url,
                final_url=final_url,
                title=parser.title or final_url,
                text=parser.text,
                links=links,
                status=status,
            ),
            parser,
        )

    def login_if_possible(self) -> dict[str, Any]:
        username = os.getenv("AUDIT_WEBSITE_USERNAME")
        password = os.getenv("AUDIT_WEBSITE_PASSWORD")

        if not username or not password:
            return {
                "attempted": False,
                "success": None,
                "message": "AUDIT_WEBSITE_USERNAME or AUDIT_WEBSITE_PASSWORD is not set.",
            }

        login_page, parser = self.fetch_page(self.start_url)
        if parser is None or not parser.forms:
            return {
                "attempted": True,
                "success": False,
                "message": "No login form was found on the start page.",
            }

        login_form = choose_login_form(parser.forms)
        if not login_form:
            return {
                "attempted": True,
                "success": False,
                "message": "No form with password input was found.",
            }

        form_data = build_login_payload(login_form, username, password)
        action = login_form.get("action") or login_page.final_url
        login_url = urljoin(login_page.final_url, action)
        method = login_form.get("method", "post").upper()

        try:
            with self.fetch(login_url, method=method, data=form_data) as response:
                final_url = response.geturl()
                status = response.status
                response.read()
        except HTTPError as error:
            return {
                "attempted": True,
                "success": False,
                "message": f"Login returned HTTP {error.code}: {error.reason}",
            }
        except URLError as error:
            return {
                "attempted": True,
                "success": False,
                "message": f"Login request failed: {error.reason}",
            }

        return {
            "attempted": True,
            "success": 200 <= status < 400,
            "message": f"Login request completed with HTTP {status}.",
            "final_url": final_url,
        }

    def crawl(self) -> list[PageResult]:
        seen: set[str] = set()
        queue = [normalize_url(self.start_url)]
        pages: list[PageResult] = []

        while queue and len(pages) < self.max_pages:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)

            page, _ = self.fetch_page(url)
            pages.append(page)

            for link in page.links:
                link_url = normalize_url(link["url"])
                if self.is_same_domain(link_url) and link_url not in seen and link_url not in queue:
                    queue.append(link_url)

        return pages

    def check_links(self, pages: list[PageResult]) -> list[LinkResult]:
        results: list[LinkResult] = []
        checked: dict[str, tuple[int | None, bool, str | None]] = {}

        for page in pages:
            for link in page.links:
                url = link["url"]

                if url not in checked:
                    checked[url] = self.check_single_link(url)

                status, ok, error = checked[url]
                results.append(
                    LinkResult(
                        url=url,
                        text=link["text"],
                        source_page=page.final_url,
                        status=status,
                        ok=ok,
                        error=error,
                    )
                )

        return results

    def check_single_link(self, url: str) -> tuple[int | None, bool, str | None]:
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT}, method="HEAD")
            with self.opener.open(request, timeout=self.timeout) as response:
                return response.status, 200 <= response.status < 400, None
        except HTTPError as error:
            return error.code, False, error.reason
        except URLError as error:
            return None, False, str(error.reason)

    def is_same_domain(self, url: str) -> bool:
        return urlparse(url).netloc == self.allowed_netloc


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    parsed = parsed._replace(fragment="")
    if parsed.path == "":
        parsed = parsed._replace(path="/")
    return urlunparse(parsed)


def is_http_url(url: str) -> bool:
    return urlparse(url).scheme in {"http", "https"}


def choose_login_form(forms: list[dict[str, Any]]) -> dict[str, Any] | None:
    for form in forms:
        if any(field.get("type") == "password" for field in form.get("inputs", [])):
            return form
    return None


def build_login_payload(form: dict[str, Any], username: str, password: str) -> dict[str, str]:
    payload: dict[str, str] = {}
    username_field = None
    password_field = None

    for field in form.get("inputs", []):
        name = field.get("name")
        field_type = field.get("type", "text")
        if not name:
            continue

        payload[name] = field.get("value", "")

        if field_type == "password":
            password_field = name
        elif username_field is None and field_type in {"email", "text"}:
            username_field = name

    if username_field:
        payload[username_field] = username
    if password_field:
        payload[password_field] = password

    return payload


def write_json(path: str, data: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect website audit data for the OpenCode website-auditor agent."
    )
    parser.add_argument(
        "--url",
        default=os.getenv("AUDIT_WEBSITE_URL", DEFAULT_START_URL),
        help=f"Starting website URL. Default: {DEFAULT_START_URL}",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=20,
        help="Maximum number of same-domain pages to crawl.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Request timeout in seconds.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_FILE,
        help=f"Output JSON file. Default: {DEFAULT_OUTPUT_FILE}",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    collector = WebsiteAuditCollector(args.url, args.max_pages, args.timeout)

    login = collector.login_if_possible()
    pages = collector.crawl()
    link_results = collector.check_links(pages)

    data = {
        "start_url": args.url,
        "login": login,
        "pages": [asdict(page) for page in pages],
        "link_checks": [asdict(result) for result in link_results],
    }

    write_json(args.output, data)

    broken_count = sum(1 for result in link_results if not result.ok)
    print(f"Wrote {args.output}")
    print(f"Pages collected: {len(pages)}")
    print(f"Links checked: {len(link_results)}")
    print(f"Broken/problem links: {broken_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
