---
name: doc-review
description: Adversarial review of design and governance prose — charters, CLAUDE.mds, grants, design records, acceptance criteria. Runs a fixed, visible brief with hard caps so review depth can't become the finding factory that killed the legacy process.
---

# doc-review

For prose that governs behavior: charters, rulebooks, grants, design
records, acceptance criteria. Not for code — that is `/code-review`,
Steve's to type. Both lanes run only on seam artifacts (decisions/0003).

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

## After

Post the findings as a comment on the target PR — no comment, no review
happened — and confirm the comment actually landed before acting on it.
Triage findings by the intake rule; one fix round; no review of the
fixes beyond CI.
