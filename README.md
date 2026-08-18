# sofa-claude

A Claude-native development process: the minimum machinery for Claude Code to
build real software on real repos with almost nothing crossing a human desk.

This repo is four things and refuses to be a fifth:

1. **A seed kit** (`seed/`) — CLAUDE.md skeleton, CI workflow, PR template
   that a new workload repo copies once at bootstrap. Copied, not depended
   on: workload repos owe this repo nothing afterward.
2. **The governance record** (`governance/`, `decisions/`) — the grants Steve
   has signed and one-page records of decisions and their reasons.
3. **Three skills** (`.claude/skills/`) — `onboard`, `wrap-up`, `bootstrap`.
   The set is closed; additions require demonstrated need in real work.
4. **The "needs Steve" digest** (Issue #2) — the one place that answers
   "what is blocked on a human right now."

It is the second attempt. The first ([sofa-claude-legacy]) produced 144
issues and PRs in 14 days, of which zero were workload output; it was
disciplined, well-tested machinery aimed entirely at itself. The full
postmortem and the design that answers it:
[decisions/0001](decisions/0001-rebuild-from-legacy.md).

The core defense against repeating that: **every PR here must name the
incident in real work that motivated it** ("What bled"), enforced by CI.
A process improvement that can't cite its bleed doesn't merge.

[sofa-claude-legacy]: https://github.com/smansf/sofa-claude-legacy
