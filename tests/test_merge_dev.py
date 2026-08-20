"""Tests for the seed kit's paved-path merge script's decision logic."""

import importlib.util
import pathlib
import unittest

_path = pathlib.Path(__file__).resolve().parent.parent / "seed" / "scripts" / "merge_dev.py"
_spec = importlib.util.spec_from_file_location("merge_dev", _path)
merge_dev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(merge_dev)

REVIEW = f"{merge_dev.REVIEW_MARKER}\nLooks correct; one keep-grade note filed."


def pr(**over):
    base = {
        "isDraft": False,
        "state": "OPEN",
        "baseRefName": "dev",
        "headRefName": "claude/unit-1",
        "statusCheckRollup": [{"name": "ci", "conclusion": "SUCCESS"}],
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

    def test_no_checks_is_not_green(self):
        blockers = merge_dev.evaluate(pr(statusCheckRollup=[]), [REVIEW])
        self.assertTrue(any("absent is not green" in b for b in blockers))

    def test_failed_check_blocks_and_is_named(self):
        rollup = [{"name": "ci", "conclusion": "SUCCESS"},
                  {"name": "coverage", "conclusion": "FAILURE"}]
        blockers = merge_dev.evaluate(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertTrue(any("coverage" in b for b in blockers))

    def test_pending_check_blocks(self):
        rollup = [{"name": "ci", "state": "PENDING"}]
        blockers = merge_dev.evaluate(pr(statusCheckRollup=rollup), [REVIEW])
        self.assertTrue(any("CI not green" in b for b in blockers))

    def test_missing_review_comment_blocks(self):
        blockers = merge_dev.evaluate(pr(), ["lgtm!"])
        self.assertTrue(any("no merge" in b for b in blockers))

    def test_review_marker_anywhere_in_comments_passes(self):
        self.assertEqual(merge_dev.evaluate(pr(), ["chatter", REVIEW]), [])

    def test_multiple_blockers_all_reported(self):
        blockers = merge_dev.evaluate(
            pr(isDraft=True, baseRefName="staging", statusCheckRollup=[]), [])
        self.assertEqual(len(blockers), 4)


if __name__ == "__main__":
    unittest.main()
