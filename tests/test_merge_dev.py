"""Tests for the seed kit's paved-path merge script's decision logic."""

import importlib.util
import json
import pathlib
import subprocess
import unittest
from unittest import mock

_path = pathlib.Path(__file__).resolve().parent.parent / "seed" / "scripts" / "merge_dev.py"
_spec = importlib.util.spec_from_file_location("merge_dev", _path)
merge_dev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(merge_dev)

REVIEW = f"{merge_dev.REVIEW_MARKER}\nLooks correct; one keep-grade note filed."
GREEN = [{"__typename": "CheckRun", "name": n, "conclusion": "SUCCESS"}
         for n in merge_dev.REQUIRED_CHECKS]


def pr(**over):
    base = {
        "isDraft": False,
        "state": "OPEN",
        "baseRefName": "dev",
        "headRefName": "claude/unit-1",
        "statusCheckRollup": list(GREEN),
    }
    base.update(over)
    return base


def blockers_of(p, bodies):
    blockers, _ = merge_dev.evaluate(p, bodies)
    return blockers


def pending_of(p, bodies):
    _, pending = merge_dev.evaluate(p, bodies)
    return pending


def _pr_view_json(**over):
    """The gh pr view --json response shape after Issue #33: the rollup
    is no longer one of its fields, and headRefOid (the commit the REST
    rollup reads) is."""
    fields = pr(**over)
    fields.pop("statusCheckRollup", None)
    fields.setdefault("headRefOid", "sha-under-test")
    return json.dumps(fields)


def _rest_rollup_jsons(rollup):
    """Split a rollup node list (the shape evaluate() consumes) into the
    two REST response bodies Issue #33's fix reads instead of GraphQL's
    statusCheckRollup: check-runs by name, status contexts separately."""
    runs = [n for n in rollup if n.get("__typename") != "StatusContext"]
    statuses = [n for n in rollup if n.get("__typename") == "StatusContext"]
    check_runs_json = json.dumps({"check_runs": [
        {"name": n.get("name"), "conclusion": n.get("conclusion"),
         "status": n.get("status")} for n in runs]})
    status_json = json.dumps({"statuses": [
        {"context": n.get("context"), "state": n.get("state")}
        for n in statuses]})
    return check_runs_json, status_json


class EvaluateTests(unittest.TestCase):
    def test_happy_path_has_no_blockers_and_nothing_pending(self):
        self.assertEqual(merge_dev.evaluate(pr(), [REVIEW]), ([], []))

    def test_draft_blocks(self):
        self.assertTrue(any("draft" in b for b in
                            blockers_of(pr(isDraft=True), [REVIEW])))

    def test_closed_state_blocks(self):
        self.assertTrue(any("OPEN" in b for b in
                            blockers_of(pr(state="MERGED"), [REVIEW])))

    def test_wrong_base_blocks(self):
        blockers = blockers_of(pr(baseRefName="main"), [REVIEW])
        self.assertTrue(any("dev only" in b for b in blockers))

    def test_non_claude_head_blocks(self):
        blockers = blockers_of(pr(headRefName="fix-1"), [REVIEW])
        self.assertTrue(any("claude/*" in b for b in blockers))

    def test_missing_required_check_blocks(self):
        rollup = [c for c in GREEN if c["name"] != "secrets"]
        blockers = blockers_of(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertTrue(any("'secrets'" in b and "absent is not green" in b
                            for b in blockers))

    def test_skipped_required_check_blocks(self):
        rollup = [c for c in GREEN if c["name"] != "test"]
        rollup.append({"__typename": "CheckRun", "name": "test",
                       "conclusion": "SKIPPED"})
        blockers = blockers_of(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertTrue(any("'test'" in b and "SKIPPED" in b for b in blockers))

    def test_vercel_status_alone_is_not_green(self):
        rollup = [{"context": "vercel", "state": "SUCCESS"}]
        blockers = blockers_of(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertEqual(len([b for b in blockers if "absent" in b]),
                         len(merge_dev.REQUIRED_CHECKS))

    def test_failing_non_required_check_is_named(self):
        rollup = list(GREEN) + [{"__typename": "CheckRun", "name": "coverage",
                                 "conclusion": "FAILURE"}]
        blockers = blockers_of(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertTrue(any("coverage" in b for b in blockers))

    def test_marker_must_start_the_comment(self):
        mid = f"as discussed, {merge_dev.REVIEW_MARKER} was posted earlier"
        blockers = blockers_of(pr(), [mid])
        self.assertTrue(any("no merge" in b for b in blockers))
        self.assertEqual(merge_dev.evaluate(pr(), ["  \n" + REVIEW]), ([], []))

    def test_refusal_text_never_contains_the_marker(self):
        blockers = blockers_of(
            pr(isDraft=True, state="CLOSED", baseRefName="main",
               headRefName="x", statusCheckRollup=[]), ["nope"])
        self.assertTrue(blockers)
        self.assertFalse(any(merge_dev.REVIEW_MARKER in b for b in blockers))

    def test_multiple_blockers_all_reported(self):
        # draft + wrong base + 3 absent required checks + no marker = 6
        blockers = blockers_of(
            pr(isDraft=True, baseRefName="staging", statusCheckRollup=[]), [])
        self.assertEqual(len(blockers), 6)


class NamespaceTests(unittest.TestCase):
    """CheckRun and StatusContext share a rollup, never a namespace
    (Issue #28): a posted status must not satisfy, override, or
    order-dependently decide a required check."""

    def test_a_commit_status_cannot_satisfy_a_required_check(self):
        """Anything with statuses:write can post {context: test, SUCCESS};
        the workflow run it impersonates never ran."""
        rollup = [c for c in GREEN if c["name"] != "test"]
        rollup.append({"__typename": "StatusContext", "context": "test",
                       "state": "SUCCESS"})
        blockers = blockers_of(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertTrue(any("'test'" in b and "absent is not green" in b
                            for b in blockers), blockers)
        self.assertTrue(any("not the workflow run" in b for b in blockers))

    def test_disagreeing_verdicts_on_one_name_block_regardless_of_order(self):
        """A FAILURE CheckRun and a SUCCESS StatusContext named alike must
        refuse identically whichever comes last in the rollup."""
        run = {"__typename": "CheckRun", "name": "test",
               "conclusion": "FAILURE"}
        status = {"__typename": "StatusContext", "context": "test",
                  "state": "SUCCESS"}
        others = [c for c in GREEN if c["name"] != "test"]
        for rollup in (others + [run, status], others + [status, run]):
            with self.subTest(order=[n.get("name") or n.get("context")
                                     for n in rollup]):
                blockers = blockers_of(pr(statusCheckRollup=rollup), [REVIEW])
                self.assertTrue(any("two verdicts" in b for b in blockers),
                                blockers)
                self.assertTrue(any("not SUCCESS" in b or "FAILURE" in b
                                    for b in blockers), blockers)

    def test_agreeing_duplicate_names_do_not_block(self):
        rollup = list(GREEN) + [
            {"__typename": "StatusContext", "context": "extra",
             "state": "SUCCESS"},
            {"__typename": "CheckRun", "name": "extra",
             "conclusion": "SUCCESS"}]
        self.assertEqual(merge_dev.evaluate(pr(statusCheckRollup=rollup),
                                            [REVIEW]), ([], []))

    def test_nodes_without_typename_are_split_by_shape(self):
        rollup = [c for c in GREEN if c["name"] != "test"]
        rollup.append({"context": "test", "state": "SUCCESS"})  # no __typename
        blockers = blockers_of(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertTrue(any("'test'" in b and "absent" in b for b in blockers))

    def test_cross_enum_agreement_is_not_a_disagreement(self):
        """NEUTRAL (a CheckRun conclusion) and SUCCESS (a status state)
        are different enums agreeing on 'good' — raw string inequality
        must not refuse them as two verdicts."""
        rollup = list(GREEN) + [
            {"__typename": "CheckRun", "name": "extra",
             "conclusion": "NEUTRAL"},
            {"__typename": "StatusContext", "context": "extra",
             "state": "SUCCESS"}]
        self.assertEqual(merge_dev.evaluate(pr(statusCheckRollup=rollup),
                                            [REVIEW]), ([], []))


class PendingTests(unittest.TestCase):
    """A running check is not a failing one (Issue #31)."""

    def test_pending_commit_status_is_pending_not_failing(self):
        rollup = GREEN + [{"context": "vercel — preview", "state": "PENDING"}]
        self.assertEqual(blockers_of(pr(statusCheckRollup=rollup), [REVIEW]),
                         [])
        pending = pending_of(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertTrue(any("vercel — preview" in p for p in pending), pending)
        self.assertFalse(any("Failing" in p for p in pending))

    def test_failing_commit_status_still_blocks(self):
        rollup = GREEN + [{"context": "vercel — preview", "state": "FAILURE"}]
        blockers = blockers_of(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertTrue(any("vercel — preview" in b for b in blockers), blockers)

    def test_successful_commit_status_does_not_block(self):
        rollup = GREEN + [{"context": "vercel — preview", "state": "SUCCESS"}]
        self.assertEqual(merge_dev.evaluate(pr(statusCheckRollup=rollup),
                                            [REVIEW]), ([], []))

    def test_running_required_check_is_pending_not_blocked(self):
        """A CheckRun mid-flight has no conclusion yet — that is 'not
        decided', never 'not SUCCESS'."""
        rollup = [c for c in GREEN if c["name"] != "test"]
        rollup.append({"__typename": "CheckRun", "name": "test",
                       "conclusion": None, "status": "IN_PROGRESS"})
        self.assertEqual(blockers_of(pr(statusCheckRollup=rollup), [REVIEW]),
                         [])
        pending = pending_of(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertTrue(any("'test'" in p and "running" in p for p in pending))

    def test_running_run_beside_decided_status_is_not_two_verdicts(self):
        """Recovered review, PR #34: a required CheckRun mid-flight next
        to a same-named SUCCESS status was refused as 'two verdicts' —
        but a node that has not finished holds no verdict yet."""
        rollup = [c for c in GREEN if c["name"] != "test"]
        rollup.append({"__typename": "CheckRun", "name": "test",
                       "conclusion": None, "status": "IN_PROGRESS"})
        rollup.append({"__typename": "StatusContext", "context": "test",
                       "state": "SUCCESS"})
        self.assertEqual(blockers_of(pr(statusCheckRollup=rollup), [REVIEW]),
                         [])
        pending = pending_of(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertTrue(any("'test'" in p and "running" in p
                            for p in pending), pending)

    def test_pending_status_behind_decided_required_check_stays_visible(self):
        """The reverse collision: a SUCCESS run + PENDING status sharing
        a required name previously blocked as a disagreement AND hid the
        pending fact; it is simply not decided yet."""
        rollup = list(GREEN) + [{"__typename": "StatusContext",
                                 "context": "lint", "state": "PENDING"}]
        self.assertEqual(blockers_of(pr(statusCheckRollup=rollup), [REVIEW]),
                         [])
        pending = pending_of(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertTrue(any("lint" in p for p in pending), pending)

    def test_pending_only_exits_5_and_merges_nothing(self):
        rollup = GREEN + [{"context": "vercel — preview", "state": "PENDING"}]
        pr_json = _pr_view_json(comments=[{"body": REVIEW}])
        runs_json, status_json = _rest_rollup_jsons(rollup)

        def fake_gh(args, env):
            if args[:2] == ["pr", "view"]:
                return pr_json
            if args[0] == "api" and args[1].endswith("/check-runs"):
                return runs_json
            if args[0] == "api" and args[1].endswith("/status"):
                return status_json
            raise AssertionError(f"unexpected gh call: {args}")

        module = mock.Mock(mint=mock.Mock(return_value=("ghs_stub", "later")))
        with mock.patch.object(merge_dev, "_origin", return_value=("o", "r")), \
             mock.patch.object(merge_dev, "_gh_token_module",
                               return_value=module), \
             mock.patch.object(merge_dev, "_gh", side_effect=fake_gh) as gh, \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(merge_dev.main(["merge_dev.py", "12"]), 5)
        merge_calls = [c for c in gh.call_args_list if "merge" in c.args[0]]
        self.assertEqual(merge_calls, [])
        printed = " ".join(str(c.args[0]) for c in fake_print.call_args_list)
        self.assertIn("NOT DECIDED YET", printed)
        self.assertIn("running check is not a failing one", printed)


class UnresolvedFieldTests(unittest.TestCase):
    """A field the token could not see is a credential problem, never a
    blocker (Issue #29): 'could not read the comments' must not print as
    'no reviewer pass'. (The rollup used to have this failure mode too —
    a silently null statusCheckRollup — but REST has no silent-null case:
    a permission problem there throws, and is covered by
    RollupFetchTests.test_rollup_fetch_failure_is_a_transport_failure.)"""

    def _run(self, pr_json, rollup=GREEN):
        runs_json, status_json = _rest_rollup_jsons(rollup)

        def fake_gh(args, env):
            if args[:2] == ["pr", "view"]:
                return pr_json
            if args[0] == "api" and args[1].endswith("/check-runs"):
                return runs_json
            if args[0] == "api" and args[1].endswith("/status"):
                return status_json
            raise AssertionError(f"unexpected gh call: {args}")

        module = mock.Mock(mint=mock.Mock(return_value=("ghs_stub", "later")))
        with mock.patch.object(merge_dev, "_origin", return_value=("o", "r")), \
             mock.patch.object(merge_dev, "_gh_token_module",
                               return_value=module), \
             mock.patch.object(merge_dev, "_gh", side_effect=fake_gh), \
             mock.patch("builtins.print") as fake_print:
            code = merge_dev.main(["merge_dev.py", "12"])
        return code, " ".join(str(c.args[0])
                              for c in fake_print.call_args_list)

    def test_missing_comments_is_a_credential_failure_not_a_refusal(self):
        answer = pr()
        answer.pop("statusCheckRollup", None)
        answer.pop("comments", None)
        answer.setdefault("headRefOid", "sha-under-test")
        code, printed = self._run(json.dumps(answer))
        self.assertEqual(code, 4)
        self.assertIn("could not resolve comments", printed)
        self.assertNotIn("No reviewer-pass comment", printed)

    def test_genuinely_empty_comments_still_refuse(self):
        code, printed = self._run(_pr_view_json(comments=[]))
        self.assertEqual(code, 1)
        self.assertIn("No reviewer-pass comment", printed)


class RollupFetchTests(unittest.TestCase):
    """The CI-status rollup is read over REST, not GraphQL (Issue #33):
    statusCheckRollup fails outright on a private repo even under the
    full permission set, while the same commit's checks and statuses
    read back cleanly under checks:read/statuses:read alone. evaluate()
    itself is untouched — only how the rollup data arrives changed."""

    def _run(self, rollup, comments=None):
        pr_json = _pr_view_json(
            comments=comments if comments is not None else [{"body": REVIEW}],
            headRefOid="deadbeef")
        runs_json, status_json = _rest_rollup_jsons(rollup)
        calls = []

        def fake_gh(args, env):
            calls.append(args)
            if args[:2] == ["pr", "view"]:
                return pr_json
            if args == ["api", "repos/o/r/commits/deadbeef/check-runs"]:
                return runs_json
            if args == ["api", "repos/o/r/commits/deadbeef/status"]:
                return status_json
            if args[:2] == ["pr", "merge"]:
                return ""
            raise AssertionError(f"unexpected gh call: {args}")

        module = mock.Mock(mint=mock.Mock(return_value=("ghs_stub", "later")))
        with mock.patch.object(merge_dev, "_origin", return_value=("o", "r")), \
             mock.patch.object(merge_dev, "_gh_token_module",
                               return_value=module), \
             mock.patch.object(merge_dev, "_gh", side_effect=fake_gh), \
             mock.patch("builtins.print"):
            code = merge_dev.main(["merge_dev.py", "12"])
        return code, calls

    def test_rollup_is_read_from_the_head_commit_by_sha(self):
        code, calls = self._run(GREEN)
        self.assertEqual(code, 0)
        self.assertIn(["api", "repos/o/r/commits/deadbeef/check-runs"], calls)
        self.assertIn(["api", "repos/o/r/commits/deadbeef/status"], calls)

    def test_lowercase_rest_values_are_understood_like_graphql_ones(self):
        """REST returns 'success'/'completed' lowercase where GraphQL
        returned 'SUCCESS'/'COMPLETED'. _verdict() upcases whatever it
        is handed, so this must merge like any other green PR, not
        stall as an unrecognized state."""
        rollup = [{"__typename": "CheckRun", "name": n,
                  "conclusion": "success", "status": "completed"}
                 for n in merge_dev.REQUIRED_CHECKS]
        code, _ = self._run(rollup)
        self.assertEqual(code, 0)

    def test_rest_status_context_still_blocks_a_missing_required_check(self):
        """A REST-shaped StatusContext must not satisfy a required
        CheckRun name, same rule as the GraphQL rollup (Issue #28)."""
        rollup = [n for n in GREEN if n["name"] != "test"]
        rollup.append({"__typename": "StatusContext", "context": "test",
                       "state": "SUCCESS"})
        code, _ = self._run(rollup)
        self.assertEqual(code, 1)

    def test_rollup_fetch_failure_is_a_transport_failure(self):
        """The exact failure Issue #33 reports: the rollup read fails
        outright. It must surface the same way any other failed gh call
        does — loud, exit 3, no merge — never as a blocked PR."""
        pr_json = _pr_view_json(comments=[{"body": REVIEW}])

        def fake_gh(args, env):
            if args[:2] == ["pr", "view"]:
                return pr_json
            if args[0] == "api":
                raise subprocess.CalledProcessError(
                    1, ["gh"],
                    stderr="Resource not accessible by integration")
            raise AssertionError(f"unexpected gh call: {args}")

        module = mock.Mock(mint=mock.Mock(return_value=("ghs_stub", "later")))
        with mock.patch.object(merge_dev, "_origin", return_value=("o", "r")), \
             mock.patch.object(merge_dev, "_gh_token_module",
                               return_value=module), \
             mock.patch.object(merge_dev, "_gh", side_effect=fake_gh), \
             mock.patch("builtins.print") as fake_print:
            code = merge_dev.main(["merge_dev.py", "12"])
        self.assertEqual(code, 3)
        printed = " ".join(str(c.args[0]) for c in fake_print.call_args_list)
        self.assertIn("TRANSPORT FAILURE", printed)

    def test_malformed_rollup_body_is_a_transport_failure_not_a_refusal(self):
        """A 200 that isn't the expected shape (or isn't JSON at all)
        must not be read as 'this commit has zero checks' — that would
        misreport a data-fetching problem as a real, and wrong, refusal."""
        pr_json = _pr_view_json(comments=[{"body": REVIEW}])

        def fake_gh(args, env):
            if args[:2] == ["pr", "view"]:
                return pr_json
            if args[0] == "api" and args[1].endswith("/check-runs"):
                return "not json at all"
            if args[0] == "api" and args[1].endswith("/status"):
                return json.dumps({"unexpected_key": []})
            raise AssertionError(f"unexpected gh call: {args}")

        module = mock.Mock(mint=mock.Mock(return_value=("ghs_stub", "later")))
        with mock.patch.object(merge_dev, "_origin", return_value=("o", "r")), \
             mock.patch.object(merge_dev, "_gh_token_module",
                               return_value=module), \
             mock.patch.object(merge_dev, "_gh", side_effect=fake_gh), \
             mock.patch("builtins.print") as fake_print:
            code = merge_dev.main(["merge_dev.py", "12"])
        self.assertEqual(code, 3)
        printed = " ".join(str(c.args[0]) for c in fake_print.call_args_list)
        self.assertIn("TRANSPORT FAILURE", printed)
        self.assertNotIn("REFUSED", printed)


class PostMergeCleanupTests(unittest.TestCase):
    """A landed merge must never report as a failed one (Issue #29):
    --delete-branch runs after the merge commits."""

    def _run(self, state_after, merge_err_stderr="branch checkout failed"):
        pr_json = _pr_view_json(comments=[{"body": REVIEW}])
        runs_json, status_json = _rest_rollup_jsons(GREEN)
        module = mock.Mock(mint=mock.Mock(return_value=("ghs_stub", "later")))

        def fake_gh(args, env):
            if "merge" in args:
                raise subprocess.CalledProcessError(
                    1, ["gh"], stderr=merge_err_stderr)
            if args[:2] == ["pr", "view"] and args[-1] == "state":
                if state_after is None:
                    raise subprocess.CalledProcessError(1, ["gh"], stderr="down")
                return json.dumps({"state": state_after})
            if args[:2] == ["pr", "view"]:
                return pr_json
            if args[0] == "api" and args[1].endswith("/check-runs"):
                return runs_json
            if args[0] == "api" and args[1].endswith("/status"):
                return status_json
            raise AssertionError(f"unexpected gh call: {args}")

        with mock.patch.object(merge_dev, "_origin", return_value=("o", "r")), \
             mock.patch.object(merge_dev, "_gh_token_module",
                               return_value=module), \
             mock.patch.object(merge_dev, "_gh", side_effect=fake_gh), \
             mock.patch("builtins.print") as fake_print:
            code = merge_dev.main(["merge_dev.py", "12"])
        return code, " ".join(str(c.args[0])
                              for c in fake_print.call_args_list)

    def test_landed_merge_with_failed_cleanup_reports_merged(self):
        code, printed = self._run("MERGED")
        self.assertEqual(code, 0)
        self.assertIn("The merge LANDED", printed)
        self.assertIn("branch checkout failed", printed)
        self.assertNotIn("nothing was merged", printed)

    def test_unlanded_merge_still_reports_transport_failure(self):
        code, printed = self._run("OPEN")
        self.assertEqual(code, 3)
        self.assertIn("TRANSPORT FAILURE", printed)

    def test_unconfirmable_state_stays_a_transport_failure(self):
        """When the re-read itself fails, claim nothing beyond failure."""
        code, printed = self._run(None)
        self.assertEqual(code, 3)
        self.assertIn("TRANSPORT FAILURE", printed)


class RepoSlugTests(unittest.TestCase):
    def test_parses_ssh_and_https_remotes(self):
        for url in ("git@github.com:warblersafety/wilson.git",
                    "https://github.com/warblersafety/wilson.git",
                    "https://github.com/warblersafety/wilson",
                    "ssh://git@github.com/warblersafety/wilson.git\n"):
            with self.subTest(url=url):
                self.assertEqual(merge_dev.repo_slug(url),
                                 ("warblersafety", "wilson"))

    def test_unparseable_remote_is_refused(self):
        with self.assertRaises(RuntimeError):
            merge_dev.repo_slug("not-a-remote")


class PermissionDerivationTests(unittest.TestCase):
    """Permission sets are derived, never asserted (Issue #30): the next
    field added to the query must fail here until its permissions are
    mapped, because three consecutive PRs each corrected a hand-asserted
    set the previous suite had waved through."""

    def test_every_query_field_has_a_permission_mapping(self):
        for field in merge_dev.FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, merge_dev.FIELD_PERMISSIONS)
                self.assertTrue(merge_dev.FIELD_PERMISSIONS[field])

    def test_inspect_set_is_exactly_the_derived_union(self):
        derived = {"metadata": "read"}
        for field in merge_dev.FIELDS:
            derived.update(merge_dev.FIELD_PERMISSIONS[field])
        derived.update(merge_dev.ROLLUP_PERMISSIONS)
        self.assertEqual(merge_dev.INSPECT_PERMISSIONS, derived)

    def test_no_unmapped_permission_smuggled_into_inspect(self):
        mapped = {"metadata"}
        for perms in merge_dev.FIELD_PERMISSIONS.values():
            mapped.update(perms)
        mapped.update(merge_dev.ROLLUP_PERMISSIONS)
        self.assertEqual(set(merge_dev.INSPECT_PERMISSIONS), mapped)

    def test_rollup_permissions_no_longer_include_actions(self):
        """Issue #33: actions:read was never what the private-repo
        failure needed — REST reads the rollup under checks/statuses
        alone."""
        self.assertEqual(merge_dev.ROLLUP_PERMISSIONS,
                         {"checks": "read", "statuses": "read"})

    def test_every_query_field_is_classified_for_null_handling(self):
        """The nullable-field list is derived, not hand-asserted — the
        next field added to FIELDS must fail here until classified."""
        self.assertEqual(set(merge_dev.FIELD_NULL_MEANS_UNRESOLVED),
                         set(merge_dev.FIELDS))
        self.assertEqual(set(merge_dev.UNRESOLVED_NULL_FIELDS),
                         {"comments"})


class CredentialTests(unittest.TestCase):
    """No silent fallback: if the App cannot mint, nothing merges."""

    def test_merge_token_carries_only_what_the_merge_needs(self):
        """The write token must not inherit the inspection surface
        (Issue #30): the rollup was evaluated under the read token, and
        actions:read in particular is ELEVATED in gh_token.py."""
        self.assertEqual(merge_dev.MERGE_PERMISSIONS,
                         {"contents": "write", "pull_requests": "write",
                          "metadata": "read"})
        for surface in ("checks", "statuses", "actions"):
            self.assertNotIn(surface, merge_dev.MERGE_PERMISSIONS)
        self.assertNotIn("administration", merge_dev.MERGE_PERMISSIONS)

    def test_inspect_token_cannot_merge(self):
        """A refused PR never has a merge-capable credential in the room."""
        for level in merge_dev.INSPECT_PERMISSIONS.values():
            self.assertEqual(level, "read")
        self.assertEqual(merge_dev.MERGE_PERMISSIONS["contents"], "write")
        self.assertEqual(merge_dev.MERGE_PERMISSIONS["pull_requests"], "write")

    def test_refused_pr_never_mints_write_permissions(self):
        minted = []

        def fake_mint(account, repositories, permissions, **kwargs):
            minted.append(dict(permissions))
            return "ghs_stub", "later"

        module = mock.Mock(mint=fake_mint)
        pr_json = _pr_view_json(isDraft=True, comments=[])
        runs_json, status_json = _rest_rollup_jsons([])

        def fake_gh(args, env):
            if args[:2] == ["pr", "view"]:
                return pr_json
            if args[0] == "api" and args[1].endswith("/check-runs"):
                return runs_json
            if args[0] == "api" and args[1].endswith("/status"):
                return status_json
            raise AssertionError(f"unexpected gh call: {args}")

        with mock.patch.object(merge_dev, "_origin", return_value=("o", "r")), \
             mock.patch.object(merge_dev, "_gh_token_module", return_value=module), \
             mock.patch.object(merge_dev, "_gh", side_effect=fake_gh), \
             mock.patch("builtins.print"):
            self.assertEqual(merge_dev.main(["merge_dev.py", "12"]), 1)
        self.assertEqual(len(minted), 1, "a refused PR must mint once, to read")
        self.assertNotIn("write", minted[0].values())

    def test_scoped_to_this_repository_only(self):
        seen = {}

        def fake_mint(account, repositories, permissions, **kwargs):
            seen.update(account=account, repositories=repositories)
            return "ghs_stub", "later"

        module = mock.Mock(mint=fake_mint)
        with mock.patch.object(merge_dev, "_origin",
                               return_value=("warblersafety", "wilson")), \
             mock.patch.object(merge_dev, "_gh_token_module", return_value=module), \
             mock.patch.object(merge_dev, "_gh",
                               side_effect=subprocess.CalledProcessError(1, ["gh"])), \
             mock.patch("builtins.print"):
            merge_dev.main(["merge_dev.py", "12"])
        self.assertEqual(seen["account"], "warblersafety")
        self.assertEqual(seen["repositories"], ["wilson"])

    def test_any_credential_exception_yields_exit_4_not_1(self):
        """Exit 1 means 'PR blocked'; a transport blip must not look like one."""
        for boom in (RuntimeError("no key"), ValueError("bad json"),
                     OSError("network down"), KeyError("token")):
            with self.subTest(error=type(boom).__name__):
                module = mock.Mock()
                module.mint.side_effect = boom
                with mock.patch.object(merge_dev, "_origin",
                                       return_value=("o", "r")), \
                     mock.patch.object(merge_dev, "_gh_token_module",
                                       return_value=module), \
                     mock.patch.object(merge_dev, "_gh") as fake_gh, \
                     mock.patch("builtins.print"):
                    self.assertEqual(merge_dev.main(["merge_dev.py", "12"]), 4)
                fake_gh.assert_not_called()

    def test_credential_failure_stops_without_merging(self):
        module = mock.Mock()
        module.mint.side_effect = RuntimeError("no key on this machine")
        with mock.patch.object(merge_dev, "_origin",
                               return_value=("o", "r")), \
             mock.patch.object(merge_dev, "_gh_token_module", return_value=module), \
             mock.patch.object(merge_dev, "_gh") as fake_gh, \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(merge_dev.main(["merge_dev.py", "12"]), 4)
        fake_gh.assert_not_called()
        printed = " ".join(str(c.args[0]) for c in fake_print.call_args_list)
        self.assertIn("CREDENTIAL FAILURE", printed)
        self.assertIn("no key on this machine", printed)
        self.assertIn("do not fall back to another credential", printed)


class TransportTests(unittest.TestCase):
    def test_transport_failure_is_loud_and_does_not_merge(self):
        err = subprocess.CalledProcessError(1, ["gh"], stderr="boom")
        module = mock.Mock(mint=mock.Mock(return_value=("ghs_stub", "later")))
        with mock.patch.object(merge_dev, "_origin", return_value=("o", "r")), \
             mock.patch.object(merge_dev, "_gh_token_module", return_value=module), \
             mock.patch.object(merge_dev, "_gh", side_effect=err):
            with mock.patch("builtins.print") as fake_print:
                self.assertEqual(merge_dev.main(["merge_dev.py", "12"]), 3)
        printed = " ".join(str(c.args[0]) for c in fake_print.call_args_list)
        self.assertIn("TRANSPORT FAILURE", printed)
        self.assertIn("boom", printed)
        self.assertIn("Do NOT merge by hand", printed)


if __name__ == "__main__":
    unittest.main()
