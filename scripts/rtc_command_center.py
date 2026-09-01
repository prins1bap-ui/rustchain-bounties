#!/usr/bin/env python3
"""Canonical RTC ledger validator and opportunity scorer.

This helper intentionally does not move funds, submit claims, or perform security testing.
It validates accounting invariants and ranks already-verified opportunity records.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class Status(str, Enum):
    BUILT = "BUILT"
    SUBMITTED = "SUBMITTED"
    ACCEPTED_QUEUED = "ACCEPTED_QUEUED"
    PENDING_ONCHAIN = "PENDING_ONCHAIN"
    RECEIVED = "RECEIVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    BLOCKED = "BLOCKED"


STAGE_RANK = {
    Status.BUILT: 0,
    Status.SUBMITTED: 1,
    Status.ACCEPTED_QUEUED: 2,
    Status.PENDING_ONCHAIN: 3,
    Status.RECEIVED: 4,
}


@dataclass(frozen=True)
class LedgerRow:
    key: str
    issue: str
    reward_rtc: float
    status: Status
    distinct_economic_deliverable: bool = True
    identity_linked: bool = False
    supersedes: str | None = None
    payout_evidence: str | None = None
    adjudication_evidence: str | None = None


@dataclass(frozen=True)
class Opportunity:
    key: str
    reward_rtc: float
    acceptance_probability: float
    effort_hours: float
    owner_minutes: float
    saturation_risk: float
    route_risk: float
    executable: bool
    safe: bool

    def expected_value(self) -> float:
        if not self.executable or not self.safe:
            return float("-inf")
        # RTC-denominated ranking heuristic. Risk terms are normalized penalties.
        return (
            self.acceptance_probability * self.reward_rtc
            - 0.75 * self.effort_hours
            - 0.02 * self.owner_minutes
            - self.reward_rtc * 0.35 * self.saturation_risk
            - self.reward_rtc * 0.35 * self.route_risk
        )


def validate_ledger(rows: Iterable[LedgerRow]) -> list[str]:
    errors: list[str] = []
    seen: dict[str, LedgerRow] = {}
    for row in rows:
        if row.key in seen:
            errors.append(f"duplicate ledger key: {row.key}")
        seen[row.key] = row

        if row.reward_rtc < 0:
            errors.append(f"negative reward: {row.key}")

        if row.status in {
            Status.ACCEPTED_QUEUED,
            Status.PENDING_ONCHAIN,
            Status.RECEIVED,
        } and not row.identity_linked:
            errors.append(
                f"identity evidence required before {row.status.value}: {row.key}"
            )

        if row.status == Status.PENDING_ONCHAIN and not row.payout_evidence:
            errors.append(f"pending requires payout evidence: {row.key}")

        if row.status == Status.RECEIVED and not row.payout_evidence:
            errors.append(f"received requires payout evidence: {row.key}")

        if row.status == Status.ACCEPTED_QUEUED and not row.adjudication_evidence:
            errors.append(f"accepted/queued requires adjudication evidence: {row.key}")

        if row.status == Status.SUPERSEDED and not row.supersedes:
            errors.append(f"superseded row must point to replacement: {row.key}")

    return errors


def totals(rows: Iterable[LedgerRow]) -> dict[str, float]:
    rows = list(rows)
    gross = sum(r.reward_rtc for r in rows if r.distinct_economic_deliverable)
    net_rows = [
        r
        for r in rows
        if r.distinct_economic_deliverable and r.status != Status.SUPERSEDED
    ]

    def total_for(status: Status) -> float:
        return sum(r.reward_rtc for r in net_rows if r.status == status)

    return {
        "gross_completed_value": gross,
        "net_distinct_value": sum(r.reward_rtc for r in net_rows),
        "submitted": total_for(Status.SUBMITTED),
        "accepted_queued": total_for(Status.ACCEPTED_QUEUED),
        "pending_onchain": total_for(Status.PENDING_ONCHAIN),
        "received": total_for(Status.RECEIVED),
        "rejected_lost": total_for(Status.REJECTED),
        "blocked": total_for(Status.BLOCKED),
    }


def rank_opportunities(opportunities: Iterable[Opportunity]) -> list[Opportunity]:
    return sorted(opportunities, key=lambda item: item.expected_value(), reverse=True)


if __name__ == "__main__":
    print("RTC command-center validator loaded. Supply verified ledger rows externally.")
