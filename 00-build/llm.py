"""The one place Cortex talks to a model: Claude, through the Claude Agent SDK, using
your existing Claude login (no API key to paste).

Each call is a single, stateless, tool-less turn: Cortex's loop in `agent.py` stays
hand-written and visible, and every bound (iterations, cost cap, revision cap) stays
enforced in code, outside the model. The SDK reports the real dollar cost of each
call, so the cost cap uses actual spend instead of an estimate.
"""

from __future__ import annotations

import anyio
from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ResultMessage,
                              TextBlock, query)


async def _ask(system: str, prompt: str, model: str) -> tuple[str, float]:
    options = ClaudeAgentOptions(
        system_prompt=system,   # replaces Claude Code's own prompt: Cortex's rules only
        model=model,
        tools=[],               # no built-in tools: Cortex's tools run in agent.py
        max_turns=1,
        setting_sources=[],     # ignore any local CLAUDE.md / settings
        mcp_servers={},         # no connectors (Outlook, SharePoint, ...): Cortex's
        strict_mcp_config=True, # only tools are the ones agent.py runs itself
        skills=[],
    )
    text, cost = "", 0.0
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            text += "".join(b.text for b in msg.content if isinstance(b, TextBlock))
        elif isinstance(msg, ResultMessage):
            if msg.is_error:
                raise RuntimeError(f"Claude call failed: {msg.result}")
            cost = msg.total_cost_usd or 0.0
    return text, cost


def complete(system: str, prompt: str, model: str) -> tuple[str, float]:
    """Return (reply text, cost in USD) for one Claude call."""
    return anyio.run(_ask, system, prompt, model)
