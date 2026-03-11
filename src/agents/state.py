"""Shared state definitions for the multi-agent dashboard team."""

from __future__ import annotations

import operator
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages


# ---------------------------------------------------------------------------
# Work-packet model: the unit of work exchanged between agents
# ---------------------------------------------------------------------------

class WorkPacket(BaseModel):
    """A discrete unit of work assigned by the Orchestrator."""

    id: str = Field(description="Unique packet identifier, e.g. 'wp-001'")
    assigned_to: Literal[
        "researcher", "graphics", "frontend", "backend", "qa"
    ]
    title: str
    description: str
    dependencies: list[str] = Field(
        default_factory=list,
        description="IDs of work packets that must complete first",
    )
    status: Literal["pending", "in_progress", "done", "revision"] = "pending"
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Orchestrator's confidence that this packet is well-scoped",
    )


# ---------------------------------------------------------------------------
# Artifact models produced by each agent
# ---------------------------------------------------------------------------

class ResearchArtifact(BaseModel):
    topic: str
    summary: str
    data_sources: list[str] = Field(default_factory=list)
    api_endpoints: list[str] = Field(default_factory=list)
    raw_data: dict | None = None


class DesignArtifact(BaseModel):
    asset_type: Literal["palette", "icon_svg", "style_guide", "layout"]
    name: str
    content: str  # CSS variables, SVG markup, or JSON layout spec
    accessibility_notes: str = ""


class FrontendArtifact(BaseModel):
    component_name: str
    file_path: str
    code: str
    framework: Literal["react", "nextjs"] = "nextjs"


class BackendArtifact(BaseModel):
    endpoint_or_model: str
    file_path: str
    code: str
    language: Literal["python", "typescript"] = "python"


class QAReport(BaseModel):
    target_packet_id: str
    passed: bool
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    revision_required: bool = False
    revision_target: str | None = None


# ---------------------------------------------------------------------------
# Top-level graph state
# ---------------------------------------------------------------------------

class TeamState(BaseModel):
    """The shared state that flows through the entire LangGraph graph."""

    # Conversation history (append-only via add_messages reducer)
    messages: Annotated[list[AnyMessage], add_messages] = Field(
        default_factory=list
    )

    # The original user request
    user_request: str = ""

    # Orchestrator planning
    plan: list[WorkPacket] = Field(default_factory=list)
    current_phase: Literal[
        "planning",
        "research",
        "design",
        "frontend",
        "backend",
        "qa",
        "delivery",
    ] = "planning"

    # Agent artifacts (append via operator.add reducer)
    research_artifacts: Annotated[list[ResearchArtifact], operator.add] = (
        Field(default_factory=list)
    )
    design_artifacts: Annotated[list[DesignArtifact], operator.add] = Field(
        default_factory=list
    )
    frontend_artifacts: Annotated[list[FrontendArtifact], operator.add] = (
        Field(default_factory=list)
    )
    backend_artifacts: Annotated[list[BackendArtifact], operator.add] = Field(
        default_factory=list
    )
    qa_reports: Annotated[list[QAReport], operator.add] = Field(
        default_factory=list
    )

    # Revision loop
    revision_count: int = 0
    max_revisions: int = 3

    # Final deliverable
    final_output: str = ""
