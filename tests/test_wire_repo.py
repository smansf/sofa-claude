"""Tests for bootstrap's repo wiring and its protection probe.

The property under test is that wiring reports what GitHub *enforces*,
not what its APIs accepted — a 201 from the rulesets endpoint means a
ruleset was recorded, not that a branch is protected. On the free plan a
private repo gets no rulesets at all, so "unprotected" is a normal
outcome; the requirement is that it can never be a quiet one.
"""

import importlib.util
import io
import json
import pathlib
import sys
import unittest
from unittest import mock

_path = (pathlib.Path(__file__).resolve().parent.parent
         / ".claude" / "skills" / "bootstrap" / "wire_repo.py")
_spec = importlib.util.spec_from_file_location("wire_repo", _path)
wire_repo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wire_repo)


class ProbeTests(unittest.TestCase):
    """The probe must create nothing, whichever answer it gets."""

    def _probe(self, patch_status, patch_detail=""):
        calls = []

        def fake_call(token, method, path, payload=None):
            calls.append((method, path, payload))
            if method == "GET":
                return 200, {"object": {"sha": "abc123"}}
            return patch_status, patch_detail

        with mock.patch.object(wire_repo, "call", fake_call):
            result = wire_repo.is_protected("t", "o", "r", "main")
        return result, calls

    def test_refused_write_means_protected(self):
        (protected, detail), _ = self._probe(422, "Repository rule violations found")
        self.assertTrue(protected)
        self.assertIn("refused", detail)

    def test_accepted_write_means_unprotected(self):
        (protected, detail), _ = self._probe(200)
        self.assertFalse(protected)
        self.assertIn("ACCEPTED", detail)

    def test_probe_is_a_no_op_fast_forward(self):
        """Points the ref at the sha it already holds: no commit, no file."""
        _, calls = self._probe(422)
        methods = [c[0] for c in calls]
        self.assertEqual(methods, ["GET", "PATCH"])
        self.assertNotIn("PUT", methods, "a contents write would leave junk behind")
        self.assertEqual(calls[1][2], {"sha": "abc123", "force": False})

    def test_unreadable_branch_is_not_reported_as_protected(self):
        """Absence of an answer must never read as protection."""
        with mock.patch.object(wire_repo, "call",
                               lambda *a, **k: (404, "Not Found")):
            protected, detail = wire_repo.is_protected("t", "o", "r", "main")
        self.assertFalse(protected)
        self.assertIn("not readable", detail)


class SeedCopyTests(unittest.TestCase):
    def test_missing_credential_path_stops_wiring(self):
        """A repo wired without gh_token.py could never merge anything."""
        with self.assertRaises(wire_repo.WiringError) as caught:
            wire_repo.load_gh_token("/nonexistent/checkout")
        message = str(caught.exception)
        self.assertIn("gh_token.py", message)
        self.assertIn("seed copy is incomplete", message)


class ReportingTests(unittest.TestCase):
    UNPROTECTED = {
        "repo": "warblersafety/wilson", "default_branch": "dev",
        "branches": {"dev": "created", "staging": "created"},
        "protected": {
            "main": {"ruleset_api": 403, "enforced": False,
                     "probe": "a direct write to this branch was ACCEPTED"},
            "staging": {"ruleset_api": 403, "enforced": False,
                        "probe": "a direct write to this branch was ACCEPTED"}},
        "unprotected": ["main", "staging"]}

    PROTECTED = {
        "repo": "warblersafety/scratch", "default_branch": "dev",
        "branches": {"dev": "created", "staging": "created"},
        "protected": {"main": {"ruleset_api": 201, "enforced": True,
                               "probe": "refused (422)"}},
        "unprotected": []}

    def test_unprotected_repo_is_reported_loudly(self):
        text = wire_repo.summarise(self.UNPROTECTED)
        self.assertIn("NOT ENFORCED", text)
        self.assertIn("PROCESS-ONLY ENFORCEMENT", text)
        self.assertIn("needs-Steve digest", text)
        self.assertIn("CLAUDE.md", text)

    def test_protected_repo_says_so_without_the_warning(self):
        text = wire_repo.summarise(self.PROTECTED)
        self.assertIn("ENFORCED", text)
        self.assertNotIn("PROCESS-ONLY", text)

    def test_a_recorded_ruleset_is_not_reported_as_protection(self):
        """201 from the rulesets API must not be mistaken for enforcement."""
        report = dict(self.PROTECTED)
        report["protected"] = {"main": {"ruleset_api": 201, "enforced": False,
                                        "probe": "a direct write was ACCEPTED"}}
        report["unprotected"] = ["main"]
        text = wire_repo.summarise(report)
        self.assertIn("NOT ENFORCED", text)
        self.assertIn("PROCESS-ONLY ENFORCEMENT", text)

    def test_exit_code_distinguishes_unprotected_from_clean(self):
        for report, expected in ((self.PROTECTED, 0), (self.UNPROTECTED, 5)):
            with self.subTest(repo=report["repo"]):
                with mock.patch.object(wire_repo, "wire", return_value=report), \
                     mock.patch.object(sys, "stdout", io.StringIO()):
                    code = wire_repo.main(["--repo", report["repo"],
                                           "--checkout", "/tmp"])
                self.assertEqual(code, expected)

    def test_wiring_failure_exits_4_not_5(self):
        with mock.patch.object(wire_repo, "wire",
                               side_effect=wire_repo.WiringError("boom")), \
             mock.patch.object(sys, "stderr", io.StringIO()):
            self.assertEqual(wire_repo.main(["--repo", "o/r",
                                             "--checkout", "/tmp"]), 4)


if __name__ == "__main__":
    unittest.main()
