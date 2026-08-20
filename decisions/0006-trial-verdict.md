# 0006 — Trial verdict: sofa-scratch round two

**Status:** accepted (Steve, 2026-08-20) · **Closes:** the acceptance test
fixed in 0001 · **Amends:** 0001's criteria — attaches the counting rules
they lacked; retires none

## Context

0001 fixed four acceptance criteria in advance and branched on the result:
pass → bootstrap wilson; fail → one blueprint revision, not a sub-project.
The trial ran 2026-08-20. Scoring it needed counting rules 0001 never
wrote, so Steve set them before any score was computed, not after:

- **Window:** bootstrap PR #30 opening (03:15Z) to Steve's merge of PR #35
  into `main` and green CI (17:39Z). This is a *PR-authoring* window;
  charter and design work began before #30 was pushed, so it bounds the
  ratio, not the trial. sofa-claude PR #12 merged 03:01Z and is pre-trial.
- **Universe:** PRs authored in the window in *both* repos — sofa-scratch
  #30/#32/#33/#34/#35 and sofa-claude #15. The metric exists to catch the
  factory building itself, so excluding the factory repo would defeat it.
- **Promotion PRs (#33, #35) are excluded from both sides** of the ratio:
  no authored content, one mandated per promotion. **Bootstrap (#30)
  counts as factory.**
- sofa-scratch's round-one PRs are out: legacy process. Standing issues
  (sofa-claude #1/#2, sofa-scratch #29) are out of the issue count — they
  are permanent fixtures that can never close.

**The scoreboard, 1 of 4:**

1. **Product reaches `main` — met.** `redact` v1 on `main` at 17:39Z, CI
   green, the charter's falsifiable end condition (six credential
   families, both fixtures each, corpus-completeness test) satisfied.
   Roughly four hours of build time; the rest was waiting on Steve.
2. **≥60% product PRs — missed, 25%** (1 of 4: #32 product; #30, #34, and
   sofa-claude #15 factory). This is a miss on the merits, not an artifact
   of the rules: under the rules above the achievable ceiling is 100%, and
   **seven of the eight defensible rule sets also fail** — the verdict is
   robust to the choice, which is why the criterion stands (see Decision).
3. **≤5 open issues at close-out — missed, 6** (sofa-claude #4, #5, #7,
   #10, #13, #14; sofa-scratch none). The count reached 6 at 04:39Z, when
   #14 was filed, and stayed there through close-out. Issue #13 was filed
   at 03:08Z — before the window's nominal start, in the wrap-up that also
   produced pre-trial PR #12 — so it is not a post-hoc addition; the trial
   ran over budget on this criterion for thirteen of its fourteen hours.
4. **≤30 minutes of Steve — missed, 30–60 minutes** (his assessment).

## Decision

**The trial fails its own acceptance test**, and the failure is
informative rather than a measurement artifact. 0001's stated consequence
applies: one blueprint revision, not a sub-project.

- **All four criteria stand.** An earlier draft of this record retired
  criterion 2 as arithmetically unpassable; that argument was wrong. It
  depended on counting promotion PRs, which the rules above exclude, and
  the surviving health metric it would have deferred to — this repo's PR
  queue trending to zero — has a documented false negative on the exact
  incident it must catch: legacy merged 60 of 61 PRs, so its queue was
  near zero for all 14 days it produced zero workload output. A queue
  measures merge latency; only criterion 2 measures composition. What 0001
  actually lacked was counting rules, and this record supplies them.
- **The blueprint defect criterion 2 detected is real, and named here.**
  Two of the three factory PRs (#34, sofa-claude #15) were process changes
  *discovered during* the trial and built in flight. sofa-scratch PR #34
  edited that repo's own `CLAUDE.md` — which its "Never" section forbids
  in as many words: "Add process machinery here. Process problems are
  sofa-claude bleeds: note the incident, raise it there, keep building the
  product." The seeded rule was correct and was not followed. **The
  revision is a rulebook change making it structural: process changes
  discovered mid-unit are filed, never built in flight, in either repo.**
  It does not land here — `CLAUDE.md` sits at its 74-line ceiling, so it
  must remove or merge a rule, which is its own unit. It is **Issue #18**,
  labeled `keep`, and it **gates wilson as a merged change, not a filed
  one.**
- **Wilson's gates, all three of which must be closed, not merely
  answered:** Issue #18 (the blueprint revision) merged; Issue #13 (seed
  harvest) merged; Issue #14 decided — and, if the decision is status
  quo, the recurring per-bootstrap Steve steps enumerated in the digest,
  so the cost criterion 4 measures is visible rather than assumed away.
  All gating issues carry `keep`, because `backlog-expiry` closes
  unlabeled issues after 14 days and would otherwise delete wilson's
  preconditions unattended.
- **Criterion 4 gets an observation point, not instrumentation:** it is
  scored once more at wilson's bootstrap, by Steve, by the same method.
- **No round three.** Re-running sofa-scratch to chase a passing
  scoreboard is the sub-project 0001 ruled out. The revision lands, then
  wilson bootstraps under it.

## Consequences

- 0001's acceptance test is closed with all four criteria intact and their
  counting rules now written down, so the next scoring is not re-litigated
  from scratch. 0001 carries a forward pointer to this record.
- sofa-scratch is finished. The repo stays as the trial's record; its
  standing handoff (Issue #29) is its only open item.
- The wilson gate is propagated to Issue #1 (handoff) and Issue #2 (the
  digest) on merge. A rule that lives only in `decisions/` is not a live
  rule by this repo's own rulebook, and `/onboard` reads Issue #1 alone.
- What the trial proved is the part the scoreboard understates: the
  failure that killed the legacy process — product dying on a branch
  behind a human gate that existed only on paper — did not recur, and the
  one criterion legacy could never satisfy was met in a day.
- Honest residuals: criterion 4 rests on Steve's recollection, and the
  process will not instrument his time — that would cost more than the
  criterion is worth. Criterion 2's rules are now fixed but were set after
  the trial ran; they were set before any score was computed, which is
  weaker than setting them in 0001 and is the reason they are recorded
  here rather than re-derived next time.
