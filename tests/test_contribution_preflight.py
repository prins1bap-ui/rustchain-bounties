import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import contribution_preflight as cp


class FakeClient:
    def __init__(self, issue=None, existing_paths=(), pr_items=()):
        self.issue = issue or {
            "state": "open",
            "title": "[BOUNTY: 15 RTC] Example",
            "body": "Reward: 15 RTC",
            "labels": [{"name": "bounty"}],
        }
        self.existing_paths = set(existing_paths)
        self.pr_items = list(pr_items)

    def get_json(self, path, params=None):
        if path.endswith("/issues/42"):
            return self.issue
        if path == "/search/issues":
            return {"items": self.pr_items}
        if "/contents/" in path:
            repo_path = path.split("/contents/", 1)[1]
            if repo_path not in self.existing_paths:
                raise RuntimeError(f"GitHub API HTTP 404 for {path}")
            return {"path": repo_path}
        raise AssertionError(path)


class PreflightTests(unittest.TestCase):
    def test_parse_issue_variants(self):
        self.assertEqual(cp.parse_issue("Scottcjn/rustchain-bounties#42"), ("Scottcjn/rustchain-bounties", 42))
        self.assertEqual(cp.parse_issue("https://github.com/Scottcjn/rustchain-bounties/issues/42"), ("Scottcjn/rustchain-bounties", 42))

    def test_closed_issue_fails(self):
        issue = {"state": "closed", "title": "[BOUNTY: 5 RTC] x", "body": "Reward: 5 RTC", "labels": [{"name": "bounty"}]}
        checks = cp.run_preflight(FakeClient(issue=issue), "Scottcjn/rustchain-bounties#42", "Scottcjn/Rustchain", [], [])
        self.assertEqual(next(c for c in checks if c.name == "issue_state").status, "fail")
        self.assertEqual(cp.exit_code(checks), 1)

    def test_reward_drift_requires_review(self):
        issue = {"state": "open", "title": "[BOUNTY: 7 RTC] x", "body": "Reward: 10 RTC", "labels": [{"name": "bounty"}]}
        checks = cp.check_issue_state(issue)
        drift = next(c for c in checks if c.name == "reward_drift")
        self.assertEqual(drift.status, "review")

    def test_junk_artifacts_fail(self):
        check = cp.check_changed_paths(["src/app.py", "node_modules/pkg/index.js", "build/x.pyc"])
        self.assertEqual(check.status, "fail")
        self.assertIn("node_modules", check.detail)

    def test_missing_reference_fails(self):
        client = FakeClient(existing_paths={"node/main.py"})
        check = cp.check_referenced_paths(client, "Scottcjn/Rustchain", ["node/main.py", "fake.py"])
        self.assertEqual(check.status, "fail")
        self.assertIn("fake.py", check.detail)

    def test_duplicate_pr_is_review_not_false_rejection(self):
        client = FakeClient(pr_items=[{"number": 88, "title": "Bounty 42 solution", "user": {"login": "other"}}])
        check = cp.check_duplicate_prs(client, "Scottcjn/Rustchain", 42, claimant="me")
        self.assertEqual(check.status, "review")
        self.assertIn("#88", check.detail)

    def test_happy_path(self):
        client = FakeClient(existing_paths={"node/main.py"})
        checks = cp.run_preflight(client, "Scottcjn/rustchain-bounties#42", "Scottcjn/Rustchain", ["docs/guide.md"], ["node/main.py"], claimant="me")
        self.assertEqual(cp.exit_code(checks), 0)
        self.assertFalse(any(c.status in {"fail", "error"} for c in checks))

    def test_unsafe_path_rejected(self):
        with self.assertRaises(ValueError):
            cp.normalize_paths(["../secret"])


if __name__ == "__main__":
    unittest.main()
