"""Orchestrator Agent — the CEO that decomposes, routes, and arbitrates."""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic

from agents.state import TeamState, WorkPacket
from agents.prompts.system_prompts import ORCHESTRATOR_PROMPT


def _build_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0.2,
        max_tokens=4096,
    )


# ── Planning node ───────────────────────────────────────────────────────────

async def plan_node(state: TeamState) -> dict:
    """Decompose the user request into a prioritised list of WorkPackets."""
    llm = _build_llm()

    planning_msg = (
        f"The user wants the following work done:\n\n"
        f"{state.user_request}\n\n"
        f"Decompose this into WorkPackets (JSON array). Each packet must have:\n"
        f"id, assigned_to (researcher|graphics|frontend|backend|qa), title, "
        f"description, dependencies (list of packet IDs), confidence (0-1).\n\n"
        f"Return ONLY the JSON array, no other text."
    )

    response = await llm.ainvoke([
        SystemMessage(content=ORCHESTRATOR_PROMPT),
        *state.messages,
        SystemMessage(content=planning_msg),
    ])

    # Parse work packets from the response
    content = response.content
    try:
        # Extract JSON array from response
        start = content.index("[")
        end = content.rindex("]") + 1
        packets_raw = json.loads(content[start:end])
        packets = [WorkPacket(**p) for p in packets_raw]
    except (ValueError, json.JSONDecodeError):
        packets = [
            WorkPacket(
                id="wp-001",
                assigned_to="researcher",
                title="Research requirements",
                description=f"Research data sources and requirements for: {state.user_request}",
                confidence=0.5,
            )
        ]

    return {
        "plan": packets,
        "current_phase": "research",
        "messages": [AIMessage(
            content=f"Plan created with {len(packets)} work packets.",
            name="orchestrator",
        )],
    }


# ── Routing node ────────────────────────────────────────────────────────────

def route_next_phase(state: TeamState) -> str:
    """Determine which agent phase to execute next based on the plan."""
    phase_order = ["research", "design", "frontend", "backend", "qa", "delivery"]

    # If QA flagged revisions and we haven't exceeded max
    if state.qa_reports:
        latest_qa = state.qa_reports[-1]
        if latest_qa.revision_required and state.revision_count < state.max_revisions:
            target = latest_qa.revision_target
            if target in phase_order:
                return target

    return state.current_phase


# ── Revision arbitration node ──────────────────────────────────────────────

async def revision_node(state: TeamState) -> dict:
    """Handle QA-triggered revisions: decide what to redo."""
    llm = _build_llm()

    qa_summary = "\n".join(
        f"- Packet {r.target_packet_id}: {'PASS' if r.passed else 'FAIL'} "
        f"Issues: {r.issues}"
        for r in state.qa_reports
    )

    response = await llm.ainvoke([
        SystemMessage(content=ORCHESTRATOR_PROMPT),
        SystemMessage(content=(
            f"QA has completed review. Results:\n{qa_summary}\n\n"
            f"Current revision count: {state.revision_count}/{state.max_revisions}\n"
            f"Decide which phase needs re-execution or if we can proceed to delivery.\n"
            f"Respond with just the phase name: research, design, frontend, backend, or delivery."
        )),
    ])

    phase = response.content.strip().lower()
    valid = {"research", "design", "frontend", "backend", "delivery"}
    if phase not in valid:
        phase = "delivery"

    return {
        "current_phase": phase,
        "revision_count": state.revision_count + 1,
        "messages": [AIMessage(
            content=f"Revision arbitration complete. Next phase: {phase}",
            name="orchestrator",
        )],
    }
