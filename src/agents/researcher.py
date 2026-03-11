"""Researcher Agent — Intelligence gathering via RAG."""

from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

from agents.state import TeamState, ResearchArtifact
from agents.prompts.system_prompts import RESEARCHER_PROMPT
from agents.tools.research_tools import RESEARCH_TOOLS


def _build_researcher_agent():
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0.1,
        max_tokens=8192,
    )
    return create_react_agent(
        model=llm,
        tools=RESEARCH_TOOLS,
        prompt=RESEARCHER_PROMPT,
    )


_researcher = None


def _get_researcher():
    global _researcher
    if _researcher is None:
        _researcher = _build_researcher_agent()
    return _researcher


async def research_node(state: TeamState) -> dict:
    """Execute research tasks from the plan."""
    agent = _get_researcher()

    # Gather research-assigned work packets
    research_packets = [
        wp for wp in state.plan if wp.assigned_to == "researcher"
    ]
    if not research_packets:
        return {
            "current_phase": "design",
            "messages": [AIMessage(
                content="No research tasks in plan. Moving to design.",
                name="researcher",
            )],
        }

    task_descriptions = "\n".join(
        f"- [{wp.id}] {wp.title}: {wp.description}"
        for wp in research_packets
    )

    input_messages = [
        {
            "role": "user",
            "content": (
                f"Execute the following research tasks:\n\n"
                f"{task_descriptions}\n\n"
                f"For each task, use the available tools to fetch real data. "
                f"Then summarize your findings as structured research artifacts "
                f"with: topic, summary, data_sources, api_endpoints, and any raw_data."
            ),
        }
    ]

    result = await agent.ainvoke({"messages": input_messages})
    final_message = result["messages"][-1].content

    # Parse artifacts from the agent's research
    artifacts = []
    for wp in research_packets:
        artifacts.append(ResearchArtifact(
            topic=wp.title,
            summary=f"Research completed for: {wp.description}. {final_message[:500]}",
            data_sources=["Pendle", "CoinGecko", "DefiLlama"],
            api_endpoints=[
                "https://api-v2.pendle.finance/core",
                "https://api.coingecko.com/api/v3/simple/price",
                "https://api.llama.fi/protocols",
                "https://yields.llama.fi/pools",
            ],
        ))

    return {
        "research_artifacts": artifacts,
        "current_phase": "design",
        "messages": [AIMessage(
            content=f"Research complete. Produced {len(artifacts)} artifacts.\n\n{final_message[:1000]}",
            name="researcher",
        )],
    }
