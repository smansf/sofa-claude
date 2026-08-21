#!/usr/bin/env python3
"""The paved path for merging a workload PR to dev.

One instruction replaces four rules: this script refuses unless every
required CI check succeeded, a fresh-context reviewer pass is posted, the
base is dev, the head is claude/*, and the PR isn't a draft. It is a
paved path, not a wall — nothing stops `gh pr merge` by hand, which is
why merging any other way is declared a defect in CLAUDE.md.

On transport failure it says so and stops: do NOT merge by hand as a
workaround — fix the cause or put it in the needs-Steve digest.

Credentials come from the App via scripts/gh_token.py, scoped to this
repository and to the permissions a merge actually needs. If minting
fails, this script stops at exit 4 without calling `gh` at all — it does
not retry under whatever credential the environment happens to carry,
because a silent fallback is how a broad standing token survives a
migration meant to remove it (governance/grants.md, Grant 4). It cannot
scrub the environment it runs in; what it guarantees is its own conduct.

Usage: python3 scripts/merge_dev.py <PR-number>
"""

import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys

# `gh pr view --json statusCheckRollup` resolves each check's workflow
# run, which needs actions:read — verified against a private repo, where
# omitting it fails with "Resource not accessible by integration" rather
# than returning a partial rollup. Read level throughout except the two
# writes the merge itself performs.
MERGE_PERMISSIONS = {
    "contents": "write",       # squash-merge, delete the branch
    "pull_requests": "write",  # perform the merge; read the comments
    "checks": "read",
    "actions": "read",
    "metadata": "read",
}
# NOT included: `statuses`. statusCheckRollup also returns StatusContext
# nodes — commit statuses, which is what a Vercel preview posts — and
# those are read under a separate Commit statuses permission the App has
# not been granted (requesting it 422s the whole mint). Until it is
# granted, a repo whose CI posts commit statuses may see them missing
# from the rollup, and a missing check is not evaluated as a blocker.
# Tracked in sofa-claude Issue #26; REQUIRED_CHECKS still catches an
# absent required check, which is the case that matters most.


def _gh_token_module():
    path = pathlib.Path(__file__).resolve().parent / "gh_token.py"
    if not path.exists():
        raise RuntimeError(
            f"{path} is missing. It is the only sanctioned credential path; "
            f"bootstrap copies it alongside this script.")
    spec = importlib.util.spec_from_file_location("gh_token", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def repo_slug(remote_url):
    """(owner, repo) from a git remote URL, SSH or HTTPS."""
    match = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", remote_url.strip())
    if not match:
        raise RuntimeError(f"Cannot parse an owner/repo out of {remote_url!r}.")
    return match.group(1), match.group(2)


def _origin():
    url = subprocess.run(["git", "remote", "get-url", "origin"],
                         check=True, capture_output=True, text=True).stdout
    return repo_slug(url)

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


def _gh(args, env):
    return subprocess.run(["gh"] + args, check=True, capture_output=True,
                          text=True, env=env).stdout


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
        owner, repo = _origin()
        gh_token = _gh_token_module()
        token, _ = gh_token.mint(owner, [repo], MERGE_PERMISSIONS)
    except Exception as err:
        # Deliberately broad, and it must stay that way: exit 4 is the
        # "nothing was merged, and not because the PR was blocked" signal.
        # A traceback escaping here would exit 1 — the same status as a
        # legitimate refusal — so an unattended run could not tell a
        # network blip from a blocked PR, and none of the text below
        # would print.
        print("CREDENTIAL FAILURE — nothing was merged.")
        print(str(err))
        print("Do NOT merge by hand as a workaround, and do not fall back to "
              "another credential — fix the cause or put it in the "
              "needs-Steve digest.")
        return 4
    env = dict(os.environ, GH_TOKEN=token, GITHUB_TOKEN=token)
    try:
        fields = ("isDraft,state,baseRefName,headRefName,"
                  "statusCheckRollup,comments")
        pr = json.loads(_gh(["pr", "view", number, "--json", fields], env))
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
        _gh(["pr", "merge", number, "--squash", "--delete-branch"], env)
    except subprocess.CalledProcessError as err:
        return _transport_failure(err)
    print(f"Merged PR #{number} to dev (squash) and deleted its branch.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
