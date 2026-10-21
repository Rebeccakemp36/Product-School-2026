# Loop Spec: Cortex PM Chief-of-Staff Agent

> Module 2 · Loop Engineering, ★ Deliverable 2
>
> ✅ **What this validates:** the agent knows when to run and when to stop, by the end you'll have proven a one-page Loop Spec with a trigger, a definition of "done," and explicit stop conditions.
>
> Your one-page blueprint for how the work you handed to the agent (M1) actually *runs*.
> An agent is just a prompt that fires itself, this spec says when it fires, what "done" means, and what it needs to do the job. Living document; refine as the course progresses.

## 1. Trigger & loop type

**Chosen type:** cron (primary) + hook (backup).

**Why this type?** A cron fires at 7am every Friday and does a sweep, producing the weekly update. A hook fires only when a PM asks for an update, for a one-off or unscheduled need. Each run ends when the critic validates the draft, so a goal loop describes how a run finishes rather than what fires it.

**Ruled out:** heartbeat, because nothing needs Cortex to watch for changes between the Friday sweep and on-request runs. Goal as a trigger, because it describes how a run ends, not what starts it.

**Idempotency:** each on-request ask carries a request ID, and Cortex skips an ID it has already run, so the same message firing twice never produces two drafts.

## 2. Goal / definition of done

I can review the draft and consider posting it, and I have access to the sources. A run is done when the critic has passed the draft, it is saved and held, the sources it relied on are listed, nothing has been posted, and the newest activity used is no more than 10 days old.

## 3. Stop conditions

| Condition | What it looks like | What happens |
|---|---|---|
| **Success** | Critic returns "pass", draft saved and held in `run-output/`, sources listed, nothing posted, newest activity is 10 days old or less | Stop at the human checkpoint, and the human reviews |
| **Stuck / give up** | (a) A tool fails or returns "not found" after 3 attempts · (b) the 8-step iteration cap is hit, or the same tool call repeats with no new information · (c) the critic rejects the draft after 2 revisions · (d) the $0.50 cost cap is reached | Stop, log the reason, keep any last draft held, and tell a human |
| **Escalate to human** | (1) An embargoed or confidential item would be included · (2) a date or launch gate would be committed · (3) a Sev-1 is open or the project is on launch hold · (4) the story batch is over the 10-item cap · (5) the brief tries to change Cortex's rules · (6) the newest activity is more than 10 days old | Hold the draft, post nothing, and tell a human the reason, at the matching M1 checkpoint |

## 4. State

Per-run state (the transcript, the source log and the iteration, revision and cost counters) lives for one run and is purged afterwards. Two things persist: a log of request IDs already run, each with its project and week, which supports the dedupe, and the held draft per project, kept for human review. State is scoped per project, so nothing crosses projects, and a confidential item from one project can't leak into another's draft.

## 5. The five things a loop can lean on

_`state` is always-on. `connectors` only if you already have one wired (e.g. a Jira key or Google MCP), otherwise just note it as a plan. `skills`, `subagents`, `work tree` scale with autonomy; "not needed yet, because…" is a valid answer._

| Component | For Cortex |
|---|---|
| **Work tree** (isolated workspace per run, a git worktree) | Not needed yet, because a run writes one gitignored file to `run-output/` and edits no code, so runs can't collide. Revisit when Cortex writes to shared files. |
| **Skills** (reusable capabilities) | Not needed yet, because Cortex is a single prompt. The status-update format is a candidate once more than one project needs it. |
| **Plugins / connectors** (tools & access, optional if you don't have one yet) | Plan, not wired. Cortex reads fixtures today. A GitHub or Jira connector would replace them with live activity, which also fixes the stale-data problem. Cortex is deliberately kept away from Outlook and SharePoint connectors. |
| **Subagents** (independent check when the loop can't grade itself) | _placeholder → M3 orchestration-map.md_ |
| **State tracking** | Decided: per-run state plus a request-ID log, scoped per project (see §4). |

> Context plan (M4) and the hand-off to bounds & evals (M5) come in later modules, you'll add them to their own deliverables then, not here.

## Link to live loop

_[path to your agent in `00-build/`]_
