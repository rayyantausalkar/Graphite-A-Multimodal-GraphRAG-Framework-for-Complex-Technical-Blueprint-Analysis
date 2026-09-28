"""API request and response schemas for Graphite Interactive Viewer and REST service."""

from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """User query request payload for Dual-Mode GraphRAG."""
    query: str
    mode: str = "auto"  # "auto", "local", "global"
    k_hop: int = 2
    target_id: Optional[str] = None
    session_id: Optional[str] = None


class VisualCitation(BaseModel):
    """Visual evidence citation linking text answers to blueprint symbol crops."""
    node_id: str
    tag: Optional[str] = None
    label: str
    crop_url: str
    center: Tuple[float, float]
    bbox: Optional[Tuple[float, float, float, float]] = None


class QueryResponse(BaseModel):
    """Grounded GraphRAG answer payload with topological and visual citations."""
    query: str
    retrieval_mode: str  # "local" or "global"
    grounded_answer: str
    visual_citations: List[VisualCitation] = Field(default_factory=list)
    topological_citations: List[str] = Field(default_factory=list)
    highlighted_node_ids: List[str] = Field(default_factory=list)
    highlighted_edge_ids: List[Tuple[str, str]] = Field(default_factory=list)
    highlighted_waypoints: List[List[Tuple[float, float]]] = Field(default_factory=list)
    target_node: Optional[Dict[str, Any]] = None
    session_id: str


class ChatMessage(BaseModel):
    """Individual conversational turn in multi-turn dialogue."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str
    citations: List[str] = Field(default_factory=list)
    visual_citations: List[VisualCitation] = Field(default_factory=list)
    highlighted_nodes: List[str] = Field(default_factory=list)
    highlighted_edges: List[Tuple[str, str]] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """Multi-turn conversational request."""
    message: str
    session_id: Optional[str] = None
    k_hop: int = 2


class ChatResponse(BaseModel):
    """Multi-turn conversational response with conversation history."""
    session_id: str
    reply: str
    retrieval_mode: str
    visual_citations: List[VisualCitation] = Field(default_factory=list)
    topological_citations: List[str] = Field(default_factory=list)
    highlighted_node_ids: List[str] = Field(default_factory=list)
    highlighted_edge_ids: List[Tuple[str, str]] = Field(default_factory=list)
    history: List[ChatMessage] = Field(default_factory=list)


class NodeDetailResponse(BaseModel):
    """Comprehensive asset inspector payload."""
    id: str
    label: str
    tag: Optional[str] = None
    center: Tuple[float, float]
    bbox: Optional[Tuple[float, float, float, float]] = None
    specs: Dict[str, Any] = Field(default_factory=dict)
    subsystem_id: Optional[int] = None
    subsystem_name: Optional[str] = None
    domain_category: Optional[str] = None
    visual_crop_url: Optional[str] = None
    neighbors: List[str] = Field(default_factory=list)
    upstream: List[str] = Field(default_factory=list)
    downstream: List[str] = Field(default_factory=list)
    isolation_valves: List[str] = Field(default_factory=list)
    bypasses: List[List[str]] = Field(default_factory=list)


class ValveSimulationRequest(BaseModel):
    """Request to simulate closing one or more boundary valves."""
    closed_valve_ids: List[str]
    origin_node: str


class ValveSimulationResponse(BaseModel):
    """Simulation results showing impacted and isolated components."""
    origin_node: str
    closed_valves: List[str]
    reachable_nodes: List[str]
    isolated_nodes: List[str]
    traversed_edges: List[Tuple[str, str]]
