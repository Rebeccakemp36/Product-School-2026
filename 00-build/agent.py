"""Cortex, a minimal, explicit agent loop you (and your coding agent) can read end
to end. This is the agent you ship: your PM chief-of-staff. You build it by
directing your coding agent (Claude Code / Cursor / Codex) to shape this file. You
never have to hand-write it.

Every bound the course talks about is visible right here in code, not buried in a
framework: the max-iteration counter, the cost cap, the revision cap, the
stop/escalate conditions, the auto-queue cap, and the absence of any publish tool.

Usage (ask your coding agent to run these for you, or run them yourself):
    python agent.py                # runs the happy-path task (weekly status update)
    python agent.py happy --request-id R1   # on-request run; a repeated ID is skipped
    python agent.py missing-data   # the stuck/escalate case
    python agent.py jailbreak       # the prompt-injection refusal case

Every run ends by showing the drafted status update in a FINAL STATUS UPDATE block
(or LAST DRAFT, held, if a bound trips), and saves it to run-output/. That file is
always a draft held for a human, it is never posted, there is no publish tool.

Talks to Claude through the Claude Agent SDK using your Claude login, so there is no
API key to set (see llm.py). Model and bounds are read from env so you can tune them, that tuning is your M5 deliverable.

The loop is deliberately transparent (hand-written tool-calling: Claude
replies with a JSON tool request or a final answer) so a grader can see the machinery. Keep the bounds explicit if you rework it.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import llm
import tools
from critic import review
from prompts import CORTEX_SYSTEM

try:  # load .env if python-dotenv is installed; harmless if it isn't
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# --- Bounds (your M5 deliverable: tune these and justify them) ----------------
MODEL = os.environ.get("CORTEX_MODEL", "claude-haiku-5-5")
MAX_ITERATIONS = int(os.environ.get("CORTEX_MAX_ITERATIONS", "8"))
MAX_REVISIONS = int(os.environ.get("CORTEX_MAX_REVISIONS", "2"))
COST_CAP_USD = float(os.environ.get("CORTEX_COST_CAP_USD", "0.50"))
MAX_QUEUE_ITEMS = int(os.environ.get("CORTEX_MAX_QUEUE_ITEMS", "10"))
# Loop Spec (M2): the newest activity Cortex uses may be at most this many days old.
FRESHNESS_DAYS = int(os.environ.get("CORTEX_FRESHNESS_DAYS", "10"))
# "Today" for the freshness check. Blank = the real date. Set it only for demos, so
# the dated fixtures count as fresh.
AS_OF = date.fromisoformat(os.environ["CORTEX_AS_OF"]) if os.environ.get("CORTEX_AS_OF") else date.today()
MAX_TOOL_ERRORS = 3   # stuck (a): a tool fails this many times
MAX_REPEATS = 3       # stuck (b): the identical call is made this many times

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_project", "description": "Look up a project by its ID (status, flags, linked PRD).",
        "parameters": {"type": "object", "properties": {
            "project_id": {"type": "string"}}, "required": ["project_id"]}}},
    {"type": "function", "function": {
        "name": "get_activity",
        "description": "Pull recent engineering activity for a project (merged PRs, open issues, Sev-1s).",
        "parameters": {"type": "object", "properties": {
            "project_id": {"type": "string"}}, "required": ["project_id"]}}},
    {"type": "function", "function": {
        "name": "search_past_updates",
        "description": "Search previous status updates and decisions for tone and precedent.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_roadmap",
        "description": "Return the roadmap. Some items are flagged confidential/embargoed.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_norms", "description": "Return the team norms / PM playbook the agent must follow.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "propose_stories",
        "description": "Queue a set of backlog stories for human approval (creates nothing; rejected above the item cap).",
        "parameters": {"type": "object", "properties": {
            "project_id": {"type": "string"},
            "stories": {"type": "array", "items": {"type": "string"}},
            "reason": {"type": "string"}}, "required": ["project_id", "stories"]}}},
]


TOOL_PROTOCOL = """

How to use tools. You have these tools (JSON-schema parameters):
""" + "\n".join(
    f"- {t['function']['name']}: {t['function']['description']} "
    f"params={json.dumps(t['function']['parameters']['properties'])}"
    for t in TOOL_SCHEMAS) + """

To call a tool, reply with ONLY one JSON object and nothing else, for example:
{"tool": "get_project", "args": {"project_id": "P-1"}}
You will get the result back and can call another tool. Call one tool per reply.
When you are finished, reply with your DONE: or ESCALATE: answer as plain text, never JSON.
"""


def parse_tool_call(reply: str):
    """Return (tool_name, args) if the reply is a tool request, else None."""
    text = reply.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    if not text.startswith("{"):
        return None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(obj, dict) and "tool" in obj:
        return obj["tool"], obj.get("args") or {}
    return None


class Bounds:
    """Tracks spend and trips the cost cap. This is enforced OUTSIDE the model."""

    def __init__(self):
        self.cost = 0.0

    def add(self, cost_usd: float) -> None:
        self.cost += cost_usd  # real cost reported by the SDK for each call

    def over_cap(self) -> bool:
        return self.cost >= COST_CAP_USD


OUTPUT_DIR = Path(__file__).parent / "run-output"


def newest_activity_date(result: dict):
    """Newest date in a get_activity result, or None if there is none."""
    dates = []
    for item in result.get("activity", []):
        try:
            dates.append(date.fromisoformat(item["date"]))
        except (KeyError, ValueError):
            pass
    return max(dates) if dates else None


def notify_human(which: str, reason: str) -> None:
    """Loop Spec: stuck and escalate both TELL a human. For now that is a visible
    notice plus a line in run-output/notifications.log; a real channel needs a connector."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    line = f"{datetime.now():%Y-%m-%d %H:%M} task-{which}: {reason}"
    with (OUTPUT_DIR / "notifications.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    banner(f"NOTIFY HUMAN, {reason}")


def already_ran(request_id: str) -> bool:
    """Dedupe by request ID: record the ID, and say whether we have run it before."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / "request-ids.json"
    seen = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if request_id in seen:
        return True
    seen[request_id] = datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(seen, indent=2), encoding="utf-8")
    return False


def banner(text: str) -> None:
    print(f"\n{'=' * 64}\n{text}\n{'=' * 64}")


def emit_deliverable(which: str, draft: str, *, accepted: bool,
                     reason: str, cost: float) -> None:
    """Surface AND persist Cortex's drafted status update so it can't get lost in
    the scroll-back. This is still a DRAFT held for human review, never a post,
    there is no publish tool, and an escalated run is held on purpose.

    Runs on every exit: an accepted pass prints the FINAL update; a bound trip or
    escalation prints the LAST draft it managed to write plus why it was held.
    """
    banner("FINAL STATUS UPDATE (draft, validator-approved, NOT posted)" if accepted
           else "LAST DRAFT (held, NOT posted, escalated to a human)")
    if draft.strip():
        print(draft.rstrip())
    else:
        print("(Cortex stopped before it produced a draft, nothing to show.)")
    if not accepted:
        print(f"\nWhy it was held: {reason}")
        notify_human(which, reason)

    if draft.strip():
        OUTPUT_DIR.mkdir(exist_ok=True)
        out = OUTPUT_DIR / f"status-update-{which}.md"
        state = "accepted by validator" if accepted else "HELD, escalated"
        out.write_text(
            f"<!-- Cortex draft, {state}; NOT posted. Run cost ~ ${cost:.4f}. -->\n"
            f"<!-- {reason} -->\n\n{draft.rstrip()}\n", encoding="utf-8")
        print(f"\nSaved draft -> {out.relative_to(Path(__file__).parent)}  "
              f"(for your review, nothing was posted)")


def run(which: str = "happy", request_id: str | None = None) -> None:
    if request_id and already_ran(request_id):
        print(f"Request {request_id} was already run, skipping (dedupe by request ID).")
        return
    bounds = Bounds()
    task = tools.get_task(which)
    if "error" in task:
        print(task)
        return

    banner(f"CORTEX RUN, fixture: task-{which}  (auto-queue cap {MAX_QUEUE_ITEMS} items)")
    print(task["body"])

    system = CORTEX_SYSTEM + TOOL_PROTOCOL
    transcript = [f"Today's date for this run: {AS_OF.isoformat()}\n\n"
                  f"PM task brief:\n\n{task['body']}"]
    source_log: list[str] = [task["body"]]
    fresh_checked = False
    errors: Counter = Counter()
    calls: Counter = Counter()
    revisions = 0
    last_draft = ""

    for step in range(1, MAX_ITERATIONS + 1):
        if bounds.over_cap():
            reason = f"cost cap ${COST_CAP_USD} hit at ${bounds.cost:.4f}"
            banner(f"BOUND TRIPPED, {reason}. Halting and escalating to a human.")
            emit_deliverable(which, last_draft, accepted=False,
                             reason=reason, cost=bounds.cost)
            return

        reply, cost = llm.complete(system, "\n\n".join(transcript), MODEL)
        bounds.add(cost)

        call = parse_tool_call(reply)
        if call:
            fn, args = call
            calls[(fn, json.dumps(args, sort_keys=True))] += 1
            if fn not in tools.TOOLS:
                result = {"error": f"unknown tool {fn}"}
            elif fn == "propose_stories" and not fresh_checked:
                result = {"error": "blocked: pull get_activity and pass the freshness check before proposing stories"}
            else:
                try:
                    result = tools.TOOLS[fn](**args)
                except TypeError as e:
                    result = {"error": f"bad arguments: {e}"}
            source_log.append(f"{fn}({args}) -> {json.dumps(result)}")
            print(f"\n[step {step}] TOOL {fn}({args})")
            print(f"          -> {json.dumps(result)[:300]}")
            transcript.append(f"ASSISTANT (tool request):\n{reply.strip()}")
            transcript.append(f"TOOL RESULT {fn}:\n{json.dumps(result)}")

            if "error" in result:
                errors[fn] += 1
            if errors[fn] >= MAX_TOOL_ERRORS:
                reason = f"stuck: {fn} failed {errors[fn]}x"
                banner(f"STUCK, {reason}. Stopping.")
                emit_deliverable(which, last_draft, accepted=False, reason=reason, cost=bounds.cost)
                return
            if max(calls.values()) >= MAX_REPEATS:
                reason = "stuck: the same tool call repeated with no new information"
                banner(f"STUCK, {reason}. Stopping.")
                emit_deliverable(which, last_draft, accepted=False, reason=reason, cost=bounds.cost)
                return

            if fn == "get_activity" and "error" not in result:
                newest = newest_activity_date(result)
                age = (AS_OF - newest).days if newest else None
                if age is None or age > FRESHNESS_DAYS:
                    shown = f"{age} days old" if age is not None else "undated"
                    reason = (f"escalate: newest activity is {shown} "
                              f"(limit {FRESHNESS_DAYS} days, as of {AS_OF})")
                    banner(f"FRESHNESS CHECK FAILED, {reason}. Escalating before anything is queued.")
                    emit_deliverable(which, last_draft, accepted=False, reason=reason, cost=bounds.cost)
                    return
                fresh_checked = True
                print(f"          freshness OK: newest activity {age} days old (limit {FRESHNESS_DAYS})")
            continue

        # No tool calls => Cortex produced a proposed output. Validate it.
        proposed = reply
        last_draft = proposed
        print(f"\n[step {step}] PROPOSED OUTPUT:\n{proposed}")

        banner("CRITIC, independent validation")
        verdict = review(MODEL, proposed, "\n".join(source_log))
        # Estimate critic spend too.
        bounds.add(verdict["_cost"])
        print(json.dumps({k: v for k, v in verdict.items() if k != "_cost"}, indent=2))

        if (verdict["verdict"] == "pass" and "ESCALATE:" not in proposed
                and "sources" not in proposed.lower()):
            verdict = {"verdict": "fail", "reasons": [
                "Loop Spec: a done draft must list the sources it relied on."]}
            print("-> no sources list in the draft; treated as not done")

        if verdict["verdict"] == "pass":
            if "ESCALATE:" in proposed:
                notify_human(which, "Cortex escalated: " + proposed.split("ESCALATE:", 1)[1].strip()[:200])
            banner(f"HITL CHECKPOINT, status update + any proposed stories queued for "
                   f"your review. Nothing posted, no commitments made. "
                   f"Run cost ≈ ${bounds.cost:.4f}")
            emit_deliverable(which, proposed, accepted=True,
                             reason="validator passed", cost=bounds.cost)
            return

        if revisions >= MAX_REVISIONS:
            reason = f"validator rejected {MAX_REVISIONS}x (revision cap)"
            banner(f"REVISION CAP hit ({MAX_REVISIONS}). Escalating to a human "
                   f"instead of looping. Run cost ≈ ${bounds.cost:.4f}")
            emit_deliverable(which, last_draft, accepted=False,
                             reason=reason, cost=bounds.cost)
            return

        revisions += 1
        print(f"\n-> critic rejected; revision {revisions}/{MAX_REVISIONS}")
        transcript.append(f"ASSISTANT:\n{proposed}")
        transcript.append("A validator rejected that for these reasons: "
                          f"{verdict['reasons']}. Fix it or escalate.")

    banner(f"MAX ITERATIONS ({MAX_ITERATIONS}) reached without finishing. "
           f"Escalating. Run cost ≈ ${bounds.cost:.4f}")
    emit_deliverable(which, last_draft, accepted=False,
                     reason=f"max iterations ({MAX_ITERATIONS}) reached",
                     cost=bounds.cost)


if __name__ == "__main__":
    args = sys.argv[1:]
    rid = None
    if "--request-id" in args:
        i = args.index("--request-id")
        rid = args[i + 1]
        del args[i:i + 2]
    run(args[0] if args else "happy", rid)
