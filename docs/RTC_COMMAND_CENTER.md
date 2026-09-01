# RTC Command Center v2

This file defines the canonical operating framework for RustChain/Elyan RTC work.

## Objective
Maximize verified RTC received while minimizing wasted effort, duplicate work, blocked submissions, and owner labor.

## Evidence states
Every distinct economic deliverable must occupy exactly one highest-supported state:

1. BUILT — complete but not transmitted through an accepted route.
2. SUBMITTED — transmitted through the bounty's accepted route.
3. ACCEPTED_QUEUED — explicit maintainer approval or authoritative queue evidence.
4. PENDING_ONCHAIN — authoritative transaction/payout evidence says pending.
5. RECEIVED — authoritative final/confirmed receipt evidence.
6. REJECTED — maintainer explicitly declined or cap/eligibility conclusively failed.
7. SUPERSEDED — replaced by a later version of the same economic deliverable.
8. BLOCKED — not complete/submittable because of an external or access requirement.

Never infer a later state from an earlier one.

## Identity-link rule
A payout or adjudication counts only when the evidence links the row to our actual submission identity through at least one of:
- our GitHub account or PR/issue comment,
- our explicitly identified wallet name,
- our email submission thread,
- a maintainer comment referencing our exact deliverable,
- an authoritative payout-ledger row referencing our exact submission.

Rows belonging to other contributors are never included in our totals.

## Deduplication rule
Use one row per distinct economic deliverable. Revisions, retries, duplicate comments, resubmissions, and superseded versions do not create new RTC value.

## Candidate gate
Before any build, verify:
- issue is currently open/payable,
- authoritative title/body reward,
- remaining pool/cap/slot,
- active competing claims and duplicate risk,
- acceptance criteria,
- exact submission route,
- route is executable with authorized tools,
- current source state,
- expected acceptance probability,
- expected RTC per unit effort.

## Priority order
1. Convert already-delivered high-value work to ACCEPTED_QUEUED or RECEIVED when concrete new maintainer evidence exists.
2. New safe opportunities: 100+ RTC, 50-99, 20-49, then smaller only when unusually fast/stackable/high-certainty.
3. Never create speculative work merely because an issue has a large headline reward.

## Security classification
Security-labeled work is split into two classes rather than rejected wholesale.

### Allowed defensive/educational lane
May be considered when the task is limited to read-only architecture explanation, analysis of already-fixed code, secure coding, defensive remediation, dependency hygiene, validation, error handling, logging, CI regressions, or documentation. It must not require discovery or reproduction of a new exploit path.

### Excluded offensive lane
Do not perform vulnerability hunting, exploit development, fuzzing, auth bypass, privilege escalation, double-spend/fund attacks, fund-creation attacks, anti-fraud evasion, destructive/adversarial testing, or instructions designed to evade safeguards.

A multi-step bounty may be split. Safe educational tranches can be pursued independently when the issue explicitly pays them independently; excluded tranches remain excluded.

## Fund-movement exclusion
Do not sign, transfer, tip, bridge, trade, stake, fund escrow, or otherwise move RTC/funds. Read-only reconciliation is permitted.

## Submission routing
- Prefer official GitHub PR/issue/comment routes.
- If upstream write fails, use a writable authenticated fork and cross-repo PR when GitHub permits it.
- Email fallback is allowed only when the bounty explicitly authorizes email.
- A fork/local commit is BUILT, not SUBMITTED.
- A failed PR attempt does not advance accounting state.

## GitHub 403 recovery
When `Resource not accessible by integration` occurs:
1. Verify the fork is writable.
2. Create/refresh a topic branch in the fork.
3. Attempt a cross-repository PR with explicit head repository and head branch.
4. If still 403, classify `BLOCKED: GITHUB_INTEGRATION_SCOPE`.
5. Use an alternate route only if the bounty explicitly permits it.
6. Do not repeatedly retry without a material authentication/permission change.

## External-proof rule
Publication, social actions, stars/reactions, hardware runs, videos, screenshots, third-party approvals, and similar claims require genuine evidence. If the action cannot be completed with authorized tools, classify externally blocked and continue elsewhere.

## Communication rule
No generic follow-ups. Contact a maintainer only when there is a concrete new artifact, requested revision, contradictory ruling, explicit route/access question tied to completed work, or evidence requiring adjudication.

## TinyFish budget
Prefer free/direct tools. Paid TinyFish automation is allowed only for a concrete high-value action and remains under the existing cumulative RTC-effort hard cap. Log each paid run and remaining budget.

## Canonical totals
Report separately:
A Gross RTC-value work ever completed
B Net distinct RTC-value completed after dedupe/supersession
C Net RTC submitted
D Net RTC accepted/queued
E Net RTC pending on-chain
F Net RTC verified received
G RTC rejected/lost
H Completed RTC-value blocked from submission
I Unadjudicated submitted RTC exposure

## Decision rule
Expected Value = probability of acceptance × RTC reward − execution cost − owner-time burden − saturation risk − submission-route risk.

Prefer adjudicating existing completed work over starting a new task when its EV is higher.

End substantive runs with exactly one of [KILL], [HOLD], [MODIFY], [CONTINUE], or [SCALE].
