"""Tests for the seed kit's paved-path merge script's decision logic."""

import importlib.util
import pathlib
import subprocess
import unittest
from unittest import mock

_path = pathlib.Path(__file__).resolve().parent.parent / "seed" / "scripts" / "merge_dev.py"
_spec = importlib.util.spec_from_file_location("merge_dev", _path)
merge_dev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(merge_dev)

REVIEW = f"{merge_dev.REVIEW_MARKER}\nLooks correct; one keep-grade note filed."
GREEN = [{"name": n, "conclusion": "SUCCESS"} for n in merge_dev.REQUIRED_CHECKS]


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


class EvaluateTests(unittest.TestCase):
    def test_happy_path_has_no_blockers(self):
        self.assertEqual(merge_dev.evaluate(pr(), [REVIEW]), [])

    def test_draft_blocks(self):
        self.assertTrue(any("draft" in b for b in
                            merge_dev.evaluate(pr(isDraft=True), [REVIEW])))

    def test_closed_state_blocks(self):
        self.assertTrue(any("OPEN" in b for b in
                            merge_dev.evaluate(pr(state="MERGED"), [REVIEW])))

    def test_wrong_base_blocks(self):
        blockers = merge_dev.evaluate(pr(baseRefName="main"), [REVIEW])
        self.assertTrue(any("dev only" in b for b in blockers))

    def test_non_claude_head_blocks(self):
        blockers = merge_dev.evaluate(pr(headRefName="fix-1"), [REVIEW])
        self.assertTrue(any("claude/*" in b for b in blockers))

    def test_missing_required_check_blocks(self):
        rollup = [c for c in GREEN if c["name"] != "secrets"]
        blockers = merge_dev.evaluate(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertTrue(any("'secrets'" in b and "absent is not green" in b
                            for b in blockers))

    def test_skipped_required_check_blocks(self):
        rollup = [c for c in GREEN if c["name"] != "test"]
        rollup.append({"name": "test", "conclusion": "SKIPPED"})
        blockers = merge_dev.evaluate(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertTrue(any("'test'" in b and "SKIPPED" in b for b in blockers))

    def test_vercel_status_alone_is_not_green(self):
        rollup = [{"context": "vercel", "state": "SUCCESS"}]
        blockers = merge_dev.evaluate(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertEqual(len([b for b in blockers if "absent" in b]),
                         len(merge_dev.REQUIRED_CHECKS))

    def test_failing_non_required_check_is_named(self):
        rollup = list(GREEN) + [{"name": "coverage", "conclusion": "FAILURE"}]
        blockers = merge_dev.evaluate(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertTrue(any("coverage" in b for b in blockers))

    def test_marker_must_start_the_comment(self):
        mid = f"as discussed, {merge_dev.REVIEW_MARKER} was posted earlier"
        blockers = merge_dev.evaluate(pr(), [mid])
        self.assertTrue(any("no merge" in b for b in blockers))
        self.assertEqual(merge_dev.evaluate(pr(), ["  \n" + REVIEW]), [])

    def test_refusal_text_never_contains_the_marker(self):
        blockers = merge_dev.evaluate(
            pr(isDraft=True, state="CLOSED", baseRefName="main",
               headRefName="x", statusCheckRollup=[]), ["nope"])
        self.assertTrue(blockers)
        self.assertFalse(any(merge_dev.REVIEW_MARKER in b for b in blockers))

    def test_multiple_blockers_all_reported(self):
        # draft + wrong base + 3 absent required checks + no marker = 6
        blockers = merge_dev.evaluate(
            pr(isDraft=True, baseRefName="staging", statusCheckRollup=[]), [])
        self.assertEqual(len(blockers), 6)


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


class CredentialTests(unittest.TestCase):
    """No silent fallback: if the App cannot mint, nothing merges."""

    def test_permissions_are_least_privilege(self):
        perms = merge_dev.MERGE_PERMISSIONS
        self.assertEqual(perms["contents"], "write")
        self.assertEqual(perms["pull_requests"], "write")
        # statusCheckRollup resolves workflow runs; read, never write.
        self.assertEqual(perms["actions"], "read")
        self.assertEqual(perms["checks"], "read")
        for name, level in perms.items():
            self.assertIn(level, ("read", "write"))
        self.assertNotIn("administration", perms)

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
