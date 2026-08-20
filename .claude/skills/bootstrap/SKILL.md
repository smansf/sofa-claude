---
name: bootstrap
description: Bootstrap a workload repo from the seed kit — elicit a charter with stakes tier and falsifiable end condition, add a stakes-scaled design record, copy and adapt seed/, wire branches, labels, and standing issues.
---

# bootstrap

Run this *from the workload repo's own directory*, never from sofa-claude.

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
   The default that always works: a test asserting `docs/charter.md`
   states an end condition and the test floor, which is a real invariant
   that really breaks. Fill `{{TEST_COMMAND_WITH_FLOOR}}` so it exercises
   it.
4. **Wire the repo**: create `dev` and `staging` from `main`; **set `dev`
   as the default branch, then verify it stuck** (`gh repo view --json
   defaultBranchRef` must say `dev` — if it doesn't, stop wiring and put
   it in the needs-Steve digest, because unit auto-close and the expiry
   record both silently lie until it's fixed). Unit issues then auto-close
   when their PR merges to `dev`, and new PRs target `dev` by default.
   **Disable "automatically delete head branches"**
   (`gh repo edit --delete-branch-on-merge=false`, then confirm with
   `gh repo view --json deleteBranchOnMerge`): a promotion PR's head *is*
   a long-lived branch, so the setting deletes `staging` the first time
   Steve promotes to `main`, and `merge_dev.py` already deletes unit
   branches itself. **Expect this to 403** — repo administration is
   outside the current token (sofa-claude Issue #14), so the normal
   outcome is a needs-Steve digest entry with the exact click path
   (Settings → General, ~15 s), not a repaired setting. Do not write it as
   a standing bar the repo starts out violating: the seeded CLAUDE.md
   carries the check at the moment it bites, holding the *first promotion*
   until the setting is off. Branch protection also exempts a branch, but
   is unavailable on private repos at this plan — never rely on it.
   Create labels `urgent`, `keep`,
   `standing`; create the standing handoff issue **labeled `standing`**
   (unlabeled, the repo's own expiry workflow will close it) and fill
   `{{HANDOFF_ISSUE}}` in CLAUDE.md with its number. Vercel wiring is
   Steve's step — list it in the needs-Steve digest, don't wait.
5. **Propose the first unit**: one issue, frozen acceptance criteria,
   sized to reach `dev` within a session. Product code, not process — if
   the process pinches during the unit, that's a sofa-claude bleed to
   note, not machinery to build here.
6. **Verify and file** — bootstrap closes by checking, not asserting.
   Runs **after the bootstrap PR merges**; if the session ends first
   (production stakes waiting on Steve's review), record step 6 as owed
   in the new repo's handoff issue — the next session runs it before any
   unit work. Mechanically confirm, via `gh` against the default branch,
   every item steps 3–4 claimed: default branch is `dev`; `staging`
   exists; labels `urgent`, `keep`, `standing` exist; `ci.yml`,
   `backlog-expiry.yml`, `pull_request_template.md`, both issue templates
   (`config.yml` with `blank_issues_enabled: false`), `.gitignore`, and
   `scripts/merge_dev.py` (its `REQUIRED_CHECKS` matching ci.yml's job
   names, its executable bit intact) are all present;
   **no seed placeholder survives** in any copied file — grep for
   `{{[A-Z_]\+}}`, the seed's own placeholder shape, **not** a bare `{{`,
   which would match the workflows' legitimate `${{ secrets.GITHUB_TOKEN }}`
   and fail on every bootstrap forever; an unfilled placeholder is the seed
   silently ceasing to be authoritative, which is the defect class this
   step exists for. The `test` job ran a real command and the repo tracks
   at least one test file. `deleteBranchOnMerge` is false, or the
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
