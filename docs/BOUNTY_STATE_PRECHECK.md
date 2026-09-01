# Bounty State Precheck

Use this precheck before spending time on an RTC bounty. It is designed to catch stale issue bodies, exhausted pools, duplicate work, and submission routes that cannot actually be completed.

## 1. Read the current issue, not a cached summary

Confirm the issue is still open and read its current title, body, labels, and latest maintainer comments.

For Elyan Labs bounties, the **current issue title is authoritative for the reward amount** when an older body shows a conflicting figure. Do not estimate a payout from a stale body value.

## 2. Confirm the bounty is still payable

Check for all of the following before starting:

- the issue is open;
- the bounty has not been retired, replaced, or declared exhausted;
- any pool, per-person cap, or slot cap still has room;
- the required deliverable has not already been accepted from another contributor;
- a current claim does not make duplicate work irrational.

An open GitHub issue is not, by itself, proof that payment remains available.

## 3. Check recent claims and competing work

Read recent issue comments and search linked pull requests before implementation. Look for:

- active `/claim` holders and expiration dates;
- already-submitted implementations;
- maintainer comments naming a winner or accepted submission;
- multiple equivalent PRs waiting for review;
- weekly or per-person caps already reached.

Claims are usually courtesy signals rather than payment reservations, but they are still important duplicate-work evidence.

## 4. Verify the submission route before building

Make sure the required submission route is available with your tooling.

For file-based work, a normal fork workflow is:

1. fork the target repository;
2. create a focused branch;
3. make and validate the change;
4. open a pull request from the fork into the upstream default branch.

If issue-comment writes return `403 Resource not accessible by integration`, do not silently treat the work as submitted. Use an explicitly accepted fallback route from the bounty instructions, such as an upstream pull request or the documented project email fallback when allowed.

## 5. Verify acceptance criteria against current source

Before editing code or documentation, verify every referenced path, command, endpoint, and dependency against the current repository state. Do not rely on filenames or behavior quoted in old comments if the source has changed.

For code changes, include reproducible validation. For documentation-only changes, verify links, commands, paths, and factual claims against primary repository sources.

## 6. Record the accounting stage correctly

Keep these stages separate:

`BUILT` → `SUBMITTED` → `ACCEPTED/QUEUED` → `PENDING ON-CHAIN` → `RECEIVED`

Do not count a completed local deliverable as submitted, a submitted PR as accepted, or an accepted claim as received RTC without authoritative evidence for that stage.

## Minimal go/no-go record

Before beginning a bounty, record:

```text
Issue: #...
Current title reward: ... RTC
Issue state: open/closed
Pool/cap/slots remaining: ...
Active claims or equivalent PRs: ...
Acceptance criteria: ...
Submission route: ...
Current-source checks completed: ...
Decision: GO / SKIP / EXTERNALLY BLOCKED
```

This takes a few minutes and is cheaper than completing a perfectly good solution to a bounty that stopped being payable yesterday.
