"""Front-end Agent — React/Next.js component generation."""

from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

from agents.state import TeamState, FrontendArtifact
from agents.prompts.system_prompts import FRONTEND_PROMPT
from agents.tools.frontend_tools import FRONTEND_TOOLS


def _build_frontend_agent():
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0.2,
        max_tokens=8192,
    )
    return create_react_agent(
        model=llm,
        tools=FRONTEND_TOOLS,
        prompt=FRONTEND_PROMPT,
    )


_frontend_agent = None


def _get_frontend_agent():
    global _frontend_agent
    if _frontend_agent is None:
        _frontend_agent = _build_frontend_agent()
    return _frontend_agent


async def frontend_node(state: TeamState) -> dict:
    """Build React/Next.js components for the requested web application."""
    agent = _get_frontend_agent()

    # Gather context from design and backend artifacts
    design_context = "\n".join(
        f"- {a.asset_type} '{a.name}': {a.content[:300]}"
        for a in state.design_artifacts
    ) or "No design artifacts yet — use brand defaults."

    backend_context = "\n".join(
        f"- {a.endpoint_or_model} ({a.file_path})"
        for a in state.backend_artifacts
    ) or "No backend artifacts yet — create mock data hooks."

    research_context = "\n".join(
        f"- {a.topic}: APIs = {a.api_endpoints}"
        for a in state.research_artifacts
    ) or "No research context."

    frontend_packets = [
        wp for wp in state.plan if wp.assigned_to == "frontend"
    ]
    task_descriptions = "\n".join(
        f"- [{wp.id}] {wp.title}: {wp.description}"
        for wp in frontend_packets
    ) or "Build the front-end application as described in the user request."

    input_messages = [
        {
            "role": "user",
            "content": (
                f"Build the front-end for this project.\n\n"
                f"User request: {state.user_request}\n\n"
                f"Design system:\n{design_context}\n\n"
                f"Available API endpoints:\n{backend_context}\n\n"
                f"Data sources:\n{research_context}\n\n"
                f"Frontend tasks:\n{task_descriptions}\n\n"
                f"Produce the appropriate components for this project:\n"
                f"1. Page layout (use scaffold_page_layout with the right layout_type)\n"
                f"2. Charts if data visualization is needed (use generate_chart_component)\n"
                f"3. Data-fetching hooks for any API endpoints (use generate_data_fetcher)\n"
                f"4. Page-level components for each route (use scaffold_page_component)\n"
                f"5. Any additional UI components (use scaffold_nextjs_component)\n\n"
                f"Adapt the architecture to what the user actually asked for — "
                f"do not assume it is always a dashboard.\n\n"
                f"Use the tools for each deliverable."
            ),
        }
    ]

    result = await agent.ainvoke({"messages": input_messages})
    final_message = result["messages"][-1].content

    # Infer a sensible page name from the plan
    page_name = "App"
    if frontend_packets:
        page_name = frontend_packets[0].title.split()[0].title()

    artifacts = [
        FrontendArtifact(
            component_name=f"{page_name}Page",
            file_path=f"app/{page_name.lower()}/page.tsx",
            code=final_message,
            framework="nextjs",
        ),
    ]

    return {
        "frontend_artifacts": artifacts,
        "current_phase": "backend",
        "messages": [AIMessage(
            content=f"Frontend complete. Produced {len(artifacts)} components.\n\n{final_message[:1000]}",
            name="frontend",
        )],
    }
