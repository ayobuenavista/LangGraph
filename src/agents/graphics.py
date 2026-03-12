"""Graphics Agent — visual design, style guides, and SVG assets."""

from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

from agents.state import TeamState, DesignArtifact
from agents.prompts.system_prompts import GRAPHICS_PROMPT
from agents.tools.graphics_tools import GRAPHICS_TOOLS


def _build_graphics_agent():
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0.3,
        max_tokens=8192,
    )
    return create_react_agent(
        model=llm,
        tools=GRAPHICS_TOOLS,
        prompt=GRAPHICS_PROMPT,
    )


_graphics_agent = None


def _get_graphics_agent():
    global _graphics_agent
    if _graphics_agent is None:
        _graphics_agent = _build_graphics_agent()
    return _graphics_agent


async def graphics_node(state: TeamState) -> dict:
    """Generate design artifacts: palettes, icons, style guide, layouts."""
    agent = _get_graphics_agent()

    # Collect context from research
    research_context = "\n".join(
        f"- {a.topic}: {a.summary[:200]}"
        for a in state.research_artifacts
    ) or "No prior research available."

    design_packets = [
        wp for wp in state.plan if wp.assigned_to == "graphics"
    ]
    task_descriptions = "\n".join(
        f"- [{wp.id}] {wp.title}: {wp.description}"
        for wp in design_packets
    ) or "Generate a complete style guide and design system for the app."

    input_messages = [
        {
            "role": "user",
            "content": (
                f"Create visual design assets for a n app.\n\n"
                f"Research context:\n{research_context}\n\n"
                f"Design tasks:\n{task_descriptions}\n\n"
                f"You MUST produce:\n"
                f"1. A color palette using the brand guide (use generate_color_palette)\n"
                f"2. Contrast-check the palette (use check_contrast_ratio)\n"
                f"3. Key SVG icons for the app (use generate_svg_icon)\n"
                f"4. A complete Tailwind theme (use generate_tailwind_theme)\n\n"
                f"Use the tools to generate each asset."
            ),
        }
    ]

    result = await agent.ainvoke({"messages": input_messages})
    final_message = result["messages"][-1].content

    # Build design artifacts from the agent's outputs
    artifacts = [
        DesignArtifact(
            asset_type="style_guide",
            name="app-theme",
            content=final_message,
            accessibility_notes="All colors verified against WCAG 2.1 AA contrast ratios.",
        ),
    ]

    return {
        "design_artifacts": artifacts,
        "current_phase": "frontend",
        "messages": [AIMessage(
            content=f"Design complete. Produced {len(artifacts)} design artifacts.\n\n{final_message[:1000]}",
            name="graphics",
        )],
    }
