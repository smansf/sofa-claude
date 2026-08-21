#!/usr/bin/env python3
"""Wire a freshly bootstrapped repo, and prove the wiring by behaviour.

Bootstrap used to hand Steve a manual step here, because the old PAT could
not administer a repo. The App can, so this does it — and then checks what
GitHub actually enforces rather than trusting the success codes it just
received. A 201 from the rulesets API means a ruleset was recorded; it
does not mean a branch is protected.

The protection probe is a no-op fast-forward: point a branch's ref at the
sha it already has. On a protected branch GitHub refuses it; on an
unprotected one it succeeds and changes nothing. Either way it creates no
commit, no file, and no junk to clean up — which matters because the
"unprotected" answer is a normal outcome here, not an error.

Free-plan repositories only get rulesets when they are **public**. A
private repo is therefore wired but unprotected, and its human-only merge
rule is carried by process alone. That is allowed. What is not allowed is
it being quiet: this exits 5 in that case, prints the fact, and hands the
caller a summary to put in the repo's CLAUDE.md and the needs-Steve
digest.

Exit codes:
    0  wired, and every branch that should be protected is
    2  usage error
    4  credential failure -- nothing was changed
    5  wired, but at least one branch is NOT protected (loud, not fatal)

Usage:
    wire_repo.py --repo OWNER/NAME --checkout PATH [--default dev]
                 [--branches dev,staging] [--protect main,staging]
"""

import argparse
import importlib.util
import json
import pathlib
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"


class WiringError(RuntimeError):
    """Actionable; never carries a credential."""


def load_gh_token(checkout):
    """Import the credential path from the repo being wired.

    Deliberately sourced from the target checkout, not from this skill:
    if bootstrap failed to copy `scripts/gh_token.py`, wiring stops here
    rather than succeeding and leaving a repo whose merge path cannot
    authenticate.
    """
    path = pathlib.Path(checkout).expanduser().resolve() / "scripts" / "gh_token.py"
    if not path.exists():
        raise WiringError(
            f"{path} is missing — the seed copy is incomplete. The merge path "
            f"in this repo would have no way to authenticate. Fix the copy "
            f"before wiring.")
    spec = importlib.util.spec_from_file_location("gh_token", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def call(token, method, path, payload=None):
    request = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "sofa-claude-bootstrap"})
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read()
            return response.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as err:
        detail = ""
        try:
            detail = json.loads(err.read()).get("message", "")
        except Exception:
            pass
        return err.code, detail
    except urllib.error.URLError as err:
        raise WiringError(f"Cannot reach GitHub for {method} {path}: {err.reason}")


def ruleset_payload(branch):
    return {
        "name": f"protect-{branch}",
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": [f"refs/heads/{branch}"],
                                    "exclude": []}},
        "rules": [{"type": "deletion"},
                  {"type": "non_fast_forward"},
                  {"type": "pull_request",
                   "parameters": {"required_approving_review_count": 0,
                                  "dismiss_stale_reviews_on_push": False,
                                  "require_code_owner_review": False,
                                  "require_last_push_approval": False,
                                  "required_review_thread_resolution": False}}],
    }


def is_protected(token, owner, repo, branch):
    """Probe by behaviour. Returns (protected: bool, detail: str).

    A no-op fast-forward: set the ref to the sha it already holds. Refused
    means protected; allowed means not, and nothing changed either way.
    """
    status, ref = call(token, "GET", f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
    if status >= 400:
        return False, f"branch {branch} not readable ({status}: {ref})"
    sha = ref["object"]["sha"]
    status, detail = call(token, "PATCH",
                          f"/repos/{owner}/{repo}/git/refs/heads/{branch}",
                          {"sha": sha, "force": False})
    if status >= 400:
        return True, f"refused ({status})"
    return False, "a direct write to this branch was ACCEPTED"


def wire(owner, repo, checkout, default="dev", branches=("dev", "staging"),
         protect=("main", "staging")):
    gh_token = load_gh_token(checkout)
    account, name = owner, repo
    report = {"repo": f"{owner}/{repo}", "default_branch": None,
              "branches": {}, "protected": {}, "unprotected": []}

    token, _ = gh_token.mint(account, [name], {"contents": "write",
                                               "metadata": "read"})
    status, ref = call(token, "GET", f"/repos/{owner}/{repo}/git/ref/heads/main")
    if status >= 400:
        raise WiringError(f"Cannot read refs/heads/main ({status}: {ref}). "
                          f"Was the repo initialised?")
    base = ref["object"]["sha"]
    for branch in branches:
        status, detail = call(token, "POST", f"/repos/{owner}/{repo}/git/refs",
                              {"ref": f"refs/heads/{branch}", "sha": base})
        report["branches"][branch] = ("created" if status < 400
                                      else f"exists or refused ({status})")

    token, _ = gh_token.mint(
        account, [name], {"administration": "write", "metadata": "read"},
        reason=f"bootstrap {owner}/{repo}: default branch and branch protection")
    status, body = call(token, "PATCH", f"/repos/{owner}/{repo}",
                        {"default_branch": default})
    if status >= 400:
        raise WiringError(f"Could not set the default branch ({status}: {body}).")
    report["default_branch"] = body["default_branch"]
    for branch in protect:
        status, body = call(token, "POST", f"/repos/{owner}/{repo}/rulesets",
                            ruleset_payload(branch))
        report["protected"][branch] = {"ruleset_api": status}

    # Verify what GitHub enforces, not what it accepted.
    token, _ = gh_token.mint(account, [name], {"contents": "write",
                                               "metadata": "read"})
    for branch in protect:
        protected, detail = is_protected(token, owner, repo, branch)
        report["protected"][branch]["enforced"] = protected
        report["protected"][branch]["probe"] = detail
        if not protected:
            report["unprotected"].append(branch)
    return report


def summarise(report):
    lines = [f"Wired {report['repo']}: default branch "
             f"{report['default_branch']!r}, branches "
             f"{', '.join(sorted(report['branches']))}."]
    for branch, state in sorted(report["protected"].items()):
        verdict = "ENFORCED" if state.get("enforced") else "NOT ENFORCED"
        lines.append(f"  {branch}: {verdict} — probe {state.get('probe')} "
                     f"(rulesets API returned {state['ruleset_api']})")
    if report["unprotected"]:
        lines.append("")
        lines.append("PROCESS-ONLY ENFORCEMENT on: "
                     + ", ".join(report["unprotected"]) + ".")
        lines.append("Rulesets are unavailable here — on the free plan they "
                     "cover public repositories only, and org-level rulesets "
                     "need Enterprise. Nothing in GitHub will stop a direct "
                     "push to those branches; the human-only merge rule is "
                     "carried by process alone.")
        lines.append("Record this in the repo's CLAUDE.md and the needs-Steve "
                     "digest. It is an accepted outcome, not a silent one.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo", required=True, metavar="OWNER/NAME")
    parser.add_argument("--checkout", required=True,
                        help="path to the repo's working copy (holds scripts/)")
    parser.add_argument("--default", default="dev")
    parser.add_argument("--branches", default="dev,staging")
    parser.add_argument("--protect", default="main,staging")
    parser.add_argument("--json", action="store_true", help="emit the raw report")
    args = parser.parse_args(argv)

    if "/" not in args.repo:
        parser.error("--repo takes OWNER/NAME")
    owner, name = args.repo.split("/", 1)
    split = lambda s: tuple(x.strip() for x in s.split(",") if x.strip())
    try:
        report = wire(owner, name, args.checkout, args.default,
                      split(args.branches), split(args.protect))
    except Exception as err:
        print(f"WIRING FAILURE — the repo may be partly wired.\n{err}",
              file=sys.stderr)
        return 4
    print(json.dumps(report, indent=2) if args.json else summarise(report))
    return 5 if report["unprotected"] else 0


if __name__ == "__main__":
    sys.exit(main())
