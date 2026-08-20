#!/usr/bin/env python3
"""The one way a workload PR merges to dev.

Checks everything the process requires and refuses loudly otherwise, so a
session needs to remember one instruction ("merge via this script"), not
four rules. Uses `gh` for all transport.

Usage: python3 scripts/merge_dev.py <PR-number>
"""

import json
import subprocess
import sys

REVIEW_MARKER = "## Reviewer pass"
GOOD_CONCLUSIONS = {"SUCCESS", "NEUTRAL", "SKIPPED"}


def evaluate(pr, comment_bodies):
    """Return the list of blockers; empty means the merge may proceed."""
    blockers = []
    if pr.get("isDraft"):
        blockers.append("PR is a draft — ready means merging is the only "
                        "step left, and this PR isn't there yet.")
    if pr.get("state") != "OPEN":
        blockers.append(f"PR state is {pr.get('state')!r}, not OPEN.")
    if pr.get("baseRefName") != "dev":
        blockers.append(f"Base branch is {pr.get('baseRefName')!r} — this "
                        "script merges to dev only; staging and main are "
                        "Steve's promotions.")
    if not str(pr.get("headRefName", "")).startswith("claude/"):
        blockers.append(f"Head branch {pr.get('headRefName')!r} is not a "
                        "claude/* branch.")
    checks = pr.get("statusCheckRollup") or []
    if not checks:
        blockers.append("No CI checks reported on this PR — green CI is "
                        "required, and absent is not green.")
    else:
        bad = [c.get("name") or c.get("context") or "?" for c in checks
               if (c.get("conclusion") or c.get("state") or "").upper()
               not in GOOD_CONCLUSIONS]
        if bad:
            blockers.append("CI not green: " + ", ".join(sorted(bad)))
    if not any(REVIEW_MARKER in (body or "") for body in comment_bodies):
        blockers.append(f"No reviewer-pass comment found (a PR comment "
                        f"starting {REVIEW_MARKER!r} is required — no "
                        "comment, no merge).")
    return blockers


def _gh(args):
    return subprocess.run(["gh"] + args, check=True, capture_output=True,
                          text=True).stdout


def main(argv):
    if len(argv) != 2 or not argv[1].isdigit():
        print(__doc__)
        return 2
    number = argv[1]
    pr = json.loads(_gh(["pr", "view", number, "--json",
                         "isDraft,state,baseRefName,headRefName,"
                         "statusCheckRollup,comments"]))
    bodies = [c.get("body", "") for c in pr.get("comments") or []]
    blockers = evaluate(pr, bodies)
    if blockers:
        print(f"REFUSED — PR #{number} is not mergeable to dev:")
        for b in blockers:
            print(f"  - {b}")
        return 1
    _gh(["pr", "merge", number, "--squash", "--delete-branch"])
    print(f"Merged PR #{number} to dev (squash) and deleted its branch.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
