#!/usr/bin/env python3
"""GitHub issue_comment adapter for RustChain bounty #747.

Processes claim-like comments on issues labeled `bounty`, verifies the public/read-only
signals requested by #747, and posts one deduplicated verification comment. It never
executes payments or mutates wallets.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

from verifier import verify

KEYWORDS = ("claiming", "wallet:", "rtc wallet:", "miner_id:", "stars:", "github:", "submitted", "/claim")
BOT_MARKER = "<!-- rustchain-bounty-verifier -->"


def github_json(url: str, token: str, method: str = "GET", payload=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "rustchain-bounty-verifier/1.2",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read()
        return json.loads(body.decode("utf-8")) if body else None


def fetch_all_comments(api_url: str, token: str) -> list[dict]:
    comments: list[dict] = []
    page = 1
    while True:
        separator = "&" if "?" in api_url else "?"
        batch = github_json(f"{api_url}{separator}per_page=100&page={page}", token)
        if not isinstance(batch, list):
            return comments
        comments.extend(batch)
        if len(batch) < 100:
            return comments
        page += 1


def should_process(event: dict) -> bool:
    issue = event.get("issue") or {}
    labels = {str(item.get("name") or "").lower() for item in (issue.get("labels") or [])}
    if "bounty" not in labels:
        return False
    comment = event.get("comment") or {}
    body = comment.get("body") or ""
    sender_type = ((comment.get("user") or {}).get("type") or "User").lower()
    if sender_type == "bot" or BOT_MARKER in body:
        return False
    text = body.lower()
    return any(keyword in text for keyword in KEYWORDS)


def run(event: dict, token: str, node_url: str) -> int:
    if not should_process(event):
        print("Not a claim-like comment on a bounty issue; skipping.")
        return 0

    comment = event.get("comment") or {}
    claimant = ((comment.get("user") or {}).get("login") or "").strip()
    body = comment.get("body") or ""
    comments_url = (event.get("issue") or {}).get("comments_url")
    if not claimant or not comments_url:
        raise ValueError("Event is missing claimant login or issue comments_url")

    history = fetch_all_comments(comments_url, token)
    source_id = str(comment.get("id") or "")
    dedupe_marker = f"<!-- source-comment:{source_id} -->" if source_id else ""
    if dedupe_marker and any(dedupe_marker in (item.get("body") or "") for item in history):
        print("Verification for this source comment already exists; skipping.")
        return 0

    result = verify(claimant, body, token, history, node_url or "https://rustchain.org")
    rendered = BOT_MARKER + "\n" + result.to_markdown()
    if dedupe_marker:
        rendered += "\n" + dedupe_marker
    github_json(comments_url, token, method="POST", payload={"body": rendered})
    print(rendered)
    return 0


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    token = os.environ.get("GITHUB_TOKEN")
    node_url = os.environ.get("RUSTCHAIN_NODE_URL") or "https://rustchain.org"
    if not event_path or not token:
        print("GITHUB_EVENT_PATH and GITHUB_TOKEN are required", file=sys.stderr)
        return 2
    with open(event_path, "r", encoding="utf-8") as handle:
        event = json.load(handle)
    return run(event, token, node_url)


if __name__ == "__main__":
    raise SystemExit(main())
