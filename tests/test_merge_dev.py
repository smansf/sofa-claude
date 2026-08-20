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


class TransportTests(unittest.TestCase):
    def test_transport_failure_is_loud_and_does_not_merge(self):
        err = subprocess.CalledProcessError(1, ["gh"], stderr="boom")
        with mock.patch.object(merge_dev, "_gh", side_effect=err):
            with mock.patch("builtins.print") as fake_print:
                self.assertEqual(merge_dev.main(["merge_dev.py", "12"]), 3)
        printed = " ".join(str(c.args[0]) for c in fake_print.call_args_list)
        self.assertIn("TRANSPORT FAILURE", printed)
        self.assertIn("boom", printed)
        self.assertIn("Do NOT merge by hand", printed)


if __name__ == "__main__":
    unittest.main()
