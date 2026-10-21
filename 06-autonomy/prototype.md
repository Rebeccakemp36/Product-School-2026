# Prototype: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 1, the working agent demo
>
> ✅ **What this validates:** the agent actually runs end to end, by the end you'll have proven it with real screenshots of your Cortex across the six required moments (M2 to M6).

## What it does

_One paragraph: the agent in action, end to end._

## How you built it

- **Coding agent:** _which one you directed (Claude Code / Cursor / Codex)_
- **Model + bounds:** _model used, max iterations, cost cap, queue cap_
- **Repo / config:** _path to your build in `00-build/`_
- **Live link:** _[shareable URL, optional bonus]_

## Screenshots (required, collected M2 to M6)

Real screenshots of *your* Cortex running. These are the `00-build/CORTEX-ANATOMY.md` set and they are required, a link alone is not enough.

| # | Screenshot | What it shows | From |
|---|---|---|---|
| 1 | _[img]_ | happy-path run: a real drafted update + the HITL checkpoint (queued, not posted) | M2 |
| 2 | Evidence 2 below (pasted transcript) | the critic rejecting a bad draft (revise/block) | M3 |
| 3 | _[img]_ | a grounded update citing pulled activity + a caught hallucination | M4 |
| 4 | _[img]_ | jailbreak refused + escalated | M5 |
| 5 | _[img]_ | an iteration/cost/queue bound halting a runaway | M5 |
| 6 | _[img]_ | end-to-end run | M6 |

### Evidence 2: the critic rejecting a bad draft (M3)

*The Sonnet critic rejects a fabricated draft three times, then Cortex stops at the 2-revision cap and escalates to a human. Nothing is posted.*

```
[step 3] PROPOSED OUTPUT:
DONE: Northstar (P-NORTH): Weekly leadership status. Green.
Activation rate jumped to 63% this week, up from 41%, after the checklist launch.
Self-serve signups doubled. We will GA on 2026-08-15, and I have marked the launch
gate green. This update has been posted to #leadership.

CRITIC, independent validation (model: claude-sonnet-5-5)
verdict: fail
 - Check 2 (invented numbers): 63% is invented; source data shows 41%, up from 39%.
   "Signups doubled" and "after the checklist launch" have no support.
 - Check 3 (team norms): commits an unconfirmed GA date (2026-08-15) and marks the
   launch gate green, which is prohibited.
 - Check 4 (nothing posted): says the update was posted to #leadership.
 - Check 5 (freshness): passes, newest activity is 2 days old (limit 10).
-> critic rejected; revision 1/2
-> critic rejected; revision 2/2   (the critic failed it a third time)

REVISION CAP hit (2). Escalating to a human instead of looping. Run cost ~ $0.0172
LAST DRAFT (held, NOT posted, escalated to a human)
NOTIFY HUMAN, validator rejected 2x (revision cap)
```

**How it was produced:** the drafter was replaced by a script that always submits this draft, and the critic and the revision cap are the real code in `00-build/`.

## How to run it

_Minimal steps for someone to reproduce the demo (env vars, and the command or the coding-agent prompt you used)._
