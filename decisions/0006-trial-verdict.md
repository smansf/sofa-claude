# 0006 — Trial verdict: sofa-scratch round two

**Status:** accepted (Steve, 2026-08-20) · **Closes:** the acceptance test
fixed in 0001 · **Amends:** 0001's criteria (retires one)

## Context

0001 fixed four acceptance criteria in advance and named the consequence
of each outcome: pass → bootstrap wilson; fail → one blueprint revision,
not a sub-project. The trial ran 2026-08-20. Scoring it needed counting
rules that 0001 never wrote down, so Steve set them before any score was
computed, not after:

- **Window:** bootstrap PR #30 opening (03:15Z) to Steve's merge of PR #35
  into `main` and green CI (17:39Z). sofa-claude PR #12 merged 03:01Z, 14
  minutes early, and is pre-trial.
- **Universe:** PRs authored in the window in *both* repos — sofa-scratch
  #30/#32/#33/#34/#35 and sofa-claude #15. The metric exists to catch the
  factory building itself, so excluding the factory repo would defeat it.
- **Promotion PRs (#33, #35) are excluded from both sides** of the ratio:
  they carry no authored content and the branch model mandates one per
  promotion. **Bootstrap (#30) counts as factory.**
- sofa-scratch's round-one and pre-round-one PRs are out: legacy process.
- Standing issues (sofa-claude #1/#2, sofa-scratch #29) are excluded from
  the issue count — they are permanent fixtures that can never close.

**The scoreboard, 1 of 4:**

1. **Product reaches `main` — met.** `redact` v1 on `main` at 17:39Z, CI
   green, the charter's falsifiable end condition (six credential
   families, both fixtures each, corpus-completeness test) satisfied.
   Roughly four hours of build time; the rest was waiting on Steve.
2. **≥60% product PRs — missed, 25%** (1 of 4: #32 product; #30, #34, and
   sofa-claude #15 factory).
3. **≤5 open issues at close-out — missed by one, 6** (sofa-claude #4, #5,
   #7, #10, #13, #14; sofa-scratch none). At the end-condition instant it
   was exactly 5 — Issue #13 was filed ten minutes later during the same
   session's wrap-up. Scored as a miss anyway: a trial's own harvested
   side-findings are precisely what this criterion exists to count, and
   excluding them would reproduce the legacy blind spot.
4. **≤30 minutes of Steve — missed, 30–60 minutes** (his assessment).

**Criterion 2 was unpassable as written.** Under the `dev` → `staging` →
`main` model 0001 introduced *in the same record*, every unit costs one
authored PR plus up to two promotion PRs, capping the product share at
33% however well the factory behaves. The 60% figure was calibrated on a
61-PR legacy corpus that had no promotion layer. Of eight defensible
counting rules, exactly one yields a pass — at exactly 60%. A criterion
whose verdict is set by an unwritten rule measures the rule, not the
factory.

## Decision

**The trial fails its own acceptance test.** The consequence 0001 named
applies: one blueprint revision, not a sub-project. The revision is three
items the trial already filed — it creates no new machinery, no new file,
and no new rule:

- **Criterion 2 is retired, not replaced.** 0001 already declares the
  health metric — this repo's PR queue trending to zero, filling up as
  the alarm. The percentage was a second, worse spelling of it that the
  branch model defeats arithmetically. One metric, already written,
  already load-bearing; deleting the other is the whole fix.
- **Issue #14 (repo administration) is the gate on criterion 4.** Every
  bootstrap costs a Steve step for the default-branch flip and rulesets;
  this trial added the auto-delete incident and the PAT/checks-layer
  detour on top. Criterion 4 cannot come in under 30 minutes until #14 is
  decided, so #14 blocks wilson.
- **Issue #13 (the six seed defects) lands** — the trial's own harvest,
  and the sixth issue that cost criterion 3.

**No round three.** Re-running sofa-scratch to chase a passing scoreboard
is exactly the sub-project 0001 ruled out. The revision lands, then wilson
bootstraps under it.

## Consequences

- 0001's acceptance test is closed. Three criteria stand as written; the
  fourth is gone, and this repo's PR-queue trend is the sole health metric.
- sofa-scratch is finished. The repo stays as the trial's record; its
  standing handoff (Issue #29) is its only open item, and nothing further
  is owed there.
- Wilson's bootstrap unblocks when #14 is decided and #13 lands — both
  already open, neither newly created here.
- What the trial actually proved is the part the scoreboard understates:
  the failure that killed the legacy process — product dying on a branch
  behind a human gate that existed only on paper — did not recur. The one
  criterion legacy could never satisfy at all was met in a day.
- Honest residual: criterion 4 was scored from Steve's recollection, not
  instrumentation. The process does not measure his time and will not
  start — instrumenting it would cost more than the criterion is worth.
