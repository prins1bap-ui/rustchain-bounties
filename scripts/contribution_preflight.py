#!/usr/bin/env python3
"""Pre-submit checks for RustChain bounty contributions.

This tool deliberately fails closed on authoritative-state checks: an unavailable
or malformed GitHub response is an error, not a pass. It never submits claims,
creates PRs, or moves RTC.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

API_ROOT = "https://api.github.com"
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ISSUE_URL_RE = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/issues/(\d+)(?:[/?#].*)?$")
REWARD_TITLE_RE = re.compile(r"(?:BOUNTY|REWARD)[^\n\]]*?(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*RTC|(?:BOUNTY|REWARD)[^\n\]]*?(\d+(?:\.\d+)?)\s*RTC", re.I)
BODY_REWARD_RE = re.compile(r"(?:reward(?:\s+range)?|payout|worth)\s*[:=-]?\s*\**\s*(\d+(?:\.\d+)?)\s*(?:-|–|to)?\s*(\d+(?:\.\d+)?)?\s*RTC", re.I)
JUNK_PARTS = {"node_modules", "__pycache__", ".DS_Store"}
JUNK_SUFFIXES = {".pyc", ".pyo"}


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


class GitHubClient:
    def __init__(self, token: str | None = None, timeout: int = 12) -> None:
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.timeout = timeout

    def get_json(self, path: str, params: dict[str, str] | None = None) -> Any:
        if not path.startswith("/"):
            raise ValueError("GitHub API path must begin with '/'")
        url = API_ROOT + path
        if params:
            url += "?" + urlencode(params)
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "rustchain-contribution-preflight/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            raise RuntimeError(f"GitHub API HTTP {exc.code} for {path}") from exc
        except URLError as exc:
            raise RuntimeError(f"GitHub API unavailable for {path}: {exc.reason}") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RuntimeError(f"GitHub API returned malformed JSON for {path}") from exc


def parse_repo(value: str) -> str:
    value = value.strip()
    if not REPO_RE.fullmatch(value):
        raise ValueError("repository must be in owner/name form")
    return value


def parse_issue(value: str) -> tuple[str, int]:
    value = value.strip()
    match = ISSUE_URL_RE.fullmatch(value)
    if match:
        return parse_repo(f"{match.group(1)}/{match.group(2)}"), int(match.group(3))
    if "#" in value:
        repo, number = value.rsplit("#", 1)
        repo = parse_repo(repo)
        if not number.isdigit() or int(number) < 1:
            raise ValueError("issue number must be a positive integer")
        return repo, int(number)
    raise ValueError("issue must be a GitHub issue URL or owner/repo#number")


def parse_reward(text: str, *, title: bool) -> tuple[float, float] | None:
    regex = REWARD_TITLE_RE if title else BODY_REWARD_RE
    match = regex.search(text or "")
    if not match:
        return None
    groups = match.groups()
    if title:
        if groups[0] is not None:
            return float(groups[0]), float(groups[1])
        return float(groups[2]), float(groups[2])
    low = float(groups[0])
    high = float(groups[1]) if groups[1] is not None else low
    return min(low, high), max(low, high)


def check_issue_state(issue: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    state = str(issue.get("state", "")).lower()
    checks.append(Check("issue_state", "pass" if state == "open" else "fail", f"issue state is {state or 'unknown'}"))

    labels = {str(label.get("name", "")).casefold() for label in issue.get("labels", []) if isinstance(label, dict)}
    if "bounty" in labels:
        checks.append(Check("bounty_label", "pass", "issue carries the bounty label"))
    else:
        checks.append(Check("bounty_label", "review", "issue is not labeled bounty; verify payment authority manually"))

    title_reward = parse_reward(str(issue.get("title", "")), title=True)
    body_reward = parse_reward(str(issue.get("body", "")), title=False)
    if title_reward:
        detail = f"title advertises {title_reward[0]:g}-{title_reward[1]:g} RTC" if title_reward[0] != title_reward[1] else f"title advertises {title_reward[0]:g} RTC"
        checks.append(Check("title_reward", "pass", detail))
    else:
        checks.append(Check("title_reward", "review", "no RTC amount parsed from title"))
    if title_reward and body_reward and title_reward != body_reward:
        checks.append(Check("reward_drift", "review", f"title reward {title_reward[0]:g}-{title_reward[1]:g} differs from body reward {body_reward[0]:g}-{body_reward[1]:g}; use the issue's stated source-of-truth rule"))
    else:
        checks.append(Check("reward_drift", "pass", "no parsed title/body reward conflict"))
    return checks


def normalize_paths(paths: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for raw in paths:
        path = raw.strip().replace("\\", "/")
        while path.startswith("./"):
            path = path[2:]
        if not path:
            continue
        if path.startswith("/") or ".." in path.split("/"):
            raise ValueError(f"unsafe repository path: {raw!r}")
        normalized.append(path)
    return normalized


def check_changed_paths(paths: Iterable[str]) -> Check:
    offenders: list[str] = []
    for path in normalize_paths(paths):
        parts = path.split("/")
        if any(part in JUNK_PARTS for part in parts) or any(path.endswith(suffix) for suffix in JUNK_SUFFIXES):
            offenders.append(path)
    if offenders:
        return Check("artifact_hygiene", "fail", "remove generated/bulky artifacts: " + ", ".join(offenders[:8]))
    return Check("artifact_hygiene", "pass", "no blocked generated/bulky artifact paths detected")


def check_referenced_paths(client: GitHubClient, repo: str, paths: Iterable[str]) -> Check:
    missing: list[str] = []
    checked = normalize_paths(paths)
    for path in checked:
        owner, name = repo.split("/", 1)
        api_path = f"/repos/{quote(owner)}/{quote(name)}/contents/{quote(path, safe='/')}"
        try:
            client.get_json(api_path)
        except RuntimeError as exc:
            if "HTTP 404" in str(exc):
                missing.append(path)
            else:
                return Check("referenced_paths", "error", str(exc))
    if missing:
        return Check("referenced_paths", "fail", "referenced upstream paths do not exist: " + ", ".join(missing[:8]))
    if not checked:
        return Check("referenced_paths", "review", "no upstream reference paths supplied")
    return Check("referenced_paths", "pass", f"verified {len(checked)} referenced upstream path(s)")


def check_duplicate_prs(client: GitHubClient, target_repo: str, bounty_number: int, *, claimant: str | None = None) -> Check:
    query = f'repo:{target_repo} is:pr "{bounty_number}"'
    try:
        result = client.get_json("/search/issues", {"q": query, "per_page": "20"})
    except RuntimeError as exc:
        return Check("duplicate_pr_scan", "error", str(exc))
    items = result.get("items", []) if isinstance(result, dict) else []
    if claimant:
        claimant_cf = claimant.casefold().lstrip("@")
        items = [item for item in items if str(item.get("user", {}).get("login", "")).casefold() != claimant_cf]
    if items:
        examples = ", ".join(f"#{item.get('number')} {item.get('title', '')}" for item in items[:5])
        return Check("duplicate_pr_scan", "review", f"found {len(items)} PR(s) mentioning bounty number; inspect before building: {examples}")
    return Check("duplicate_pr_scan", "pass", "no PRs mentioning the bounty number found in the target repo")


def run_preflight(client: GitHubClient, issue_ref: str, target_repo: str, changed_paths: Iterable[str], referenced_paths: Iterable[str], claimant: str | None = None) -> list[Check]:
    issue_repo, issue_number = parse_issue(issue_ref)
    target_repo = parse_repo(target_repo)
    owner, repo = issue_repo.split("/", 1)
    try:
        issue = client.get_json(f"/repos/{quote(owner)}/{quote(repo)}/issues/{issue_number}")
    except RuntimeError as exc:
        return [Check("issue_fetch", "error", str(exc))]
    if not isinstance(issue, dict) or "pull_request" in issue:
        return [Check("issue_fetch", "error", "reference did not resolve to a GitHub issue")]
    checks = check_issue_state(issue)
    checks.append(check_changed_paths(changed_paths))
    checks.append(check_referenced_paths(client, target_repo, referenced_paths))
    checks.append(check_duplicate_prs(client, target_repo, issue_number, claimant=claimant))
    return checks


def render_text(checks: Iterable[Check]) -> str:
    symbols = {"pass": "PASS", "review": "REVIEW", "fail": "FAIL", "error": "ERROR"}
    return "\n".join(f"[{symbols.get(check.status, check.status.upper())}] {check.name}: {check.detail}" for check in checks)


def exit_code(checks: Iterable[Check]) -> int:
    statuses = {check.status for check in checks}
    if "error" in statuses:
        return 2
    if "fail" in statuses:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fail-closed preflight checks for RustChain bounty contributions")
    parser.add_argument("--issue", required=True, help="GitHub issue URL or owner/repo#number")
    parser.add_argument("--target-repo", required=True, help="repository the contribution will modify, owner/name")
    parser.add_argument("--changed-path", action="append", default=[], help="planned/changed path; repeat as needed")
    parser.add_argument("--reference-path", action="append", default=[], help="upstream path referenced by the submission; repeat as needed")
    parser.add_argument("--claimant", help="GitHub login; own PRs are excluded from duplicate warnings")
    parser.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        checks = run_preflight(GitHubClient(), args.issue, args.target_repo, args.changed_path, args.reference_path, claimant=args.claimant)
    except ValueError as exc:
        checks = [Check("input", "error", str(exc))]
    if args.json_output:
        print(json.dumps({"checks": [asdict(check) for check in checks], "exit_code": exit_code(checks)}, indent=2))
    else:
        print(render_text(checks))
    return exit_code(checks)


if __name__ == "__main__":
    raise SystemExit(main())
