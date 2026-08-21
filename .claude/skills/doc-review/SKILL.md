---
name: doc-review
description: Adversarial review of design and governance prose — charters, CLAUDE.mds, grants, design records, acceptance criteria. Runs a fixed, visible brief with hard caps so review depth can't become the finding factory that killed the legacy process.
---

# doc-review

For prose that governs behavior: charters, rulebooks, grants, design
records. Not for code — that is `/code-review`, Steve's to type. Where
this skill runs: every PR to sofa-claude (there both lanes run — the
seam rule, recorded in that repo's decisions/0003), and workload design
prose — the charter and design record, at bootstrap and on any later
amendment. Unit-level acceptance criteria get no adversarial pass: that
is proportionality, not an omission.

## Before running

Make the brief visible: attended, paste the filled brief in chat so Steve
can amend it; unattended, commit it in the PR before the reviewer starts.
The reviewer must be fresh-context — a subagent that has not worked on
the artifact — and must not read any other review's findings first.

## The brief (fill the [brackets]; change anything else only via a PR)

> Target: [files or diff]. Context: [one paragraph — what this artifact
> governs, and what its predecessor got wrong]. Stance: adversarial —
> try to break the design, not improve its prose. Attack, in order:
> (1) loopholes — ways a letter-compliant actor still causes the harm
> the rules exist to prevent; (2) false enforcement claims — promises
> the machinery doesn't deliver; (3) contradictions between files;
> (4) failure modes of unattended operation. Forbidden: style or wording
> notes, hypothetical edge cases with no plausible path, anything
> without a concrete harm scenario. Output: at most 8 findings, ranked
> most severe first, each with file/rule, the failure scenario, and a
> grade (urgent-grade / keep-grade). Fewer is fine — padding is itself a
> failure. One round; no recommendations for further review passes.

For a design record, Context must quote the charter's review-depth
conclusion and end condition and list the record's own claimed risks —
a bland Context is a defective review, not a compliant one. Also attack
non-load-bearing content directly, under (1): a section that restates
the charter, pads architecture rationale, or hedges every risk without
a decision attached is the loophole a no-page-cap rule depends on
closing, and it has no other named attacker.

## After

Post the findings as a comment on the target PR — no comment, no review
happened — and confirm the comment actually landed before acting on it.
Triage findings by the intake rule; one fix round; no review of the
fixes beyond CI, and a second review round only if an urgent-grade
finding survives the fix round.
