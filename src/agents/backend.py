"""Back-end Agent — API endpoints, data models, and transformations."""

from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

from agents.state import TeamState, BackendArtifact
from agents.prompts.system_prompts import BACKEND_PROMPT
from agents.tools.backend_tools import BACKEND_TOOLS


def _build_backend_agent():
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0.1,
        max_tokens=8192,
    )
    return create_react_agent(
        model=llm,
        tools=BACKEND_TOOLS,
        prompt=BACKEND_PROMPT,
    )


_backend_agent = None


def _get_backend_agent():
    global _backend_agent
    if _backend_agent is None:
        _backend_agent = _build_backend_agent()
    return _backend_agent


async def backend_node(state: TeamState) -> dict:
    """Build API endpoints, data models, and transformation logic."""
    agent = _get_backend_agent()

    # Research context for API sources
    research_context = "\n".join(
        f"- {a.topic}: endpoints={a.api_endpoints}, sources={a.data_sources}"
        for a in state.research_artifacts
    ) or "No research artifacts — use standard CoinGecko and DefiLlama APIs."

    # Frontend context for what the UI needs
    frontend_context = "\n".join(
        f"- Component '{a.component_name}' at {a.file_path}"
        for a in state.frontend_artifacts
    ) or "No frontend artifacts yet."

    backend_packets = [
        wp for wp in state.plan if wp.assigned_to == "backend"
    ]
    task_descriptions = "\n".join(
        f"- [{wp.id}] {wp.title}: {wp.description}"
        for wp in backend_packets
    ) or "Build API endpoints to serve token prices, TVL, and yield data."

    input_messages = [
        {
            "role": "user",
            "content": (
                f"Build the back-end for an app based on user's request.\n\n"
                f"Data sources from research:\n{research_context}\n\n"
                f"Frontend components that need data:\n{frontend_context}\n\n"
                f"Backend tasks:\n{task_descriptions}\n\n"
                f"You MUST produce:\n"
                f"1. Pydantic data models (use generate_pydantic_model)\n"
                f"2. FastAPI endpoints (use generate_fastapi_endpoint)\n"
                f"3. Data transformers for raw API data (use generate_data_transformer)\n"
                f"4. An aggregator for parallel data fetching (use generate_api_aggregator)\n\n"
                f"Use the tools for each deliverable."
            ),
        }
    ]

    result = await agent.ainvoke({"messages": input_messages})
    final_message = result["messages"][-1].content

    artifacts = [
        BackendArtifact(
            endpoint_or_model="App API",
            file_path="api/backend.py",
            code=final_message,
            language="python",
        ),
    ]

    return {
        "backend_artifacts": artifacts,
        "current_phase": "qa",
        "messages": [AIMessage(
            content=f"Backend complete. Produced {len(artifacts)} artifacts.\n\n{final_message[:1000]}",
            name="backend",
        )],
    }
