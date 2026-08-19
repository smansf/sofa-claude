---
name: bootstrap
description: Bootstrap a workload repo from the seed kit — elicit a one-page charter with a stakes tier and end condition, copy and adapt seed/, wire branches and standing issues.
---

# bootstrap

Run this *from the workload repo's own directory*, never from sofa-claude.

1. **Charter first** (`docs/charter.md`, one page, elicited from Steve):
   what is being built and why; who uses it; the **stakes tier**
   (throwaway / standard / production) that sets review depth everywhere;
   the coverage floor; and the project's **end condition** — what done looks
   like, written before work starts.
2. **Copy the seed**: `seed/CLAUDE.md.template` → `CLAUDE.md`,
   `seed/workflows/ci.yml` → `.github/workflows/ci.yml`,
   `seed/workflows/backlog-expiry.yml` → `.github/workflows/backlog-expiry.yml`,
   `seed/pull_request_template.md` → `.github/pull_request_template.md`.
   Fill every `{{PLACEHOLDER}}` from the charter and the project's actual
   stack. The copy is a divorce: this repo owes sofa-claude nothing after.
3. **Wire the repo**: create `dev` and `staging` from `main`; create labels
   `urgent`, `keep`, and `standing`; create the standing handoff issue and
   note its number in CLAUDE.md. Vercel wiring (which branch deploys where)
   is Steve's step — list it for him in the needs-Steve digest, don't wait.
4. **Propose the first unit**: one issue, frozen acceptance criteria, sized
   to reach `dev` within a session. Product code, not process — if the
   process pinches during the unit, that's a sofa-claude bleed to note,
   not machinery to build here.

Total bootstrap budget: one session, one PR into the workload's `dev`
(charter + seed files). If it wants to grow beyond that, stop — that is a
bleed to raise in sofa-claude, not a bigger bootstrap.
