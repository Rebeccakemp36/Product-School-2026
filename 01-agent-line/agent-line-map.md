# Agent Line Map: Cortex PM Chief-of-Staff Agent

> Module 1 · The Agent Line
>
> ✅ **What this validates:** every risky action has a clear owner, by the end you'll have proven an above/below-the-line map with HITL checkpoints, scored on reversibility, blast radius, and measurability.

## The workflow, decision by decision

List every discrete decision or action in your agent's workflow, then score each one and place it **above** the line (a human owns it) or **below** (the agent owns it). Borderline calls get an HITL checkpoint.

| Decision / action | Reversibility (H/M/L) | Blast radius (H/M/L) | Measurability (H/M/L) | Above / Below | HITL? |
|---|---|---|---|---|---|
| Pull project state and activity | H | L | H | Below | No |
| Decide relevant context | H | L | L | Below | Yes, human approves |
| Draft the update | H | L | M | Below | Yes, human reviews |
| Decide tone and commitment level | H | L | H | Below | No (human sets the tone once) |
| Flag at-risk items and escalations | H | L | M | Below | Yes, human approves |
| Choose what to escalate | H | L | L | Below | Yes, human approves |
| Propose a story batch (capped) | H | L | M | Below | Yes, human curates |
| Post an update, or approve a company-wide one | L | H | H | Above | n/a, human owns it |

## Why each decision sits where it does

1. **Pull project state and activity** sits below the line because it's easy to reverse, has a small blast radius, and is easy to verify. Deciding factor: reversibility, since it's read-only.
2. **Decide relevant context** sits below the line, with a human approving, because it's easy to reverse and has a small blast radius, but it's hard to verify, since a missed item doesn't show up. Deciding factor: measurability.
3. **Draft the update** sits below the line, with a human approving, because it's easy to reverse and has a small blast radius, but it's only moderately easy to verify and needs checking before it goes on. Deciding factor: measurability.
4. **Decide tone and commitment level** sits below the line because it's easy to reverse, has a small blast radius, and is easy to test and correct. Deciding factor: measurability. The human sets the tone once.
5. **Flag at-risk items and escalations** sits below the line, with a human approving, because it's easy to reverse and has a small blast radius, but it needs human verification. Deciding factor: measurability.
6. **Choose what to escalate** sits below the line, with a human approving, because it's easy to reverse and has a small blast radius, but it's hard to verify, since a missed escalation is invisible. Deciding factor: measurability.
7. **Propose a story batch (capped)** sits below the line, with a human curating, because it's easy to reverse and has a small blast radius, but it needs human verification. Deciding factor: measurability.
8. **Post an update, or approve a company-wide one** sits above the line because it's hard to reverse and has a large blast radius, though it's easy to verify. Deciding factor: reversibility.

## Agent anatomy (sketch)

- **Model:** Haiku (`claude-haiku-5-5`) by default. The critic always runs on a stronger model, because verification is the weak spot. The drafter escalates to a stronger model only when the critic fails a draft once.
- **Tools:** five read-only lookups (project, activity, past updates, roadmap, team norms) · one capped, queue-only write (`propose_stories`, human approves)
- **Memory:** the roadmap, decision log, past updates and team norms persist as read-only reference. The task brief, tool results and transcript are purged after each run. Only the held draft is kept for human review.
- **Loop:** _placeholder, defined in M2 loop-spec.md_
- **Bounds:** _placeholder, defined in M5 bounds-and-evals.md_
- **Evals:** _placeholder, defined in M5 bounds-and-evals.md_

## The golden rule, applied

_One sentence per above-the-line decision: why it stays human (which of reversibility / blast radius / measurability failed)._

## Hardest call

**Action 6, choose what to escalate.** I first put it above the line, then moved it below with a human approving. The deciding axis was measurability, which I scored Low, because a missed escalation leaves no visible trace. I agreed it was better to get the work done first, and then review.
