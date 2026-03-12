"""Main LangGraph graph — wires all agents into a supervised workflow.

Entrypoint for LangSmith deployment via langgraph.json.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph

from agents.state import TeamState
from agents.orchestrator import plan_node, route_next_phase, revision_node
from agents.researcher import research_node
from agents.graphics import graphics_node
from agents.frontend import frontend_node
from agents.backend import backend_node
from agents.qa import qa_node


# ── Delivery node ──────────────────────────────────────────────────────────

async def delivery_node(state: TeamState) -> dict:
    """Compile all artifacts into the final deliverable summary."""

    # Simple requests already have final_output set by the orchestrator
    if state.request_type == "simple" and state.final_output:
        return {
            "current_phase": "delivery",
            "messages": [AIMessage(
                content=state.final_output,
                name="orchestrator",
            )],
        }

    sections = []

    # Research summary
    if state.research_artifacts:
        sections.append("## Research Findings")
        for a in state.research_artifacts:
            sections.append(f"### {a.topic}")
            sections.append(a.summary)
            if a.api_endpoints:
                sections.append("**API Endpoints:**")
                sections.extend(f"- `{ep}`" for ep in a.api_endpoints)
            sections.append("")

    # Design system
    if state.design_artifacts:
        sections.append("## Design System")
        for a in state.design_artifacts:
            sections.append(f"### {a.name} ({a.asset_type})")
            sections.append(f"```\n{a.content[:2000]}\n```")
            if a.accessibility_notes:
                sections.append(f"*Accessibility:* {a.accessibility_notes}")
            sections.append("")

    # Frontend components
    if state.frontend_artifacts:
        sections.append("## Frontend Components")
        for a in state.frontend_artifacts:
            sections.append(f"### {a.component_name}")
            sections.append(f"**File:** `{a.file_path}` | **Framework:** {a.framework}")
            sections.append(f"```tsx\n{a.code[:3000]}\n```")
            sections.append("")

    # Backend
    if state.backend_artifacts:
        sections.append("## Backend Services")
        for a in state.backend_artifacts:
            sections.append(f"### {a.endpoint_or_model}")
            sections.append(f"**File:** `{a.file_path}` | **Language:** {a.language}")
            sections.append(f"```python\n{a.code[:3000]}\n```")
            sections.append("")

    # QA report
    if state.qa_reports:
        sections.append("## QA Report")
        for r in state.qa_reports:
            status = "PASSED" if r.passed else "NEEDS REVISION"
            sections.append(f"- **{r.target_packet_id}**: {status}")
            if r.issues:
                for issue in r.issues:
                    sections.append(f"  - {issue[:200]}")
        sections.append("")

    final = "\n".join(sections) or "No artifacts were produced."

    return {
        "final_output": final,
        "current_phase": "delivery",
        "messages": [AIMessage(
            content=f"Deliverable compiled.\n\n{final[:2000]}",
            name="orchestrator",
        )],
    }


# ── Intake node ────────────────────────────────────────────────────────────

async def intake_node(state: TeamState) -> dict:
    """Extract the user request from the last human message."""
    user_request = ""
    for msg in reversed(state.messages):
        if isinstance(msg, HumanMessage):
            user_request = msg.content
            break

    return {
        "user_request": user_request,
        "current_phase": "planning",
    }


# ── Conditional edges ─────────────────────────────────────────────────────

def _after_planning(state: TeamState) -> str:
    """Route after planning: skip the full pipeline for simple requests."""
    if state.request_type == "simple":
        return "delivery"
    return "research"


def _after_qa(state: TeamState) -> str:
    """Route after QA: either revise or deliver."""
    if state.qa_reports:
        latest = state.qa_reports[-1]
        if latest.revision_required and state.revision_count < state.max_revisions:
            return "revision"
    return "delivery"


def _after_revision(state: TeamState) -> str:
    """Route after revision arbitration to the correct agent phase."""
    return route_next_phase(state)


# ── Graph construction ─────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Build and compile the multi-agent team graph.

    This is the entrypoint referenced in langgraph.json.
    """
    graph = StateGraph(TeamState)

    # Add all nodes
    graph.add_node("intake", intake_node)
    graph.add_node("planning", plan_node)
    graph.add_node("research", research_node)
    graph.add_node("design", graphics_node)
    graph.add_node("frontend", frontend_node)
    graph.add_node("backend", backend_node)
    graph.add_node("qa", qa_node)
    graph.add_node("revision", revision_node)
    graph.add_node("delivery", delivery_node)

    # Set entry point
    graph.set_entry_point("intake")

    # intake -> planning -> (conditional) research or delivery
    graph.add_edge("intake", "planning")
    graph.add_conditional_edges("planning", _after_planning, {
        "research": "research",
        "delivery": "delivery",
    })
    graph.add_edge("research", "design")
    graph.add_edge("design", "frontend")
    graph.add_edge("frontend", "backend")
    graph.add_edge("backend", "qa")

    # After QA: either revise or deliver
    graph.add_conditional_edges("qa", _after_qa, {
        "revision": "revision",
        "delivery": "delivery",
    })

    # After revision arbitration: route back to the appropriate phase
    graph.add_conditional_edges("revision", _after_revision, {
        "research": "research",
        "design": "design",
        "frontend": "frontend",
        "backend": "backend",
        "delivery": "delivery",
    })

    # Delivery is the terminal node
    graph.add_edge("delivery", END)

    return graph.compile()
