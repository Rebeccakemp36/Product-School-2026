# Orchestration Map: Cortex PM Chief-of-Staff Agent

> Module 3 · Orchestration & Subagents, ★ Deliverable 3
>
> ✅ **What this validates:** nothing advances unchecked, by the end you'll have proven a justified topology, a roster, and a validator with a defined fail action.
>
> Builds on your M2 Loop Spec. Only split one agent into a team when there's a real reason, coordination has a cost.

## 1. Why split? (or why not)

Cortex splits for **one reason only: the independent validator.** Cortex needs an independent grade, because it can't reliably grade its own draft.

| Reason | Splits? | Why |
|---|---|---|
| Separation of concerns | No | The check is the split, not a separate reading and drafting agent |
| Parallelism | No | It's a small agent, so one is fine |
| Independent validator | **Yes** | Cortex needs an independent grade |
| Context-window pressure | No | Runs are small |

**Design today:** a cron (Friday 7am) plus on-request hook fires one agent that pulls project data, drafts the weekly update, queues story proposals, and stops at a human checkpoint, done when the critic passes, and stuck or escalating otherwise.

## 2. Topology

**Pattern:** single + subagents (one main agent, with the critic as a helper).

```
[Friday 7am cron, or on-request ask with a request ID]
        |
        v
[Cortex: pulls data, drafts the update + proposes stories]
        |
        v
[Freshness gate (code): newest activity > 10 days -> escalate]
        |
        v
[Critic (Sonnet, own context)]
   fail -> back to Cortex with reasons (max 2 revisions) -> then escalate
   pass -> [PM review checkpoint] -> held, never auto-sent
```

## 3. Roster

| Agent | Responsibility | Runs which Loop Spec |
|---|---|---|
| Cortex (chief-of-staff) | Pulls project data, drafts the weekly update, proposes stories | M2 loop: cron plus on-request hook, ends at the human checkpoint |
| Critic (validator) | Grades the draft against the five checks; Sonnet, own context | A validation pass inside each run, capped at 2 revisions |

## 4. Communication & hand-offs

| From → to | What passes | In what form |
|---|---|---|
| Trigger → Cortex | The task brief, and a request ID for on-request asks | Text |
| Cortex → critic | The proposed draft, plus the source log (what each tool returned) | Text, in-process |
| Critic → Cortex (on fail) | The verdict and reasons | JSON (`verdict`, `reasons`) |
| Critic → human (on pass or after the cap) | The held draft, the sources list, and the notification | A saved file in `run-output/`, plus a log line |

All hand-offs are plain in-process Python. No MCP or A2A protocol is used.

## 5. The validator

- **What the critic checks:**
  1. The update names the right project and cites real activity.
  2. No invented numbers: every figure, date and Red/Yellow/Green call traces to the pulled data.
  3. Within the team norms: no unconfirmed date, no launch gate marked, no confidential item in a company-wide update.
  4. Nothing posted or committed: stories are only proposed or queued.
  5. Freshness: the newest activity is within 10 days of the run date.
- **Fail action:** revise up to **2** times, with the critic's reasons returned to Cortex each time. If it still fails, escalate to a human. Every rejection is logged.
- **Revision cap:** 2, "a good level of checking before human intervention".
- **Pass action:** the draft advances to the PM review checkpoint. It is never sent automatically.

## 6. State: shared vs isolated

| Shared | Isolated |
|---|---|
| The task brief and the run date | Cortex's transcript and reasoning |
| The source data the tools returned | The critic's own reasoning (Cortex gets only the verdict and reasons) |
| The draft | The request-ID log (only the trigger and orchestration code touch it) |

State is scoped per project, so one project's data never reaches another's critic pass.

## 7. Cost & latency budget

_Coordination has a price. Rough token/latency cost of the fleet vs a single agent. (Forward-link to M5 bounds.)_
