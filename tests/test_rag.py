"""Unit tests for Layer 3: Dual-Mode GraphRAG Retrieval & Generation."""

from pathlib import Path
import pytest

from graphite.core.parser import parse_graphml
from graphite.core.collapsing import collapse_connectors
from graphite.mmkg.builder import MMKGBuilder
from graphite.rag.context import LocalRetrievalContext, GlobalRetrievalContext, GraphRAGResponse
from graphite.rag.retriever import LocalRetriever, GlobalRetriever, DualModeGraphRAGRetriever
from graphite.rag.generator import GraphRAGGenerator
from graphite.rag.engine import GraphRAGEngine


@pytest.fixture(scope="module")
def sample_mmkg():
    file_path = Path("data/PID2Graph/Complete/PID2Graph OPEN100/0.graphml")
    if not file_path.exists():
        pytest.skip("Dataset file not available")

    raw = parse_graphml(file_path)
    collapsed = collapse_connectors(raw)

    builder = MMKGBuilder(enable_visual_embeddings=False, device="cpu")
    specs = {
        "valve99": {"tag": "V-101", "rating": "150#", "type": "gate"},
        "general13": {"tag": "P-101", "flow": "50 m3/h", "type": "pump"},
    }
    return builder.build_mmkg(collapsed, equipment_specs=specs)


def test_local_retrieval(sample_mmkg):
    local_retriever = LocalRetriever(sample_mmkg)
    ctx = local_retriever.retrieve("general13", k_hop=2)

    assert ctx is not None
    assert isinstance(ctx, LocalRetrievalContext)
    assert ctx.target_node_id == "general13"
    assert len(ctx.subgraph_nodes) > 0
    assert len(ctx.subgraph_edges) >= 0
    assert isinstance(ctx.upstream_equipment, list)
    assert isinstance(ctx.downstream_equipment, list)
    assert isinstance(ctx.isolation_valves, list)

    summary_text = ctx.summary()
    assert "Component: general13" in summary_text
    assert "2-Hop Subgraph" in summary_text


def test_global_retrieval(sample_mmkg):
    global_retriever = GlobalRetriever(sample_mmkg)
    ctx = global_retriever.retrieve()

    assert ctx is not None
    assert isinstance(ctx, GlobalRetrievalContext)
    assert ctx.total_equipment_count == len(sample_mmkg.nodes)
    assert ctx.total_subsystems == len(sample_mmkg.subsystems)
    assert "Process" in ctx.domains
    assert len(ctx.subsystem_summaries) == len(sample_mmkg.subsystems)

    summary_text = ctx.summary()
    assert "Plant Hierarchy" in summary_text
    assert "Total Physical Assets" in summary_text


def test_dual_mode_routing(sample_mmkg):
    router = DualModeGraphRAGRetriever(sample_mmkg)

    # Local queries
    assert router.route_query("What is downstream of P-101?") == "local"
    assert router.route_query("How do I isolate valve99?") == "local"
    assert router.route_query("Find bypass path around the pump") == "local"

    # Global queries
    assert router.route_query("Provide an overview of all plant subsystems") == "global"
    assert router.route_query("List all utility and safety systems in the facility") == "global"
    assert router.route_query("Summarize the entire plant hierarchy") == "global"


def test_graphrag_engine_end_to_end(sample_mmkg):
    engine = GraphRAGEngine(sample_mmkg)

    # 1. Local component query
    resp_local = engine.query("How to isolate general13 and what is downstream?", mode="auto")
    assert isinstance(resp_local, GraphRAGResponse)
    assert resp_local.retrieval_mode == "local"
    assert len(resp_local.grounded_answer) > 0
    assert "general13" in resp_local.grounded_answer

    # 2. Global plant query
    resp_global = engine.query("Provide a plant-wide overview of all subsystems", mode="auto")
    assert isinstance(resp_global, GraphRAGResponse)
    assert resp_global.retrieval_mode == "global"
    assert len(resp_global.grounded_answer) > 0
    assert "Plant-Wide Topological Summary" in resp_global.grounded_answer
