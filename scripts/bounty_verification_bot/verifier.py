#!/usr/bin/env python3
"""Read-only verifier for RustChain bounty claims.

This module never executes payments, transfers, wallet writes, escrow, settlement,
or claim mutations. It only gathers public/read-only evidence for maintainer review.
"""
from __future__ import annotations

import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable, Optional

UA = "rustchain-bounty-verifier/1.2"
DEFAULT_NODE = "https://rustchain.org"
PAID_KEYS = ("paid", "queued", "payout", "pending_id", "transaction", "txid", "settled")


@dataclass
class Check:
    name: str
    ok: Optional[bool]
    detail: str


@dataclass
class Verification:
    claimant: str
    wallet: Optional[str]
    checks: list[Check]
    suggested_rtc: int

    def to_markdown(self) -> str:
        rows = []
        for check in self.checks:
            icon = "✅" if check.ok is True else "❌" if check.ok is False else "⚪"
            rows.append(f"| {check.name} | {icon} {check.detail} |")
        return (
            f"## Automated Verification for @{self.claimant}\n\n"
            "| Check | Result |\n|---|---|\n"
            + "\n".join(rows)
            + f"\n\n**Suggested payout basis:** {self.suggested_rtc} RTC\n\n"
            "> Read-only verification only. Human maintainer approval is required; this bot never executes payment."
        )


def request(url: str, token: Optional[str] = None, method: str = "GET", timeout: int = 15):
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    req = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError:
        return 0, b""


def follows_target(user: str, target: str, token: Optional[str]) -> Check:
    url = f"https://api.github.com/users/{urllib.parse.quote(user)}/following/{urllib.parse.quote(target)}"
    status, _ = request(url, token)
    if status == 204:
        return Check("Follows @" + target, True, "Yes")
    if status == 404:
        return Check("Follows @" + target, False, "No")
    return Check("Follows @" + target, None, f"Unable to verify (HTTP {status or 'network error'})")


def count_owner_stars(user: str, owner: str, token: Optional[str], max_pages: int = 10) -> tuple[Check, int]:
    count = 0
    for page in range(1, max_pages + 1):
        url = f"https://api.github.com/users/{urllib.parse.quote(user)}/starred?per_page=100&page={page}"
        status, body = request(url, token)
        if status != 200:
            return Check(f"{owner} repos starred", None, f"Unable to verify (HTTP {status or 'network error'})"), count
        items = json.loads(body.decode("utf-8"))
        count += sum(1 for item in items if (item.get("owner") or {}).get("login", "").lower() == owner.lower())
        if len(items) < 100:
            break
    return Check(f"{owner} repos starred", count > 0, str(count)), count


def wallet_exists(wallet: Optional[str], node_url: str) -> Check:
    if not wallet:
        return Check("Wallet existence", None, "No wallet found in claim")
    base = (node_url or DEFAULT_NODE).rstrip("/")
    query = urllib.parse.urlencode({"miner_id": wallet})
    candidates = [f"{base}/wallet/balance?{query}", f"{base}/api/wallet/balance?{query}"]
    last = 0
    for url in candidates:
        status, body = request(url)
        last = status
        if status == 200:
            text = body.decode("utf-8", "replace")
            try:
                data = json.loads(text)
                if isinstance(data, dict) and data.get("ok") is not False:
                    balance = data.get("balance", data.get("rtc_balance", data.get("amount")))
                    detail = "Exists" + (f"; balance={balance}" if balance is not None else "")
                    return Check("Wallet existence", True, detail)
            except json.JSONDecodeError:
                return Check("Wallet existence", True, "Endpoint returned HTTP 200")
        if status not in (400, 404):
            break
    return Check("Wallet existence", False if last in (400, 404) else None, f"Not verified (HTTP {last or 'network error'})")


def proof_url(text: str) -> Optional[str]:
    urls = re.findall(r"https?://[^\s>)\]]+", text or "")
    return urls[0].rstrip(".,") if urls else None


def wallet_from_claim(text: str) -> Optional[str]:
    match = re.search(r"\bRTC[a-fA-F0-9]{40}\b", text or "")
    if match:
        return match.group(0)
    match = re.search(r"(?im)^\s*(?:rtc\s+wallet|wallet|miner_id)\s*:\s*`?([^\s`]+)", text or "")
    return match.group(1).strip() if match else None


def url_liveness(url: Optional[str]) -> Check:
    if not url:
        return Check("Proof URL", None, "No proof URL found")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return Check("Proof URL", False, "Unsupported URL scheme")
    status, _ = request(url, method="HEAD")
    if status in (0, 403, 405) or status >= 500:
        status, _ = request(url, method="GET")
    return Check("Proof URL", 200 <= status < 400, f"HTTP {status or 'network error'}")


def article_word_count(url: Optional[str]) -> Check:
    if not url:
        return Check("Article word count", None, "No article URL found")
    host = urllib.parse.urlparse(url).netloc.lower()
    if not any(domain in host for domain in ("dev.to", "medium.com")):
        return Check("Article word count", None, "Not a Dev.to/Medium URL")
    status, body = request(url)
    if status != 200:
        return Check("Article word count", False, f"HTTP {status or 'network error'}")
    text = body.decode("utf-8", "replace")
    text = re.sub(r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    words = re.findall(r"\b[\w’'-]+\b", html.unescape(text))
    return Check("Article word count", len(words) >= 500, f"~{len(words)} words")


def prior_payment_markers(comments: Iterable[dict], claimant: str, wallet: Optional[str]) -> Check:
    claimant_l = claimant.lower()
    wallet_l = wallet.lower() if wallet else None
    hits = 0
    for comment in comments:
        body = (comment.get("body") or "").lower()
        user = ((comment.get("user") or {}).get("login") or "").lower()
        references = user == claimant_l or f"@{claimant_l}" in body or (wallet_l and wallet_l in body)
        if references and any(key in body for key in PAID_KEYS):
            hits += 1
    if hits:
        return Check("Prior payment markers", False, f"Found {hits} possible prior payout marker(s)")
    return Check("Prior payment markers", True, "No matching payout marker found in issue history")


def verify(user: str, claim_text: str, token: Optional[str], comments: list[dict], node_url: str, target: str = "Scottcjn") -> Verification:
    wallet = wallet_from_claim(claim_text)
    proof = proof_url(claim_text)
    follow = follows_target(user, target, token)
    stars, _ = count_owner_stars(user, target, token)
    wallet_check = wallet_exists(wallet, node_url)
    live = url_liveness(proof)
    words = article_word_count(proof)
    duplicate = prior_payment_markers(comments, user, wallet)
    score = 0
    if follow.ok is True and stars.ok is True:
        score += 30
    if wallet_check.ok is True:
        score += 10
    if live.ok is True:
        score += 10
    if words.ok is True:
        score += 10
    if duplicate.ok is True:
        score += 15
    return Verification(user, wallet, [follow, stars, wallet_check, live, words, duplicate], score)
