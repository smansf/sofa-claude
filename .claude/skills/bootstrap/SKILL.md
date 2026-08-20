---
name: bootstrap
description: Bootstrap a workload repo from the seed kit — elicit a charter with stakes tier and falsifiable end condition, add a stakes-scaled design record, copy and adapt seed/, wire branches, labels, and standing issues.
---

# bootstrap

Run this *from the workload repo's own directory*, never from sofa-claude.

1. **Charter first** (`docs/charter.md`, one page, elicited from Steve):
   what is being built and why; who uses it; the **stakes tier**
   (throwaway / standard / production) that sets review depth everywhere;
   the coverage floor; and the project's **end condition** — what done
   looks like, written before work starts and *falsifiable*: if you can't
   say how you'd test that it's met, rewrite it until you can.
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
   `REQUIRED_CHECKS` with the workload ci.yml's job names).
   Fill every `{{PLACEHOLDER}}` from the charter and design record. The
   copy is a divorce: this repo owes sofa-claude nothing after.
4. **Wire the repo**: create `dev` and `staging` from `main`; **set `dev`
   as the default branch, then verify it stuck** (`gh repo view --json
   defaultBranchRef` must say `dev` — if it doesn't, stop wiring and put
   it in the needs-Steve digest, because unit auto-close and the expiry
   record both silently lie until it's fixed). Unit issues then auto-close
   when their PR merges to `dev`, and new PRs target `dev` by default.
   Create labels `urgent`, `keep`,
   `standing`; create the standing handoff issue **labeled `standing`**
   (unlabeled, the repo's own expiry workflow will close it) and note its
   number in CLAUDE.md. Vercel wiring is Steve's step — list it in the needs-Steve
   digest, don't wait.
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
   (`config.yml` with `blank_issues_enabled: false`), and
   `scripts/merge_dev.py` (its `REQUIRED_CHECKS` matching ci.yml's job
   names) are all present; the standing handoff issue exists, carries
   `standing`, and CLAUDE.md names its number. A failed check that one
   `gh` command repairs is re-run once, re-verified, and noted in the
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
