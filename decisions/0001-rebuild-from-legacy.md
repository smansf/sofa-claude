# 0001 — Rebuild from legacy

**Status:** accepted (Steve, 2026-08-18) · **Supersedes:** the entire
`sofa-claude-legacy` process corpus

## Context

The first sofa-claude ran 14 days (2026-08-05 → 08-18) and did not converge.
The evidence, from four independent sweeps of its history:

- 83 issues + 61 PRs; **0 items of workload output** (97% factory machinery).
- **49% of issues were self-reported side-findings** of other work; the open
  backlog grew every week (11 → 25 → 35), never shrank.
- Discipline was real (test:code ratio 1.13:1, severity triage held, 60/61
  PRs merged) — but each completed unit spawned >1 new issue and nothing at
  intake could say "not worth recording." The one-fix-round rule, followed
  faithfully, *manufactured* backlog by converting rework into filed issues.
- No proportionality: a hand-edit-only edge case in a throwaway todo CLI got
  a charter, a milestone, two 3-lens Opus panels, and a +425-line PR.
- The dogfood trial (sofa-scratch) was fast — working CLI + 80 tests in 31
  hours — then the tail turned self-referential and nobody returned for the
  product. Zero promotions to main ever happened; the product died on a
  deleted branch. The human gate existed on paper only.
- Enforcement failed silently: two hooks never once executed on the
  production machine (fail-open, wrong token variable); local main drifted
  78 commits unnoticed. CLAUDE.md was the hottest file (19 of 61 PRs).
- ~34% of machinery lines were workarounds for a MacBook sandbox that the
  mini-only future doesn't have.

## Decision

Rebuild from scratch as a **public** repo (native branch protection,
unlimited CI), mini-only, on seven principles: workload-first; native-first;
enforcement fails loudly (CI and platform config, never fail-open local
machinery); proportionality by product stakes; closure declared before work
starts; an intake kill step with auto-expiring low-severity issues; a hard
rulebook budget. Structure: seed kit + governance + three skills + digest,
and nothing else ("What bled" gate on every PR here).

Branch models — process repo: `claude/*` → PR → Steve merges `main`.
Workload repos: `dev` (Claude merges on green CI + reviewer pass) →
`staging` (Steve promotes; human-facing preview) → `main` (Steve promotes;
production). Vercel branch wiring, touchable only by Steve's account, is the
deterministic deploy gate. A separate GitHub machine account (deferred) later
turns the honor-system merge gates into enforced rulesets.

Carried from legacy: PR templates, checks-that-import pattern, onboard/
wrap-up/handoff conventions, the pr-visibility idea, spec templates, the
redesign doc's ideas as distilled here. Dropped: all MacBook machinery, the
discipline-marker hook family (verified utterances, not outcomes; 9 defect
issues in 4 fix generations), the 137 KB living process doc.

## Consequences

- The rebuild has an acceptance test with criteria fixed in advance:
  **sofa-scratch round two** — product reaches `main`; ≥60% of PRs are
  product PRs; ≤5 open issues at close-out; ≤30 minutes of Steve's time.
  Pass → bootstrap wilson. Fail → one blueprint revision, not a sub-project.
  **Scored in 0006 (2026-08-20): failed, 1 of 4.** That record supplies the
  counting rules these criteria lacked and names wilson's gates; read it
  before applying any criterion above.
- This repo's PR queue trending to zero is the health metric; it filling up
  is the alarm.
- Full review document (postmortem + blueprint + rules ledger) is preserved
  as the artifact "The Sofa-Claude Rebuild" (2026-08-18); this record is its
  one-page distillation.
