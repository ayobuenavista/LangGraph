# LangGraph

A multi-agent AI team built on [LangGraph](https://langchain-ai.github.io/langgraph/) that produces web applications — dashboards, analytics tools, landing pages, and more. Each agent has a distinct specialization and they collaborate through a shared state graph deployed on [LangSmith](https://smith.langchain.com/).

## Architecture

```
User Request
     |
     v
 [ Intake ] ---- extracts the user prompt
     |
     v
 [ Orchestrator ] ---- decomposes into WorkPackets, assigns confidence scores
     |
     v
 [ Researcher ] ---- gathers market data, API docs, framework recommendations
     |
     v
 [ Graphics ] ---- generates color palettes, SVGs, style guides, layout specs
     |
     v
 [ Front-end ] ---- builds React/Next.js pages, charts, data hooks
     |
     v
 [ Back-end ] ---- creates FastAPI endpoints, Pydantic models, data pipelines
     |
     v
 [ QA ] ---+--- PASS ---> [ Delivery ] ---> Final Output
            |
            +--- FAIL ---> [ Revision ] ---> routes back to the failing agent
                            (up to 3 revision loops)
```

## Agents

| Agent | Role | LLM |
|---|---|---|
| **Orchestrator** | Plan decomposition, routing, revision arbitration | Claude Sonnet 4.6 |
| **Researcher** | DeFi/crypto market intelligence, API discovery | Kimi K2.5 Thinking |
| **Graphics** | Design system, color palettes, SVGs, accessibility | Gemini 3 Flash |
| **Front-end** | React/Next.js pages, charts, data hooks | OpenAI GPT 5.4 |
| **Back-end** | FastAPI endpoints, data transforms, caching | DeepSeek V3.2-Exp |
| **QA** | Security scans, accessibility audits, coverage checks | Claude Opus 4.6 |

## Shared State

All agents read from and write to a single `TeamState` (defined in `src/agents/state.py`):

```
TeamState
  messages              # Conversation history (append-only)
  user_request          # Original prompt
  plan                  # List[WorkPacket] from the Orchestrator
  current_phase         # Which agent is active
  research_artifacts    # List[ResearchArtifact]
  design_artifacts      # List[DesignArtifact]
  frontend_artifacts    # List[FrontendArtifact]
  backend_artifacts     # List[BackendArtifact]
  qa_reports            # List[QAReport]
  revision_count        # Tracks revision loops (max 3)
  final_output          # Compiled deliverable
```

Artifact lists use the `operator.add` reducer so each agent appends without overwriting previous results.

## Project Structure

```
Sons_of_Anton/
├── langgraph.json                  # LangSmith deployment config
├── pyproject.toml                  # Dependencies and package metadata
├── run.py                          # Local test runner with streaming output
├── .env.example                    # Required environment variables
└── src/agents/
    ├── graph.py                    # StateGraph definition (entrypoint)
    ├── state.py                    # TeamState + all Pydantic artifact models
    ├── orchestrator.py             # Orchestrator Agent (plan + revision nodes)
    ├── researcher.py               # Researcher Agent
    ├── graphics.py                 # Graphics Agent
    ├── frontend.py                 # Front-end Agent
    ├── backend.py                  # Back-end Agent
    ├── qa.py                       # QA Agent
    ├── prompts/
    │   └── system_prompts.py       # System prompts for all 6 agents
    └── tools/
        ├── research_tools.py       # CoinGecko, DefiLlama, yield APIs
        ├── graphics_tools.py       # Palettes, contrast, SVGs, Tailwind
        ├── frontend_tools.py       # Layouts, charts, hooks, pages
        ├── backend_tools.py        # Endpoints, models, transformers
        └── qa_tools.py             # Security, a11y, data, coverage
```

## Setup

### Prerequisites

- Python 3.11+
- API keys for LangSmith and the LLM models for each agent

### Install

```bash
pip install -e .
```

## Usage

### Run locally

```bash
# Default demo prompt (build pages)
python run.py

# Custom prompt
python run.py "Build a DeFi portfolio tracker with real-time PnL"
```

The runner streams each agent's work to stdout so you can follow the pipeline in real time.

### Deploy to LangSmith

```bash
# Start local dev server
langgraph up

# Deploy to LangSmith Cloud
langgraph deploy
```

The `langgraph.json` config points to `build_graph` in `src/agents/graph.py` as the entrypoint:

```json
{
  "dependencies": ["."],
  "graphs": {
    "sons_of_anton": "./src/agents/graph.py:build_graph"
  },
  "env": ".env"
}
```

### Invoke via LangSmith SDK

```python
from langgraph_sdk import get_client

client = get_client(url="YOUR_DEPLOYMENT_URL")
thread = await client.threads.create()

run = await client.runs.create(
    thread["thread_id"],
    "sons_of_anton",
    input={"messages": [{"role": "user", "content": "Build a yield farming leaderboard"}]},
)
```

## QA and Revision Loop

The QA Agent enforces an **Unreliability Tax** budget of 15%. It runs four checks on every build:

1. **Security scan** — hardcoded secrets, injection vectors, XSS, unsafe eval
2. **Accessibility audit** — missing alt text, ARIA labels, color contrast, semantic HTML
3. **Data consistency** — source values vs. displayed values within tolerance
4. **Requirements coverage** — delivered items vs. original requirements

If any check fails, QA routes the work back to the responsible agent through the Revision node. The loop runs up to 3 times before forcing delivery.

## Brand Guidelines

The Graphics Agent follows a built-in brand guide:

| Token | Value | Usage |
|---|---|---|
| Primary | `#6366F1` | Buttons, links, active states |
| Accent | `#22D3EE` | Highlights, badges |
| Success | `#10B981` | Positive values, gains |
| Danger | `#EF4444` | Negative values, losses |
| Background | `#0F172A` | Page background |
| Surface | `#1E293B` | Cards, panels |
| Text | `#F8FAFC` | Primary text |
| Font (UI) | Inter | All interface text |
| Font (Data) | JetBrains Mono | Numbers, code, monospace |

## License

MIT
