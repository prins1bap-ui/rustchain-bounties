# Contribution Preflight

`contribution_preflight.py` turns the RustChain bounty submission guide's most common rejection causes into a repeatable, fail-closed check before a contributor spends time on a PR.

It does **not** claim bounties, submit pull requests, approve payouts, or move RTC. It reads public GitHub state and reports blockers/review warnings.

## Checks

- Confirms the bounty issue still resolves and is open.
- Notes whether the issue carries the `bounty` label.
- Parses the title RTC value and flags detectable title/body reward drift for manual source-of-truth review.
- Rejects accidental `node_modules`, `__pycache__`, `.pyc`, `.pyo`, and `.DS_Store` paths.
- Verifies explicitly referenced upstream paths actually exist through GitHub's Contents API.
- Searches the target repository for PRs mentioning the same bounty number and treats matches as a **review warning**, not a false automatic rejection.
- Emits text or JSON and stable exit codes for agent/CI use.

## Usage

```bash
python scripts/contribution_preflight.py \
  --issue Scottcjn/rustchain-bounties#1524 \
  --target-repo Scottcjn/Rustchain \
  --changed-path site/beacon/ui.js \
  --reference-path site/beacon/ui.js \
  --claimant your-github-login
```

Machine-readable output:

```bash
python scripts/contribution_preflight.py ... --json
```

`GITHUB_TOKEN` is optional for public repositories but recommended to avoid anonymous API rate limits.

## Exit codes

- `0`: no hard failure; `REVIEW` warnings may still require human judgment.
- `1`: a hard preflight failure was found, such as a closed issue, missing referenced path, or blocked generated artifact.
- `2`: authoritative state could not be verified because of invalid input or a GitHub API/network error.

## Why this exists

The repository's submission guide documents repeated closures caused by stale bounty state, hallucinated file paths, unrelated/bulky artifacts, and duplicate work. This utility moves those checks before implementation so agents and humans can fail cheaply instead of shipping an avoidable rejection.
