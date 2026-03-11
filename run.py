#!/usr/bin/env python3
"""Local runner for the multi-agent dashboard team.

Usage:
    python run.py "Build a DeFi yield farming dashboard showing top pools by APY"
    python run.py  # uses default demo prompt
"""

from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()

# Add src to path for local execution
sys.path.insert(0, "src")

from agents.graph import build_graph  # noqa: E402


DEFAULT_PROMPT = (
    "Build a crypto dashboard that shows:\n"
    "1. Top 10 tokens by market cap with real-time price updates\n"
    "2. DeFi TVL comparison chart across protocols (Aave, Lido, Uniswap, Pendle)\n"
    "3. Yield farming opportunities table with APY, TVL, and risk indicators\n"
    "4. A portfolio tracker section where users can input their holdings"
)


async def main():
    user_input = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_PROMPT

    print(f"{'='*60}")
    print("Son of Anton — Multi-Agent Dashboard Team")
    print(f"{'='*60}")
    print(f"\nUser Request:\n{user_input}\n")
    print(f"{'='*60}\n")

    graph = build_graph()

    # Stream events to see each agent's work
    async for event in graph.astream_events(
        {"messages": [{"role": "user", "content": user_input}]},
        version="v2",
    ):
        kind = event.get("event", "")
        name = event.get("name", "")

        if kind == "on_chain_start" and name in {
            "intake", "planning", "research", "design",
            "frontend", "backend", "qa", "revision", "delivery",
        }:
            print(f"\n--- [{name.upper()}] Agent starting ---\n")

        elif kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                print(chunk.content, end="", flush=True)

        elif kind == "on_tool_start":
            tool_name = event.get("name", "unknown")
            print(f"\n  [tool] {tool_name}...", end="", flush=True)

        elif kind == "on_tool_end":
            print(" done.", flush=True)

    # Get final state
    final_state = await graph.ainvoke(
        {"messages": [{"role": "user", "content": user_input}]},
    )

    print(f"\n\n{'='*60}")
    print("FINAL DELIVERABLE")
    print(f"{'='*60}\n")
    print(final_state.get("final_output", "No output produced."))


if __name__ == "__main__":
    asyncio.run(main())
