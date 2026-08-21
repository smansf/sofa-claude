---
name: bootstrap
description: Bootstrap a workload repo from the seed kit — elicit a charter with stakes tier and falsifiable end condition, add a stakes-scaled design record, copy and adapt seed/, wire branches, labels, and standing issues.
---

# bootstrap

Run this *from the workload repo's own directory*, never from sofa-claude.

Every `gh` call in this skill runs under a short-lived App token minted
by the workload's own copy of the helper — `python3 scripts/gh_token.py
--account <owner> --repos <name> --perm <name=level> -- gh ...` — never
ambient session auth. Grant 4's regime has no ambient fallback, and a
step that "just works" on session credentials today is the step that
breaks the day the PAT is gone.

1. **Charter first** (`docs/charter.md`, one page, elicited from Steve):
   what is being built and why; who uses it; the **stakes tier**
   (throwaway / standard / production) that sets review depth everywhere;
   the **test floor**, in whatever shape the subject actually has — a
   coverage percentage, fixture-corpus completeness, a property suite —
   which must be mechanically checkable by CI, because a shape that forces
   a fake number is the wrong shape; and the project's **end condition**
   — what done looks like, written before work starts and *falsifiable*:
   if you can't say how you'd test that it's met, rewrite it until you can.
2. **Design record — scaled by the stakes tier.** Throwaway: skip
   entirely; the charter is enough. Standard and production: one page
   (`docs/design.md`) — stack choice and why, architecture sketch, data
   shape, main structural risks — reviewed with `doc-review`. At
   production stakes, Steve's approving GitHub review **on the bootstrap
   PR itself** is the approval artifact — Claude merges that PR only
   after it exists; chat assent is not approval. Decisions, not
   documents: a section with nothing load-bearing to say gets deleted,
   not filled.
3. **Copy the seed**: `seed/CLAUDE.md.template` → `CLAUDE.md`,
   `seed/workflows/ci.yml` → `.github/workflows/ci.yml`,
   `seed/workflows/backlog-expiry.yml` → `.github/workflows/backlog-expiry.yml`,
   `seed/pull_request_template.md` → `.github/pull_request_template.md`,
   `seed/ISSUE_TEMPLATE/unit.yml` → `.github/ISSUE_TEMPLATE/unit.yml`,
   `seed/ISSUE_TEMPLATE/config.yml` → `.github/ISSUE_TEMPLATE/config.yml`,
   `seed/scripts/gh_token.py` → `scripts/gh_token.py` (the credential
   path for scripted access; `merge_dev.py` imports it from alongside
   itself and stops rather than falling back to ambient auth if it is
   absent — keep its executable bit, mode `100755`, since it has a
   shebang and step 6 invokes it directly),
   `seed/scripts/merge_dev.py` → `scripts/merge_dev.py` (align its
   `REQUIRED_CHECKS` with the workload ci.yml's job names, and keep its
   executable bit — mode `100755`, so the shebang stays honest and a lint
   config that enables EXE001 has nothing to flag; note ruff's defaults do
   not, so nothing in a bootstrapped repo catches a dropped bit for you),
   `seed/gitignore` → `.gitignore` (extend for the stack; without it the
   first `git add -A` after a test run can commit bytecode that has secret
   fixtures folded into it).
   Fill every `{{PLACEHOLDER}}` from the charter and design record. The
   copy is a divorce: this repo owes sofa-claude nothing after.
   **The bootstrap PR ships at least one real test**, because `ci.yml`
   has no zero-test escape hatch: most runners exit non-zero when nothing
   is collected, and that is correct — a `test` job that ran no tests is
   not a passing `test` job, and a CI branch that reports SUCCESS having
   run nothing is the legacy failure (0005) rebuilt inside the test gate.
   Ship the smallest real module the charter implies — the CLI entry
   point, the one exported function — plus a test covering it. A charter
   assertion test alone is not enough when the floor is a coverage
   percentage: `--cov-fail-under` against a repo with no product code
   reports no data and fails, which is defect 2 recurring one step later,
   because the floor and the test run are the same command. Real module
   plus real test satisfies every floor shape.
4. **Wire the repo**: from the workload repo's root — where this whole
   skill already runs — invoke
   `python3 ~/.claude/skills/bootstrap/wire_repo.py --repo OWNER/NAME
   --checkout .`. The script lives in the skill; the credential comes
   from the checkout (`scripts/gh_token.py`), so it stops if the seed
   copy is incomplete rather than wiring a repo whose merge path could
   never authenticate. It creates `dev` and `staging`, sets `dev` as the
   default branch, applies the `protect-main` / `protect-staging`
   rulesets — requiring **one approving human review** on the merge
   path, because zero approvals requires a PR, not a human — and then
   **verifies what GitHub actually enforces**, on both paths a change
   can take: a no-op fast-forward push that must be refused *by rules*
   (an error is not a refusal), and a read-back of the rules GitHub
   reports as applying to the branch, which must include that
   one-approval merge gate. A 201 from the rulesets API is not
   protection; only the two checks together are. Exit 0 means everything
   that should be protected is. **Exit 5 means wired but NOT protected**,
   and its summary says which of two very different things happened:
   the free-plan limitation (rulesets cover public repos only, org-level
   rulesets need Enterprise — an accepted outcome: copy the summary
   verbatim into the repo's CLAUDE.md **and** the central needs-Steve
   digest, smansf/sofa-claude Issue #2, workload repos carry no digest
   of their own, and fill `{{ENFORCEMENT}}` in the seeded CLAUDE.md from
   it so the distinction outlives this session — step 6's placeholder
   grep catches it if you skip that), or **recorded-but-unenforced**,
   an anomaly to investigate and never to record as accepted. **Exit 4
   means wiring or verification failed partway**: its output lists
   exactly what had been done — and says so when nothing was — but none
   of it is verified. Fix the cause and re-run; never treat exit 4 as
   either clean or wired.
   **Disable "automatically delete head branches"**
   (`python3 scripts/gh_token.py --account OWNER --repos NAME
   --perm administration=write --reason "bootstrap OWNER/NAME: turn off
   delete-branch-on-merge" -- gh repo edit OWNER/NAME
   --delete-branch-on-merge=false`, then confirm under a read mint:
   `... --perm metadata=read -- gh repo view OWNER/NAME --json
   deleteBranchOnMerge`): a promotion PR's head *is*
   a long-lived branch, so the setting deletes `staging` the first time
   Steve promotes to `main`, and `merge_dev.py` already deletes unit
   branches itself. The App can do this now — it holds repository
   administration — so a 403 here is a real failure to investigate, not
   the expected outcome it once was (sofa-claude Issue #14, closed).
   Do not write it as a standing bar the repo starts out violating: the
   seeded CLAUDE.md carries the check at the moment it bites, holding the
   *first promotion* until the setting is off.
   Create labels `urgent`, `keep`,
   `standing`, and the standing handoff issue **labeled `standing`**
   (unlabeled, the repo's own expiry workflow will close it), all under
   one `--perm issues=write` mint; fill `{{HANDOFF_ISSUE}}` in CLAUDE.md
   with the issue's number. Vercel wiring is Steve's step — list it in
   the needs-Steve digest, don't wait.
5. **Propose the first unit**: one issue, frozen acceptance criteria,
   sized to reach `dev` within a session. Product code, not process — if
   the process pinches during the unit, that's a sofa-claude bleed to
   note, not machinery to build here.
6. **Verify and file** — bootstrap closes by checking, not asserting.
   Runs **after the bootstrap PR merges**; if the session ends first
   (production stakes waiting on Steve's review), record step 6 as owed
   in the new repo's handoff issue — the next session runs it before any
   unit work. Mechanically confirm, via `gh` against the default branch
   (one `--perm contents=read --perm issues=read --perm metadata=read`
   mint covers this step's reads), every item steps 3–4 claimed: default branch is `dev`; `staging`
   exists; labels `urgent`, `keep`, `standing` exist; `ci.yml`,
   `backlog-expiry.yml`, `pull_request_template.md`, both issue templates
   (`config.yml` with `blank_issues_enabled: false`), `.gitignore`, and
   `scripts/merge_dev.py` (its `REQUIRED_CHECKS` matching ci.yml's job
   names, its executable bit intact) and `scripts/gh_token.py` are all
   present; **the credential path actually works** — mint
   `merge_dev.MERGE_PERMISSIONS` verbatim and run one `gh` call under it.
   Not a read-only token, and not a hand-written subset: requesting a
   permission the installation has not been granted 422s the *whole* mint,
   so a narrower probe passes while the merge path is dead. The file being
   present proves nothing about the repo being inside the App's
   installation, and a green mint of the wrong permissions proves nothing
   about the merge. A personal-account installation is scoped to selected
   repositories and a new repo is **not** added automatically; adding it
   needs a user-to-server token, so it is Steve's ceremony, not Claude's.
   A mint that fails here means the first unit will reach a green PR and
   then be unable to merge, so it is a needs-Steve digest entry with the
   exact step (App → Install → this repo), never a silent pass. An
   org installation set to *All repositories* covers new repos
   automatically — confirm which of the two applies and record it;
   **no seed placeholder survives** in any copied file — grep for `{{`
   and discard only `${{` (GitHub Actions expressions, which are
   legitimate and permanent). Do not narrow this to `{{[A-Z_]\+}}`: the
   stakes tier is written `{{throwaway | standard | production}}` and
   would slip through, leaving review depth read off an unfilled slot
   forever. An unfilled placeholder is the seed silently ceasing to be
   authoritative, which is the defect class this step exists for. The
   `test` job ran a real command, and the repo tracks at least one test
   file and the module it covers. `deleteBranchOnMerge` is false, or the
   needs-Steve digest carries it with the click path;
   the standing handoff issue exists, carries `standing`, and CLAUDE.md
   names its number. A failed check that one `gh` command repairs is
   re-run once, re-verified, and noted in the
   bootstrap PR — repaired loudly, never silently. What still fails gets
   filed in the new repo, labeled by the seeded triage doctrine —
   `urgent` when it invalidates the first unit's premise, else `keep`;
   a wrong default branch additionally stays under step 4's
   stop-and-digest rule. Steve-owed items (Vercel wiring, ruleset
   creation) go in the needs-Steve digest with the exact steps.
   Bootstrap ends only when every check is green or every gap is filed.

Total bootstrap budget: one session, one PR into the workload's `dev`
(charter + design record + seed files). If it wants to grow beyond that,
stop — that is a bleed to raise in sofa-claude, not a bigger bootstrap.
