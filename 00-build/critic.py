"""Independent validator (M3). A separate model call that never saw the drafting
context, so it can't inherit the draft's blind spots. Returns a pass/fail verdict.
The revision cap that stops a critic<->drafter loop lives in `agent.py`.
"""

from __future__ import annotations

import json

import llm
from prompts import CRITIC_SYSTEM


def review(model: str, proposed_output: str, source_data: str) -> dict:
    """Return {"verdict": "pass"|"fail", "reasons": [...]} for a proposed output."""
    text, cost = llm.complete(
        CRITIC_SYSTEM + "\nRespond with the JSON object only, no other text.",
        f"SOURCE DATA Cortex used:\n{source_data}\n\n"
        f"CORTEX PROPOSED OUTPUT:\n{proposed_output}",
        model)
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        verdict = json.loads(text)
    except json.JSONDecodeError:
        verdict = {"verdict": "fail", "reasons": ["critic returned unparseable output"]}
    verdict["_cost"] = cost
    return verdict
