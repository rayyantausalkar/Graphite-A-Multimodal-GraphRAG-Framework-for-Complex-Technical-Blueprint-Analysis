"""Unit tests for the Deterministic Topological Reasoning Engine."""

from pathlib import Path
import pytest
from graphite.core.parser import parse_graphml
from graphite.core.collapsing import collapse_connectors
from graphite.reasoning.engine import TopologicalReasoningEngine
from graphite.reasoning.flow import FlowTracer
from graphite.reasoning.isolation import IsolationAnalyzer
from graphite.reasoning.pathfinding import PathFinder
from graphite.reasoning.rules import BlueprintRuleChecker


@pytest.fixture
def collapsed_open100():
    file_path = Path("data/PID2Graph/Complete/PID2Graph OPEN100/0.graphml")
    if not file_path.exists():
        pytest.skip("Dataset file not available")
    raw = parse_graphml(file_path)
    return collapse_connectors(raw, remove_crossings=True)


def test_flow_tracing(collapsed_open100):
    engine = TopologicalReasoningEngine(collapsed_open100)
    
    # Pick a connected physical component
    connected_nodes = [n for n, deg in engine.graph.to_networkx().degree() if deg > 1]
    assert len(connected_nodes) > 0
    start_node = connected_nodes[0]

    # Trace unblocked flow
    result = engine.trace_flow(start_node)
    assert result.origin_node == start_node
    assert len(result.reachable_nodes) >= 2
    assert start_node in result.reachable_nodes

    # Block one of the neighbors
    nbr = list(engine.graph.to_networkx().neighbors(start_node))[0]
    result_blocked = engine.trace_flow(start_node, closed_valves={nbr})
    assert nbr in result_blocked.blocked_nodes


def test_component_isolation(collapsed_open100):
    analyzer = IsolationAnalyzer(collapsed_open100)
    connected_nodes = [n for n, deg in collapsed_open100.to_networkx().degree() if deg >= 2]
    assert len(connected_nodes) > 0
    target = connected_nodes[0]

    plan = analyzer.compute_isolation_perimeter(target)
    assert plan.target_node == target
    assert target in plan.isolated_components
    assert isinstance(plan.isolation_valves, list)


def test_pathfinding_and_bypasses(collapsed_open100):
    finder = PathFinder(collapsed_open100)
    G = collapsed_open100.to_networkx()

    # Find two connected nodes
    edges = list(G.edges())
    assert len(edges) > 0
    u, v = edges[0]

    path_res = finder.find_shortest_path(u, v)
    assert path_res is not None
    assert path_res.source == u
    assert path_res.target == v
    assert path_res.hops >= 1
    assert path_res.total_length > 0.0

    # Test cycle detection
    cycles = finder.find_all_cycles()
    assert isinstance(cycles, list)


def test_rule_checker(collapsed_open100):
    checker = BlueprintRuleChecker(collapsed_open100)
    report = checker.run_all_checks()

    assert report.total_components_checked == len(collapsed_open100.get_physical_nodes())
    assert isinstance(report.anomalies, list)
    assert isinstance(report.passed_rules, list)


def test_master_engine_k_hop(collapsed_open100):
    engine = TopologicalReasoningEngine(collapsed_open100)
    sample_id = list(collapsed_open100.nodes.keys())[0]

    context = engine.get_k_hop_context(sample_id, k=2)
    assert context["center_component"] == sample_id
    assert context["k_hops"] == 2
    assert "nodes" in context
    assert "edges" in context
