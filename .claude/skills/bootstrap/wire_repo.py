#!/usr/bin/env python3
"""Wire a freshly bootstrapped repo, and prove the wiring by verification.

Bootstrap used to hand Steve a manual step here, because the old PAT could
not administer a repo. The App can, so this does it — and then checks what
GitHub actually enforces rather than trusting the success codes it just
received. A 201 from the rulesets API means a ruleset was recorded; it
does not mean a branch is protected.

Protection is verified on both paths a change can take:

* The push path, by behaviour: a no-op fast-forward — point the branch's
  ref at the sha it already holds. Refused *by rules* means protected; a
  plain acceptance means not, and nothing changes either way. An error is
  not a refusal: a 500, a rate limit, an expired token all mean "could
  not verify", never "protected".

* The merge path, by reading back the rules GitHub reports as APPLYING
  to the branch, which must include a pull_request rule requiring at
  least one approving review. Zero required approvals requires a PR, not
  a human: a token holding `contents` + `pull_requests` write can open a
  PR and merge it unreviewed (demonstrated on a throwaway repo — PR #32,
  finding 1). This is a read-back, not a behavioural probe, because the
  behavioural test of the merge path is an actual merge, which is not
  harmless. It is still evidence rather than an echo of the payload:
  rules GitHub does not enforce drop out of the applying-rules listing.

The default branch and delete-branch-on-merge (wired off in the same
PATCH — a promotion PR's head is a long-lived branch) are verified by an
independent read-back, not the PATCH response's echo.

Free-plan repositories only get rulesets when they are **public**. A
private repo is therefore wired but unprotected, and its human-only merge
rule is carried by process alone. That is allowed. What is not allowed is
it being quiet: this exits 5 in that case, prints the fact, and hands the
caller a summary to put in the repo's CLAUDE.md and the central
needs-Steve digest (sofa-claude Issue #2).

Exit codes:
    0  wired, and every branch that should be protected is — both paths
    2  usage error
    4  wiring or verification failed partway. The repo may be partly
       wired: the output lists exactly what had been done, and says so
       when nothing had. Fix the cause and re-run.
    5  wired, but at least one branch is NOT protected (loud, not fatal)

Usage:
    wire_repo.py --repo OWNER/NAME --checkout PATH [--default dev]
                 [--branches dev,staging] [--protect main,staging]

Run from the workload repo's root with `--checkout .` — the script lives
in the skill directory, the credential comes from the checkout.
"""

import argparse
import importlib.util
import json
import pathlib
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"

# Refusal and plan-limit shapes, verified against the live API 2026-08-20:
# a ruleset refuses a ref write with 422 "Repository rule violations
# found"; a free-plan private repo answers rule reads with 403 "Upgrade to
# GitHub Pro or make this repository public to enable this feature."
# Only the ruleset shape is listed: this script creates rulesets, never
# classic branch protection, and classic protection's refusal shape is
# unverified — an unlisted refusal is inconclusive and exits 4, loudly,
# rather than being guessed at.
RULE_REFUSALS = ("rule violations",)
PLAN_LIMITS = ("upgrade to github pro", "make this repository public")


def plan_limited(detail):
    """GitHub's plan limitation, positively identified from its message."""
    return any(s in str(detail).lower() for s in PLAN_LIMITS)


class WiringError(RuntimeError):
    """Actionable; never carries a credential. May carry a partial
    `report` attribute listing what had been done before the failure."""


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
            f"{path} is missing. Either --checkout does not point at the "
            f"workload repo's root (run from that root with --checkout .), "
            f"or the seed copy is incomplete. The merge path in this repo "
            f"would have no way to authenticate; fix that before wiring.")
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
        # Explicitly nobody: omitting the list means the same today, but
        # the gate's whole value is that no actor bypasses it, so say so.
        "bypass_actors": [],
        "conditions": {"ref_name": {"include": [f"refs/heads/{branch}"],
                                    "exclude": []}},
        "rules": [{"type": "deletion"},
                  {"type": "non_fast_forward"},
                  {"type": "pull_request",
                   # 1, not 0: zero approvals requires a PR, not a human —
                   # a contents+pull_requests token could merge its own PR
                   # unreviewed (PR #32, finding 1).
                   "parameters": {"required_approving_review_count": 1,
                                  "dismiss_stale_reviews_on_push": False,
                                  "require_code_owner_review": False,
                                  "require_last_push_approval": False,
                                  "required_review_thread_resolution": False}}],
    }


def push_refused(token, owner, repo, branch):
    """Probe the push path by behaviour. Returns (verdict, detail).

    verdict: True = refused by rules, False = write accepted, None =
    could not verify. The probe is a no-op fast-forward — set the ref to
    the sha it already holds — so nothing changes whichever answer comes
    back. Only a recognised rules refusal counts as protection; every
    other failure is inconclusive, never a refusal.
    """
    status, ref = call(token, "GET", f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
    if status >= 400:
        return None, f"branch {branch} not readable ({status}: {ref})"
    sha = ref["object"]["sha"]
    status, detail = call(token, "PATCH",
                          f"/repos/{owner}/{repo}/git/refs/heads/{branch}",
                          {"sha": sha, "force": False})
    if status < 400:
        return False, "a direct write to this branch was ACCEPTED"
    if status == 422 and any(s in str(detail).lower() for s in RULE_REFUSALS):
        return True, f"refused by rules ({status}: {detail})"
    return None, (f"probe inconclusive ({status}: {detail}) — an error is "
                  f"not a refusal and must never be read as protection")


def merge_gate(token, owner, repo, branch):
    """Read back the merge-path rules GitHub reports as applying.
    Returns (verdict, detail).

    verdict: True = a pull_request rule applies and requires at least one
    approving review, False = it does not (including the free-plan case,
    where GitHub answers rule reads with its recognisable upgrade
    message), None = could not read.
    """
    status, rules = call(token, "GET",
                         f"/repos/{owner}/{repo}/rules/branches/{branch}")
    if status == 403 and plan_limited(rules):
        return False, ("rules unavailable on this plan for this repo "
                       f"({status}: {rules})")
    if status >= 400:
        return None, f"applying rules not readable ({status}: {rules})"
    pull_rules = [r for r in rules if r.get("type") == "pull_request"]
    if not pull_rules:
        return False, "no pull_request rule applies to this branch"
    required = max(((r.get("parameters") or {})
                    .get("required_approving_review_count") or 0)
                   for r in pull_rules)
    if required >= 1:
        return True, (f"pull_request rule applies, {required} approving "
                      f"review(s) required")
    return False, ("a pull_request rule applies but requires 0 approving "
                   "reviews — that requires a PR, not a human; a "
                   "contents+pull_requests token could merge its own PR")


def wire(owner, repo, checkout, default="dev", branches=("dev", "staging"),
         protect=("main", "staging")):
    gh_token = load_gh_token(checkout)
    report = {"repo": f"{owner}/{repo}", "default_branch": None,
              "delete_branch_on_merge": None,
              "branches": {}, "protected": {}, "unprotected": []}
    try:
        # This token never holds `administration`; verification reuses it
        # below, so the probes demonstrate what an unprivileged writer can
        # do. Installation tokens outlive this run by ~an hour.
        probe_token, _ = gh_token.mint(owner, [repo], {"contents": "write",
                                                       "metadata": "read"})
        status, ref = call(probe_token, "GET",
                           f"/repos/{owner}/{repo}/git/ref/heads/main")
        if status >= 400:
            raise WiringError(f"Cannot read refs/heads/main ({status}: {ref}). "
                              f"Was the repo initialised?")
        base = ref["object"]["sha"]
        for branch in branches:
            status, detail = call(probe_token, "POST",
                                  f"/repos/{owner}/{repo}/git/refs",
                                  {"ref": f"refs/heads/{branch}", "sha": base})
            if status < 400:
                report["branches"][branch] = "created"
            elif status == 422 and "already exists" in str(detail).lower():
                report["branches"][branch] = "already existed"
            else:
                report["branches"][branch] = f"creation FAILED ({status}: {detail})"
                raise WiringError(
                    f"Creating branch {branch!r} failed ({status}: {detail}). "
                    f"Stopping here: carrying on would leave a branch that "
                    f"later probes as unreadable and risks being misread as "
                    f"a plan limitation instead of a missing branch.")

        admin_token, _ = gh_token.mint(
            owner, [repo], {"administration": "write", "metadata": "read"},
            reason=f"bootstrap {owner}/{repo}: default branch, merge "
                   f"settings, and branch protection")
        # delete_branch_on_merge rides the same PATCH: a promotion PR's
        # head is a long-lived branch, so left on, the setting deletes
        # `staging` at the first promotion to `main`.
        status, body = call(admin_token, "PATCH", f"/repos/{owner}/{repo}",
                            {"default_branch": default,
                             "delete_branch_on_merge": False})
        if status >= 400:
            raise WiringError(f"Could not set the default branch and merge "
                              f"settings ({status}: {body}).")
        if body["default_branch"] != default:
            raise WiringError(
                f"GitHub accepted the change but reports the default branch "
                f"as {body['default_branch']!r}, not {default!r} — what it "
                f"accepted is not what it holds.")
        report["default_branch"] = body["default_branch"]
        for branch in protect:
            status, detail = call(admin_token, "POST",
                                  f"/repos/{owner}/{repo}/rulesets",
                                  ruleset_payload(branch))
            report["protected"][branch] = {"ruleset_api": status}
            if status < 400:
                continue
            if status == 403 and plan_limited(detail):
                continue  # positively identified; verification confirms below
            if status == 422 and "already" in str(detail).lower():
                continue  # a re-run: the ruleset survives from a prior attempt
            raise WiringError(
                f"Creating ruleset protect-{branch} failed ({status}: "
                f"{detail}). Neither the recognised plan limitation nor a "
                f"re-run duplicate: a rate limit or server error here must "
                f"fail the wiring, never pass as an accepted plan limitation.")

        # Verify what GitHub enforces, not what it accepted — both paths.
        # Reuses probe_token: minted before the admin work and never
        # holding `administration`, so the probes show what an
        # unprivileged writer can do.
        status, repo_state = call(probe_token, "GET", f"/repos/{owner}/{repo}")
        if status >= 400:
            raise WiringError(f"Cannot read the repo back for verification "
                              f"({status}: {repo_state}).")
        # Merge-settings fields are withheld from metadata-only callers;
        # this token holds contents, which GitHub documents as sufficient.
        if repo_state.get("default_branch") != default:
            raise WiringError(
                f"Read-back says the default branch is "
                f"{repo_state.get('default_branch')!r}, not {default!r}.")
        if repo_state.get("delete_branch_on_merge") is not False:
            raise WiringError(
                f"delete_branch_on_merge reads back as "
                f"{repo_state.get('delete_branch_on_merge')!r}, not False — "
                f"either the setting did not stick or this token cannot see "
                f"it. Left on, the first promotion deletes staging.")
        report["delete_branch_on_merge"] = False
        for branch in protect:
            state = report["protected"][branch]
            pushed, push_detail = push_refused(probe_token, owner, repo, branch)
            merged, merge_detail = merge_gate(probe_token, owner, repo, branch)
            state["push"] = push_detail
            state["merge"] = merge_detail
            if pushed is None or merged is None:
                raise WiringError(
                    f"Protection on {branch!r} could not be verified "
                    f"(push: {push_detail}; merge: {merge_detail}). Neither "
                    f"ENFORCED nor an accepted limitation can be claimed "
                    f"from an error — fix the cause and re-run.")
            # Plan-ness comes from GitHub's own message, carried in the
            # merge detail — never from the POST status alone.
            state["plan_limited"] = plan_limited(merge_detail)
            state["enforced"] = pushed and merged
            if not state["enforced"]:
                report["unprotected"].append(branch)
    except WiringError as err:
        err.report = report
        raise
    except Exception as err:
        wrapped = WiringError(f"{type(err).__name__}: {err}")
        wrapped.report = report
        raise wrapped from err
    return report


def summarise(report):
    branches = ", ".join(f"{name} ({state})" for name, state
                         in sorted(report["branches"].items()))
    lines = [f"Wired {report['repo']}: default branch "
             f"{report['default_branch']!r} (read back), delete-branch-"
             f"on-merge {report.get('delete_branch_on_merge')}, "
             f"branches {branches}."]
    for branch, state in sorted(report["protected"].items()):
        verdict = "ENFORCED" if state.get("enforced") else "NOT ENFORCED"
        lines.append(f"  {branch}: {verdict} (rulesets API returned "
                     f"{state['ruleset_api']})")
        lines.append(f"    push:  {state.get('push')}")
        lines.append(f"    merge: {state.get('merge')}")
    # Keyed on GitHub's own plan-limit message as verification saw it —
    # a bare 403 status is a proxy that rate limits and permission gaps
    # also produce, and those must never read as an accepted outcome.
    limited = [b for b in report["unprotected"]
               if report["protected"][b].get("plan_limited")]
    anomalies = [b for b in report["unprotected"] if b not in limited]
    if anomalies:
        lines.append("")
        lines.append("RECORDED BUT NOT ENFORCED on: " + ", ".join(anomalies) + ".")
        lines.append("GitHub does not enforce these rules, and verification "
                     "never saw the plan-limit message that is the one "
                     "acceptable reason for that (the rulesets API status "
                     "is printed above) — investigate before recording "
                     "anything; do not write it off as a plan limitation.")
    if limited:
        lines.append("")
        lines.append("PROCESS-ONLY ENFORCEMENT on: "
                     + ", ".join(limited) + ".")
        lines.append("Rulesets are unavailable here — on the free plan they "
                     "cover public repositories only, and org-level rulesets "
                     "need Enterprise. Nothing in GitHub will stop a direct "
                     "push or an unreviewed merge to those branches; the "
                     "human-only merge rule is carried by process alone.")
        lines.append("Record this in the repo's CLAUDE.md and the central "
                     "needs-Steve digest (sofa-claude Issue #2). It is an "
                     "accepted outcome, not a silent one.")
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
        print("WIRING FAILURE — the repo may be partly wired. Fix the cause "
              "and re-run; treat exit 4 as neither clean nor wired.",
              file=sys.stderr)
        print(str(err), file=sys.stderr)
        partial = getattr(err, "report", None)
        done = partial and (partial["default_branch"] is not None
                            or partial["branches"] or partial["protected"])
        if done:
            print("Done before the failure (none of it verified):",
                  file=sys.stderr)
            print(json.dumps(partial, indent=2), file=sys.stderr)
        else:
            print("Nothing had been changed yet.", file=sys.stderr)
        return 4
    print(json.dumps(report, indent=2) if args.json else summarise(report))
    return 5 if report["unprotected"] else 0


if __name__ == "__main__":
    sys.exit(main())
