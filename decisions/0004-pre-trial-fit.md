# 0004 — Pre-build design, the doc-review skill, and the operator toolbox

**Status:** accepted (Steve, 2026-08-19) · **Amends:** the bootstrap
procedure, 0002 (review lines), and the PR conventions

## Context

Steve inspected the factory before the sofa-scratch trial and found five
gaps. (1) Bootstrap jumped from charter to first unit with stack,
architecture, and data decisions made nowhere — harmless for a throwaway,
a hole for wilson. (2) The adversarial review existed only as chat
precedent, re-authored ad hoc each run. (3) Factory skills are repo-scoped,
so in the workload directories they must run from, they don't exist — the
design couldn't run its own trial. (4) "What bled" was jargon,
uncommunicative to any reader outside this conversation. (5) Unit issues
would never auto-close: closing keywords fire only on the default branch,
which wasn't `dev`.

## Decision

- **Pre-build design scales with the charter's stakes tier.** Throwaway:
  charter only. Standard/production: a one-page design record (stack and
  why, architecture sketch, data shape, structural risks) reviewed via
  doc-review; production adds Steve's explicit approval before unit 1.
  Decisions, not documents. Charters must state a falsifiable end
  condition. No milestone layer yet — wilson's bootstrap decides whether
  one is needed.
- **doc-review joins the closed skill set:** the canonical brief in one
  inspectable file, visible before every run; fresh-context reviewer,
  blind to other reviews; at most 8 findings, each with a harm scenario;
  one round; findings posted to the PR or the review didn't happen.
- **Snapshot vs. toolbox.** Workload repos are point-in-time snapshots
  that never reference sofa-claude. Skills are the operator's toolbox —
  live, account-level (`~/.claude/skills/`), installed as copies from
  merged `main` only, because a symlink would let unreviewed branch text
  govern live behavior. A skill may never *require* a repo convention a
  bootstrapped repo lacks; a change that would is a re-bootstrap-grade
  event, not a silent upgrade.
- **PR conventions:** sections are *Why this change* / *What changed* /
  *Verification* — self-explanatory to a cold reader, with the bleed
  discipline living in the instruction text and the same CI gate. Issues
  are linked with closing keywords, and workload repos set `dev` as the
  default branch so units auto-close at the moment the process calls them
  done.
- **Adopt stays parked** until a real adoption target exists; the legacy
  implementation remains in sofa-claude-legacy as reference.

## Consequences

Bootstrap can run its own trial once the post-merge install lands —
onboard's freshness check then keeps the toolbox current every session.
Wilson gets a designed foundation without re-importing ceremony into
throwaway work; PR bodies read plainly to future miners; unit hygiene is
automatic. doc-review's first invocation was this PR itself; its review
drove this record's own amendments (see the PR's findings comment).

Accepted residual risks, revisited only if they bleed: at standard
stakes the design-record review is self-administered (author fills the
brief; the brief-content rule and the production-stakes PR-review
artifact bound but don't eliminate steering); and sessions working
inside sofa-claude itself load the checkout's repo-scoped skills — that
is the development loop, while the account copies govern everywhere
else.
