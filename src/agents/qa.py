"""QA Agent — the final quality gate with revision authority."""

from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

from agents.state import TeamState, QAReport
from agents.prompts.system_prompts import QA_PROMPT
from agents.tools.qa_tools import QA_TOOLS


def _build_qa_agent():
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0.0,
        max_tokens=8192,
    )
    return create_react_agent(
        model=llm,
        tools=QA_TOOLS,
        prompt=QA_PROMPT,
    )


_qa_agent = None


def _get_qa_agent():
    global _qa_agent
    if _qa_agent is None:
        _qa_agent = _build_qa_agent()
    return _qa_agent


async def qa_node(state: TeamState) -> dict:
    """Review all artifacts for quality, security, accessibility, and completeness."""
    agent = _get_qa_agent()

    # Compile all code artifacts for review
    code_to_review = []
    for a in state.frontend_artifacts:
        code_to_review.append(f"### Frontend: {a.component_name}\n```\n{a.code[:2000]}\n```")
    for a in state.backend_artifacts:
        code_to_review.append(f"### Backend: {a.endpoint_or_model}\n```\n{a.code[:2000]}\n```")

    code_summary = "\n\n".join(code_to_review) or "No code artifacts to review."

    # Requirements from the plan
    requirements = [wp.title for wp in state.plan]

    # Delivered items
    delivered = (
        [f"Research: {a.topic}" for a in state.research_artifacts]
        + [f"Design: {a.name}" for a in state.design_artifacts]
        + [f"Frontend: {a.component_name}" for a in state.frontend_artifacts]
        + [f"Backend: {a.endpoint_or_model}" for a in state.backend_artifacts]
    )

    input_messages = [
        {
            "role": "user",
            "content": (
                f"Perform a complete quality review of the project.\n\n"
                f"Original user request: {state.user_request}\n\n"
                f"Code to review:\n{code_summary}\n\n"
                f"Requirements: {requirements}\n"
                f"Delivered items: {delivered}\n\n"
                f"You MUST:\n"
                f'1. Security-scan all code (use review_code_security with the code text)\n'
                f'2. Check accessibility of frontend components (use check_accessibility)\n'
                f'3. Verify requirements coverage (use check_requirements_coverage)\n'
                f"4. Report whether revision is needed and for which agent.\n\n"
                f"Unreliability Tax budget: 15%. If >15% of checks fail, flag for re-plan."
            ),
        }
    ]

    result = await agent.ainvoke({"messages": input_messages})
    final_message = result["messages"][-1].content

    # Determine if revision is needed based on the QA agent's assessment
    needs_revision = any(
        keyword in final_message.lower()
        for keyword in ["revision required", "needs revision", "must revise", "fail"]
    )

    revision_target = None
    if needs_revision:
        for phase in ["frontend", "backend", "graphics", "researcher"]:
            if phase in final_message.lower():
                revision_target = phase if phase != "graphics" else "design"
                break

    report = QAReport(
        target_packet_id="all",
        passed=not needs_revision,
        issues=[final_message[:500]] if needs_revision else [],
        suggestions=[],
        revision_required=needs_revision and state.revision_count < state.max_revisions,
        revision_target=revision_target,
    )

    next_phase = "delivery"
    if report.revision_required and revision_target:
        next_phase = revision_target

    return {
        "qa_reports": [report],
        "current_phase": next_phase,
        "messages": [AIMessage(
            content=f"QA review complete. Passed: {report.passed}.\n\n{final_message[:1000]}",
            name="qa",
        )],
    }
