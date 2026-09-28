"""FastAPI application for Graphite Interactive Blueprint Viewer & Grounded Dialogue REST API."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from graphite.core.parser import parse_graphml
from graphite.core.collapsing import collapse_connectors
from graphite.mmkg.representation import MultimodalKnowledgeGraph
from graphite.mmkg.builder import MMKGBuilder
from graphite.reasoning.engine import TopologicalReasoningEngine
from graphite.rag.engine import GraphRAGEngine
from graphite.rag.context import LocalRetrievalContext, GlobalRetrievalContext
from graphite.api.models import (
    QueryRequest,
    QueryResponse,
    ChatRequest,
    ChatResponse,
    ChatMessage,
    VisualCitation,
    NodeDetailResponse,
    ValveSimulationRequest,
    ValveSimulationResponse,
)


def create_app(
    mmkg: Optional[MultimodalKnowledgeGraph] = None,
    reasoning_engine: Optional[TopologicalReasoningEngine] = None,
    image_path: Optional[Path] = None,
    crops_dir: Optional[Path] = None,
) -> FastAPI:
    """Create and configure the master Graphite FastAPI service."""
    app = FastAPI(
        title="Graphite MMKG & GraphRAG API",
        description="Multimodal GraphRAG Framework for Complex Technical Blueprint Analysis",
        version="0.1.0",
    )

    # Enable CORS for browser integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Resolve default paths
    base_dir = Path(__file__).resolve().parent
    static_dir = base_dir / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    default_crops_dir = Path("outputs/mmkg_crops").resolve()
    active_crops_dir = crops_dir or default_crops_dir
    active_crops_dir.mkdir(parents=True, exist_ok=True)

    default_img_path = Path("data/PID2Graph/Complete/PID2Graph OPEN100/0.png").resolve()
    active_img_path = image_path or default_img_path

    # Initialize MMKG and Reasoning Engine if not injected
    if mmkg is None:
        graphml_p = Path("data/PID2Graph/Complete/PID2Graph OPEN100/0.graphml").resolve()
        if graphml_p.exists():
            raw_g = parse_graphml(graphml_p, image_path=active_img_path)
            collapsed_g = collapse_connectors(raw_g, remove_crossings=False)
            builder = MMKGBuilder(device="cpu")
            sample_specs = {
                "general13": {"tag": "P-101", "type": "Centrifugal Feed Pump", "flow": "85 m3/hr", "head": "60 m"},
                "valve99": {"tag": "V-101", "type": "Isolation Gate Valve", "rating": "300# ANSI", "material": "SS316"},
                "tank70": {"tag": "TK-01", "type": "Main Storage Vessel", "capacity": "50000 L", "pressure": "Atmospheric"},
            }
            mmkg = builder.build_mmkg(
                collapsed_g,
                blueprint_image_path=active_img_path,
                crop_output_dir=active_crops_dir,
                equipment_specs=sample_specs,
            )
            bp_graph = collapsed_g
        else:
            mmkg = MultimodalKnowledgeGraph(name="empty_mmkg")
            from graphite.core.models import BlueprintGraph
            bp_graph = BlueprintGraph(name="empty_graph")
    else:
        # Construct matching BlueprintGraph from mmkg for reasoning engine
        from graphite.core.models import BlueprintGraph, ComponentNode
        bp_graph = BlueprintGraph(
            name=mmkg.name,
            image_path=mmkg.image_path,
            image_width=mmkg.image_width,
            image_height=mmkg.image_height,
        )
        for nid, node in mmkg.nodes.items():
            bp_graph.add_node(ComponentNode(
                id=node.id,
                label=node.label,
                bbox=node.bbox,
                center=node.get_center(),
                attributes=node.attributes,
            ))
        for edge in mmkg.edges:
            bp_graph.add_edge(edge)

    engine = reasoning_engine or TopologicalReasoningEngine(bp_graph)
    rag_engine = GraphRAGEngine(mmkg, engine)

    # In-memory multi-turn chat sessions
    chat_sessions: Dict[str, List[ChatMessage]] = {}

    # Mount static assets and symbol crops
    if active_crops_dir.exists():
        app.mount("/crops", StaticFiles(directory=str(active_crops_dir)), name="crops")

    # ---------------- API ENDPOINTS ----------------

    @app.get("/api/health")
    def health_check() -> Dict[str, Any]:
        """Health and system metrics endpoint."""
        return {
            "status": "healthy",
            "framework": "Graphite MMKG & Dual-Mode GraphRAG",
            "version": "0.1.0",
            "blueprint_name": mmkg.name,
            "total_nodes": len(mmkg.nodes),
            "total_edges": len(mmkg.edges),
            "total_subsystems": len(mmkg.subsystems),
            "image_available": active_img_path.exists(),
        }

    @app.get("/api/blueprint")
    def get_blueprint_topology() -> Dict[str, Any]:
        """Return the complete blueprint topology for interactive canvas rendering."""
        nodes_payload = []
        for nid, node in mmkg.nodes.items():
            cx, cy = node.get_center()
            safe_nid = nid.replace("/", "_").replace("\\", "_")
            crop_url = f"/crops/{safe_nid}.png"
            nodes_payload.append({
                "id": node.id,
                "label": node.label,
                "tag": node.tag,
                "cx": cx,
                "cy": cy,
                "bbox": node.bbox.to_tuple() if node.bbox else None,
                "subsystem_id": node.subsystem_id,
                "subsystem_name": node.subsystem_name,
                "specs": node.specs,
                "crop_url": crop_url,
            })

        edges_payload = []
        for edge in mmkg.edges:
            edges_payload.append({
                "source": edge.source,
                "target": edge.target,
                "edge_label": edge.edge_label,
                "hops": edge.hops,
                "length": edge.length,
                "waypoints": edge.waypoints,
            })

        return {
            "name": mmkg.name,
            "image_width": mmkg.image_width or 1000,
            "image_height": mmkg.image_height or 1000,
            "image_url": "/api/blueprint/image" if active_img_path.exists() else None,
            "nodes": nodes_payload,
            "edges": edges_payload,
            "subsystems": mmkg.subsystems,
        }

    @app.get("/api/blueprint/image")
    def get_blueprint_raster_image():
        """Serve the raw high-resolution technical blueprint image."""
        if not active_img_path.exists():
            raise HTTPException(status_code=404, detail="Blueprint image file not found.")
        return FileResponse(str(active_img_path), media_type="image/png")

    @app.get("/api/node/{node_id}", response_model=NodeDetailResponse)
    def get_node_details(node_id: str) -> NodeDetailResponse:
        """Fetch deep engineering specs, topological relations, and isolation boundary for a component."""
        node = mmkg.nodes.get(node_id)
        if not node:
            # Try tag lookup
            node = mmkg.get_node_by_tag(node_id)
        if not node:
            raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found in MMKG.")

        nid = node.id
        cx, cy = node.get_center()
        safe_nid = nid.replace("/", "_").replace("\\", "_")
        crop_url = f"/crops/{safe_nid}.png"

        # Neighbors
        G_nx = engine.graph.to_networkx(directed=False)
        neighbors = list(G_nx.neighbors(nid)) if nid in G_nx else []

        # Upstream & Downstream
        upstream = engine.trace_upstream(nid)
        downstream = engine.trace_downstream(nid)

        # Boundary valves
        iso_valves = engine.find_containment_valves(nid)
        bypasses = engine.find_bypasses(nid)

        # Subsystem domain
        domain = None
        if node.subsystem_id is not None and node.subsystem_id in mmkg.subsystems:
            domain = mmkg.subsystems[node.subsystem_id].get("domain_category")

        return NodeDetailResponse(
            id=node.id,
            label=node.label,
            tag=node.tag,
            center=(cx, cy),
            bbox=node.bbox.to_tuple() if node.bbox else None,
            specs=node.specs,
            subsystem_id=node.subsystem_id,
            subsystem_name=node.subsystem_name,
            domain_category=domain,
            visual_crop_url=crop_url,
            neighbors=neighbors,
            upstream=upstream,
            downstream=downstream,
            isolation_valves=iso_valves,
            bypasses=bypasses,
        )

    @app.post("/api/query", response_model=QueryResponse)
    def query_graphrag(req: QueryRequest) -> QueryResponse:
        """Execute grounded Dual-Mode GraphRAG query with visual & topological citations."""
        session_id = req.session_id or str(uuid.uuid4())

        resp = rag_engine.query(
            query_str=req.query,
            mode=req.mode,
            target_id=req.target_id,
            k_hop=req.k_hop,
        )

        visual_citations: List[VisualCitation] = []
        highlighted_nodes: List[str] = []
        highlighted_edges: List[Tuple[str, str]] = []
        highlighted_waypoints: List[List[Tuple[float, float]]] = []
        target_payload: Optional[Dict[str, Any]] = None

        if isinstance(resp.context, LocalRetrievalContext):
            l_ctx = resp.context
            target_node = mmkg.nodes.get(l_ctx.target_node_id)
            if target_node:
                target_payload = {
                    "id": target_node.id,
                    "tag": target_node.tag,
                    "label": target_node.label,
                    "center": target_node.get_center(),
                    "specs": target_node.specs,
                }

            for snode in l_ctx.subgraph_nodes:
                nid = snode["id"]
                highlighted_nodes.append(nid)
                safe_nid = nid.replace("/", "_").replace("\\", "_")
                node_obj = mmkg.nodes.get(nid)
                visual_citations.append(
                    VisualCitation(
                        node_id=nid,
                        tag=snode.get("tag"),
                        label=snode.get("label", "unknown"),
                        crop_url=f"/crops/{safe_nid}.png",
                        center=snode.get("center", (0.0, 0.0)),
                        bbox=node_obj.bbox.to_tuple() if node_obj and node_obj.bbox else None,
                    )
                )

            for sedge in l_ctx.subgraph_edges:
                highlighted_edges.append((sedge["source"], sedge["target"]))
                if sedge.get("waypoints"):
                    highlighted_waypoints.append(sedge["waypoints"])

        elif isinstance(resp.context, GlobalRetrievalContext):
            for s in resp.context.subsystem_summaries[:5]:
                for b_valve in s.get("boundary_valves", []):
                    if b_valve not in highlighted_nodes:
                        highlighted_nodes.append(b_valve)

        return QueryResponse(
            query=req.query,
            retrieval_mode=resp.retrieval_mode,
            grounded_answer=resp.grounded_answer,
            visual_citations=visual_citations,
            topological_citations=resp.topological_citations,
            highlighted_node_ids=highlighted_nodes,
            highlighted_edge_ids=highlighted_edges,
            highlighted_waypoints=highlighted_waypoints,
            target_node=target_payload,
            session_id=session_id,
        )

    @app.post("/api/chat", response_model=ChatResponse)
    def chat_dialogue(req: ChatRequest) -> ChatResponse:
        """Handle multi-turn grounded conversation preserving conversational context."""
        session_id = req.session_id or str(uuid.uuid4())
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []

        now_str = datetime.now().strftime("%H:%M:%S")
        # Add user message
        chat_sessions[session_id].append(
            ChatMessage(role="user", content=req.message, timestamp=now_str)
        )

        # Run GraphRAG query
        q_resp = query_graphrag(QueryRequest(query=req.message, session_id=session_id, k_hop=req.k_hop))

        # Add assistant reply
        chat_sessions[session_id].append(
            ChatMessage(
                role="assistant",
                content=q_resp.grounded_answer,
                timestamp=datetime.now().strftime("%H:%M:%S"),
                citations=q_resp.topological_citations,
                visual_citations=q_resp.visual_citations,
                highlighted_nodes=q_resp.highlighted_node_ids,
                highlighted_edges=q_resp.highlighted_edge_ids,
            )
        )

        return ChatResponse(
            session_id=session_id,
            reply=q_resp.grounded_answer,
            retrieval_mode=q_resp.retrieval_mode,
            visual_citations=q_resp.visual_citations,
            topological_citations=q_resp.topological_citations,
            highlighted_node_ids=q_resp.highlighted_node_ids,
            highlighted_edge_ids=q_resp.highlighted_edge_ids,
            history=chat_sessions[session_id],
        )

    @app.get("/api/subsystems")
    def get_plant_hierarchy() -> Dict[str, Any]:
        """Return the plant-wide hierarchical domain tree for Global Retrieval."""
        return mmkg.get_subsystem_hierarchy()

    @app.get("/api/compliance")
    def get_compliance_report() -> Dict[str, Any]:
        """Run industrial engineering compliance audit."""
        report = engine.audit_compliance()
        return report.model_dump()

    @app.post("/api/simulate/valve", response_model=ValveSimulationResponse)
    def simulate_valves(req: ValveSimulationRequest) -> ValveSimulationResponse:
        """Simulate closing boundary valves and calculate isolated process equipment."""
        closed_set = set(req.closed_valve_ids)
        flow_result = engine.trace_flow(origin=req.origin_node, closed_valves=closed_set)
        all_nodes = set(engine.graph.nodes.keys())
        reachable = set(flow_result.reachable_nodes)
        isolated = sorted(list(all_nodes - reachable))

        return ValveSimulationResponse(
            origin_node=req.origin_node,
            closed_valves=req.closed_valve_ids,
            reachable_nodes=flow_result.reachable_nodes,
            isolated_nodes=isolated,
            traversed_edges=flow_result.traversed_edges,
        )

    @app.get("/", response_class=HTMLResponse)
    def serve_interactive_viewer():
        """Serve the Graphite Interactive Blueprint Viewer & Grounded Dialogue UI."""
        html_file = static_dir / "index.html"
        if html_file.exists():
            return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
        return HTMLResponse("<h2>Graphite Interactive Viewer: UI file missing.</h2>")

    return app
