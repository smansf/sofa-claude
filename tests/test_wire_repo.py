"""Tests for bootstrap's repo wiring and its protection verification.

The property under test is that wiring reports what GitHub *enforces*,
not what its APIs accepted — a 201 from the rulesets endpoint means a
ruleset was recorded, not that a branch is protected, and an errored
probe means "could not verify", never "protected". Protection itself
means both paths: direct pushes refused by rules, and merges gated on at
least one approving human review — a zero-approval rule requires a PR,
not a human (PR #32, finding 1). On the free plan a private repo gets no
rulesets at all, so "unprotected" is a normal outcome; the requirement
is that it can never be a quiet one.
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


class PayloadTests(unittest.TestCase):
    def test_ruleset_requires_a_human_approval(self):
        """Zero approvals requires a PR, not a human (finding 1)."""
        payload = wire_repo.ruleset_payload("main")
        pull = [r for r in payload["rules"] if r["type"] == "pull_request"]
        self.assertEqual(len(pull), 1)
        self.assertGreaterEqual(
            pull[0]["parameters"]["required_approving_review_count"], 1)

    def test_nobody_bypasses(self):
        self.assertEqual(wire_repo.ruleset_payload("main")["bypass_actors"], [])


class PushProbeTests(unittest.TestCase):
    """The probe must create nothing, and an error is never a refusal."""

    def _probe(self, patch_status, patch_detail=""):
        calls = []

        def fake_call(token, method, path, payload=None):
            calls.append((method, path, payload))
            if method == "GET":
                return 200, {"object": {"sha": "abc123"}}
            return patch_status, patch_detail

        with mock.patch.object(wire_repo, "call", fake_call):
            result = wire_repo.push_refused("t", "o", "r", "main")
        return result, calls

    def test_rules_refusal_means_protected(self):
        (verdict, detail), _ = self._probe(422, "Repository rule violations found")
        self.assertIs(verdict, True)
        self.assertIn("refused", detail)

    def test_accepted_write_means_unprotected(self):
        (verdict, detail), _ = self._probe(200)
        self.assertIs(verdict, False)
        self.assertIn("ACCEPTED", detail)

    def test_probe_is_a_no_op_fast_forward(self):
        """Points the ref at the sha it already holds: no commit, no file."""
        _, calls = self._probe(422, "Repository rule violations found")
        methods = [c[0] for c in calls]
        self.assertEqual(methods, ["GET", "PATCH"])
        self.assertNotIn("PUT", methods, "a contents write would leave junk behind")
        self.assertEqual(calls[1][2], {"sha": "abc123", "force": False})

    def test_errors_are_not_refusals(self):
        """A 500, a rate limit, a dead token, an unrelated 422: could not
        verify — never 'protected' (finding 3). Classic branch
        protection's refusal shapes are deliberately unlisted — this
        script only ever creates rulesets, and an unverified shape must
        land inconclusive-and-loud, not guessed as protection."""
        for status, detail in ((500, "boom"), (429, "rate limited"),
                               (401, "Bad credentials"),
                               (403, "Resource not accessible"),
                               (422, "Validation Failed"),
                               (422, "protected branch hook declined"),
                               (403, "Refusing to update ref: protected branch")):
            with self.subTest(status=status):
                (verdict, text), _ = self._probe(status, detail)
                self.assertIsNone(verdict)
                self.assertIn("inconclusive", text)

    def test_unreadable_branch_is_not_reported_as_protected(self):
        """Absence of an answer must never read as protection."""
        with mock.patch.object(wire_repo, "call",
                               lambda *a, **k: (404, "Not Found")):
            verdict, detail = wire_repo.push_refused("t", "o", "r", "main")
        self.assertIsNone(verdict)
        self.assertIn("not readable", detail)


class MergeGateTests(unittest.TestCase):
    """The merge gate is read from the rules GitHub reports as applying."""

    def _gate(self, status, rules):
        with mock.patch.object(wire_repo, "call",
                               lambda *a, **k: (status, rules)):
            return wire_repo.merge_gate("t", "o", "r", "main")

    def test_one_required_approval_is_a_gate(self):
        verdict, _ = self._gate(200, [
            {"type": "pull_request",
             "parameters": {"required_approving_review_count": 1}}])
        self.assertIs(verdict, True)

    def test_zero_required_approvals_is_not_a_gate(self):
        """The demonstrated hole: a PR is required, a human is not."""
        verdict, detail = self._gate(200, [
            {"type": "pull_request",
             "parameters": {"required_approving_review_count": 0}}])
        self.assertIs(verdict, False)
        self.assertIn("0 approving", detail)

    def test_no_applying_rule_is_not_a_gate(self):
        verdict, _ = self._gate(200, [{"type": "deletion"}])
        self.assertIs(verdict, False)

    def test_the_free_plan_answer_is_a_definite_no_not_an_error(self):
        """Verified live 2026-08-20: a private free-plan repo answers rule
        reads with 403 and its upgrade message. That is the plan
        limitation positively identified — it must not exit 4."""
        verdict, detail = self._gate(
            403, "Upgrade to GitHub Pro or make this repository public "
                 "to enable this feature.")
        self.assertIs(verdict, False)
        self.assertIn("unavailable on this plan", detail)

    def test_any_other_error_is_not_a_verdict(self):
        for status, body in ((500, "boom"), (403, "Resource not accessible"),
                             (429, "rate limited")):
            with self.subTest(status=status):
                verdict, _ = self._gate(status, body)
                self.assertIsNone(verdict)


class SeedCopyTests(unittest.TestCase):
    def test_missing_credential_path_stops_wiring(self):
        """A repo wired without gh_token.py could never merge anything —
        and the message names the wrong-directory cause (finding 7)."""
        with self.assertRaises(wire_repo.WiringError) as caught:
            wire_repo.load_gh_token("/nonexistent/checkout")
        message = str(caught.exception)
        self.assertIn("gh_token.py", message)
        self.assertIn("seed copy is incomplete", message)
        self.assertIn("workload repo's root", message)


class WireTests(unittest.TestCase):
    """wire() stops loudly, and what it raises carries the partial report."""

    REPO_OK = (200, {"default_branch": "dev", "delete_branch_on_merge": False})

    def _wire(self, responses, branches=("dev", "staging"), protect=()):
        """responses: {(method, path-suffix): [answers]} — an answer queue
        per endpoint; the last answer repeats. Records every mint in
        self.mints and every call's token in self.tokens_used."""
        self.mints = []
        self.tokens_used = []

        outer = self

        class FakeTokens:
            @staticmethod
            def mint(account, repositories, permissions, reason=None):
                outer.mints.append(dict(permissions))
                return f"tok{len(outer.mints)}", None

        def fake_call(token, method, path, payload=None):
            self.tokens_used.append((token, method, path, payload))
            for (m, suffix), answers in responses.items():
                if m == method and path.endswith(suffix):
                    return answers.pop(0) if len(answers) > 1 else answers[0]
            raise AssertionError(f"unexpected call {method} {path}")

        with mock.patch.object(wire_repo, "load_gh_token",
                               return_value=FakeTokens), \
             mock.patch.object(wire_repo, "call", fake_call):
            return wire_repo.wire("o", "r", "/anywhere",
                                  branches=branches, protect=protect)

    def test_an_existing_branch_is_recorded_not_failed(self):
        report = self._wire({
            ("GET", "/git/ref/heads/main"): [(200, {"object": {"sha": "a"}})],
            ("POST", "/git/refs"): [(201, {}), (422, "Reference already exists")],
            ("PATCH", "/repos/o/r"): [(200, {"default_branch": "dev"})],
            ("GET", "/repos/o/r"): [self.REPO_OK],
        })
        self.assertEqual(report["branches"],
                         {"dev": "created", "staging": "already existed"})

    def test_a_failed_branch_creation_stops_wiring_loudly(self):
        """Finding 5: carrying on would turn a missing branch into a
        'plan limitation' in the permanent record."""
        with self.assertRaises(wire_repo.WiringError) as caught:
            self._wire({
                ("GET", "/git/ref/heads/main"): [(200, {"object": {"sha": "a"}})],
                ("POST", "/git/refs"): [(201, {}), (403, "Forbidden")],
            })
        self.assertIn("staging", str(caught.exception))
        self.assertEqual(caught.exception.report["branches"]["dev"], "created")

    def test_failure_carries_the_partial_report(self):
        """Finding 4: exit 4 must be able to say exactly what was done."""
        with self.assertRaises(wire_repo.WiringError) as caught:
            self._wire({
                ("GET", "/git/ref/heads/main"): [(200, {"object": {"sha": "a"}})],
                ("POST", "/git/refs"): [(201, {})],
                ("PATCH", "/repos/o/r"): [(500, "boom")],
            }, branches=("dev",))
        self.assertEqual(caught.exception.report["branches"], {"dev": "created"})
        self.assertIsNone(caught.exception.report["default_branch"])

    def test_inconclusive_verification_is_a_failure_not_a_verdict(self):
        """Finding 3 end to end: an errored probe must become exit 4 —
        never ENFORCED (exit 0), never an accepted outcome (exit 5)."""
        with self.assertRaises(wire_repo.WiringError) as caught:
            self._wire({
                ("GET", "/git/ref/heads/main"): [(200, {"object": {"sha": "a"}})],
                ("POST", "/git/refs"): [(201, {})],
                ("PATCH", "/repos/o/r"): [(200, {"default_branch": "dev"})],
                ("GET", "/repos/o/r"): [self.REPO_OK],
                ("POST", "/rulesets"): [(201, {})],
                ("PATCH", "/git/refs/heads/main"): [(500, "boom")],
                ("GET", "/rules/branches/main"): [(200, [])],
            }, branches=("dev",), protect=("main",))
        self.assertIn("could not be verified", str(caught.exception))

    def test_enforced_needs_both_paths(self):
        """A refused push with a zero-approval merge rule is the
        demonstrated hole, and must land in unprotected (finding 1)."""
        report = self._wire({
            ("GET", "/git/ref/heads/main"): [(200, {"object": {"sha": "a"}})],
            ("POST", "/git/refs"): [(201, {})],
            ("PATCH", "/repos/o/r"): [(200, {"default_branch": "dev"})],
            ("GET", "/repos/o/r"): [self.REPO_OK],
            ("POST", "/rulesets"): [(201, {})],
            ("PATCH", "/git/refs/heads/main"):
                [(422, "Repository rule violations found")],
            ("GET", "/rules/branches/main"): [(200, [
                {"type": "pull_request",
                 "parameters": {"required_approving_review_count": 0}}])],
        }, branches=("dev",), protect=("main",))
        self.assertFalse(report["protected"]["main"]["enforced"])
        self.assertEqual(report["unprotected"], ["main"])

    def test_ruleset_post_failure_stops_wiring(self):
        """Recovered finding 1: a rate limit or server error on the
        rulesets POST must exit 4 — not flow on to be summarised as a
        plan limitation (403) or a phantom anomaly (500)."""
        for status, detail in ((500, "boom"), (429, "rate limited"),
                               (403, "API rate limit exceeded"),
                               (403, "Resource not accessible by integration")):
            with self.subTest(status=status, detail=detail):
                with self.assertRaises(wire_repo.WiringError) as caught:
                    self._wire({
                        ("GET", "/git/ref/heads/main"):
                            [(200, {"object": {"sha": "a"}})],
                        ("POST", "/git/refs"): [(201, {})],
                        ("PATCH", "/repos/o/r"):
                            [(200, {"default_branch": "dev"})],
                        ("POST", "/rulesets"): [(status, detail)],
                    }, branches=("dev",), protect=("main",))
                self.assertIn("never pass as an accepted plan limitation",
                              str(caught.exception))

    def test_ruleset_post_plan_limit_and_rerun_are_benign(self):
        """The two POST refusals wiring may legitimately continue past:
        GitHub's own plan-limit message, and a re-run's duplicate name."""
        for status, detail in (
                (403, "Upgrade to GitHub Pro or make this repository "
                      "public to enable this feature."),
                (422, "Name has already been taken")):
            with self.subTest(status=status):
                report = self._wire({
                    ("GET", "/git/ref/heads/main"):
                        [(200, {"object": {"sha": "a"}})],
                    ("POST", "/git/refs"): [(201, {})],
                    ("PATCH", "/repos/o/r"): [(200, {"default_branch": "dev"})],
                    ("GET", "/repos/o/r"): [self.REPO_OK],
                    ("POST", "/rulesets"): [(status, detail)],
                    ("PATCH", "/git/refs/heads/main"):
                        [(422, "Repository rule violations found")],
                    ("GET", "/rules/branches/main"): [(200, [
                        {"type": "pull_request",
                         "parameters": {"required_approving_review_count": 1}}])],
                }, branches=("dev",), protect=("main",))
                self.assertTrue(report["protected"]["main"]["enforced"])

    def test_plan_limited_is_read_from_the_merge_message_not_the_status(self):
        """Recovered finding 1: plan-ness must come from GitHub's own
        message during verification, so a plan-limited repo carries the
        structured marker and nothing else does."""
        report = self._wire({
            ("GET", "/git/ref/heads/main"): [(200, {"object": {"sha": "a"}})],
            ("POST", "/git/refs"): [(201, {})],
            ("PATCH", "/repos/o/r"): [(200, {"default_branch": "dev"})],
            ("GET", "/repos/o/r"): [self.REPO_OK],
            ("POST", "/rulesets"):
                [(403, "Upgrade to GitHub Pro or make this repository "
                       "public to enable this feature.")],
            ("PATCH", "/git/refs/heads/main"): [(200, {})],
            ("GET", "/rules/branches/main"):
                [(403, "Upgrade to GitHub Pro or make this repository "
                       "public to enable this feature.")],
        }, branches=("dev",), protect=("main",))
        self.assertTrue(report["protected"]["main"]["plan_limited"])
        self.assertEqual(report["unprotected"], ["main"])

    def test_default_branch_echo_mismatch_stops_wiring(self):
        """Recovered finding 5: a 200 whose reported default branch is
        not the requested one must never exit 0."""
        with self.assertRaises(wire_repo.WiringError) as caught:
            self._wire({
                ("GET", "/git/ref/heads/main"): [(200, {"object": {"sha": "a"}})],
                ("POST", "/git/refs"): [(201, {})],
                ("PATCH", "/repos/o/r"): [(200, {"default_branch": "main"})],
            }, branches=("dev",))
        self.assertIn("not 'dev'", str(caught.exception))

    def test_read_back_verifies_default_branch_and_merge_setting(self):
        """Recovered findings 5 and 6: the verification pass reads the
        repo back independently — a wrong default branch or a
        delete-branch-on-merge that did not stick (or is invisible to
        the token) fails wiring rather than passing silently."""
        for repo_state in ({"default_branch": "main",
                            "delete_branch_on_merge": False},
                           {"default_branch": "dev",
                            "delete_branch_on_merge": True},
                           {"default_branch": "dev"}):
            with self.subTest(repo_state=repo_state):
                with self.assertRaises(wire_repo.WiringError):
                    self._wire({
                        ("GET", "/git/ref/heads/main"):
                            [(200, {"object": {"sha": "a"}})],
                        ("POST", "/git/refs"): [(201, {})],
                        ("PATCH", "/repos/o/r"):
                            [(200, {"default_branch": "dev"})],
                        ("GET", "/repos/o/r"): [(200, repo_state)],
                    }, branches=("dev",))

    def test_delete_branch_on_merge_rides_the_admin_patch(self):
        """Recovered finding 6: the setting is wired in the same PATCH
        the admin mint already makes, not left to manual prose."""
        self._wire({
            ("GET", "/git/ref/heads/main"): [(200, {"object": {"sha": "a"}})],
            ("POST", "/git/refs"): [(201, {})],
            ("PATCH", "/repos/o/r"): [(200, {"default_branch": "dev"})],
            ("GET", "/repos/o/r"): [self.REPO_OK],
        }, branches=("dev",))
        patches = [payload for token, method, path, payload in self.tokens_used
                   if method == "PATCH" and path.endswith("/repos/o/r")]
        self.assertEqual(patches, [{"default_branch": "dev",
                                    "delete_branch_on_merge": False}])

    def test_verification_reuses_the_unprivileged_token(self):
        """Recovered finding 7: exactly two mints — and every probe runs
        under the first, which never held administration."""
        self._wire({
            ("GET", "/git/ref/heads/main"): [(200, {"object": {"sha": "a"}})],
            ("POST", "/git/refs"): [(201, {})],
            ("PATCH", "/repos/o/r"): [(200, {"default_branch": "dev"})],
            ("GET", "/repos/o/r"): [self.REPO_OK],
            ("POST", "/rulesets"): [(201, {})],
            ("PATCH", "/git/refs/heads/main"):
                [(422, "Repository rule violations found")],
            ("GET", "/rules/branches/main"): [(200, [
                {"type": "pull_request",
                 "parameters": {"required_approving_review_count": 1}}])],
        }, branches=("dev",), protect=("main",))
        self.assertEqual(self.mints,
                         [{"contents": "write", "metadata": "read"},
                          {"administration": "write", "metadata": "read"}])
        probe_tokens = {token for token, method, path, payload
                        in self.tokens_used
                        if (method == "GET" and path.endswith("/repos/o/r"))
                        or "/git/refs/heads/" in path   # push probe
                        or "/rules/branches/" in path}  # merge gate
        self.assertEqual(probe_tokens, {"tok1"},
                         "verification must not run under the admin token")


class ReportingTests(unittest.TestCase):
    UNPROTECTED = {
        "repo": "warblersafety/wilson", "default_branch": "dev",
        "delete_branch_on_merge": False,
        "branches": {"dev": "created", "staging": "created"},
        "protected": {
            "main": {"ruleset_api": 403, "enforced": False,
                     "plan_limited": True,
                     "push": "a direct write to this branch was ACCEPTED",
                     "merge": "rules unavailable on this plan for this repo"},
            "staging": {"ruleset_api": 403, "enforced": False,
                        "plan_limited": True,
                        "push": "a direct write to this branch was ACCEPTED",
                        "merge": "rules unavailable on this plan for this repo"}},
        "unprotected": ["main", "staging"]}

    PROTECTED = {
        "repo": "warblersafety/scratch", "default_branch": "dev",
        "delete_branch_on_merge": False,
        "branches": {"dev": "created", "staging": "already existed"},
        "protected": {
            "main": {"ruleset_api": 201, "enforced": True,
                     "plan_limited": False,
                     "push": "refused by rules (422: Repository rule "
                             "violations found)",
                     "merge": "pull_request rule applies, 1 approving "
                              "review(s) required"}},
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

    def test_branch_statuses_are_visible(self):
        """Finding 5: a name alone hides a branch that was never made."""
        self.assertIn("staging (already existed)",
                      wire_repo.summarise(self.PROTECTED))

    def test_recorded_but_unenforced_is_an_anomaly_not_a_plan_limit(self):
        """A 201 followed by no enforcement is not the free-plan story and
        must never be recorded as an accepted outcome (findings 1, 5)."""
        report = dict(self.PROTECTED)
        report["protected"] = {
            "main": {"ruleset_api": 201, "enforced": False,
                     "push": "a direct write to this branch was ACCEPTED",
                     "merge": "no pull_request rule applies to this branch"}}
        report["unprotected"] = ["main"]
        text = wire_repo.summarise(report)
        self.assertIn("NOT ENFORCED", text)
        self.assertIn("RECORDED BUT NOT ENFORCED", text)
        self.assertIn("investigate", text)
        self.assertNotIn("PROCESS-ONLY", text)
        self.assertNotIn("accepted outcome", text)

    def test_a_bare_403_status_is_not_the_plan_limitation(self):
        """Recovered finding 1: plan-ness is the structured marker set
        from GitHub's message during verification — a 403 POST status
        alone (a rate limit produces one too) summarises as an anomaly,
        never as the accepted plan outcome."""
        report = dict(self.PROTECTED)
        report["protected"] = {
            "main": {"ruleset_api": 403, "enforced": False,
                     "push": "a direct write to this branch was ACCEPTED",
                     "merge": "no pull_request rule applies to this branch"}}
        report["unprotected"] = ["main"]
        text = wire_repo.summarise(report)
        self.assertIn("RECORDED BUT NOT ENFORCED", text)
        self.assertNotIn("PROCESS-ONLY", text)

    def test_summary_carries_the_merge_setting(self):
        """Recovered finding 6: the setting is part of the wiring report,
        not a side conversation."""
        self.assertIn("delete-branch-on-merge False",
                      wire_repo.summarise(self.PROTECTED))

    def test_exit_code_distinguishes_unprotected_from_clean(self):
        for report, expected in ((self.PROTECTED, 0), (self.UNPROTECTED, 5)):
            with self.subTest(repo=report["repo"]):
                with mock.patch.object(wire_repo, "wire", return_value=report), \
                     mock.patch.object(sys, "stdout", io.StringIO()):
                    code = wire_repo.main(["--repo", report["repo"],
                                           "--checkout", "/tmp"])
                self.assertEqual(code, expected)

    def test_wiring_failure_exits_4_and_lists_what_was_done(self):
        """Finding 4: the failure output shows the partial state."""
        err = wire_repo.WiringError("boom")
        err.report = {"repo": "o/r", "default_branch": "dev",
                      "branches": {"dev": "created"}, "protected": {},
                      "unprotected": []}
        stderr = io.StringIO()
        with mock.patch.object(wire_repo, "wire", side_effect=err), \
             mock.patch.object(sys, "stderr", stderr):
            code = wire_repo.main(["--repo", "o/r", "--checkout", "/tmp"])
        self.assertEqual(code, 4)
        self.assertIn("may be partly wired", stderr.getvalue())
        self.assertIn('"dev": "created"', stderr.getvalue())

    def test_wiring_failure_before_any_change_says_so(self):
        """Finding 4: when nothing was changed, exit 4 says exactly that."""
        stderr = io.StringIO()
        with mock.patch.object(wire_repo, "wire",
                               side_effect=wire_repo.WiringError("no checkout")), \
             mock.patch.object(sys, "stderr", stderr):
            code = wire_repo.main(["--repo", "o/r", "--checkout", "/tmp"])
        self.assertEqual(code, 4)
        self.assertIn("Nothing had been changed yet", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
