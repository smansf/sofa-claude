#!/usr/bin/env python3
"""The paved path for merging a workload PR to dev.

One instruction replaces four rules: this script refuses unless every
required CI check succeeded, a fresh-context reviewer pass is posted, the
base is dev, the head is claude/*, and the PR isn't a draft. It is a
paved path, not a wall — nothing stops `gh pr merge` by hand, which is
why merging any other way is declared a defect in CLAUDE.md.

On transport failure it says so and stops: do NOT merge by hand as a
workaround — fix the cause or put it in the needs-Steve digest.

Usage: python3 scripts/merge_dev.py <PR-number>
"""

import json
import subprocess
import sys

REVIEW_MARKER = "## Reviewer pass"
# Bootstrap aligns these with the workload ci.yml's actual job names.
REQUIRED_CHECKS = ("lint", "test", "secrets")
# Acceptable states for checks that are NOT required (required checks
# must be SUCCESS outright — a skipped required check is not green).
GOOD_CONCLUSIONS = {"SUCCESS", "NEUTRAL", "SKIPPED"}


def evaluate(pr, comment_bodies):
    """Return the list of blockers; empty means the merge may proceed.

    Invariant: no blocker string may contain REVIEW_MARKER, so a refusal
    pasted into a PR comment can never become the passing credential.
    """
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
    statuses = {}
    for c in pr.get("statusCheckRollup") or []:
        name = c.get("name") or c.get("context") or "?"
        statuses[name] = (c.get("conclusion") or c.get("state") or "").upper()
    for req in REQUIRED_CHECKS:
        if req not in statuses:
            blockers.append(f"Required check {req!r} is absent — absent is "
                            "not green.")
        elif statuses[req] != "SUCCESS":
            blockers.append(f"Required check {req!r} is "
                            f"{statuses[req] or 'UNKNOWN'}, not SUCCESS.")
    bad_others = sorted(n for n, s in statuses.items()
                        if n not in REQUIRED_CHECKS
                        and s not in GOOD_CONCLUSIONS)
    if bad_others:
        blockers.append("Failing checks: " + ", ".join(bad_others))
    if not any((body or "").lstrip().startswith(REVIEW_MARKER)
               for body in comment_bodies):
        blockers.append("No reviewer-pass comment found — a fresh-context "
                        "reviewer must post one, with the marker heading "
                        "on its first line (see CLAUDE.md). No comment, "
                        "no merge.")
    return blockers


def _gh(args):
    return subprocess.run(["gh"] + args, check=True, capture_output=True,
                          text=True).stdout


def _transport_failure(err):
    print("TRANSPORT FAILURE — nothing was merged.")
    detail = (getattr(err, "stderr", "") or "").strip()
    if detail:
        print(detail)
    print("Do NOT merge by hand as a workaround — fix the cause or put "
          "it in the needs-Steve digest.")
    return 3


def main(argv):
    if len(argv) != 2 or not argv[1].isdigit():
        print(__doc__)
        return 2
    number = argv[1]
    try:
        pr = json.loads(_gh(["pr", "view", number, "--json",
                             "isDraft,state,baseRefName,headRefName,"
                             "statusCheckRollup,comments"]))
    except subprocess.CalledProcessError as err:
        return _transport_failure(err)
    bodies = [c.get("body", "") for c in pr.get("comments") or []]
    blockers = evaluate(pr, bodies)
    if blockers:
        print(f"REFUSED — PR #{number} is not mergeable to dev:")
        for b in blockers:
            print(f"  - {b}")
        return 1
    try:
        _gh(["pr", "merge", number, "--squash", "--delete-branch"])
    except subprocess.CalledProcessError as err:
        return _transport_failure(err)
    print(f"Merged PR #{number} to dev (squash) and deleted its branch.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
