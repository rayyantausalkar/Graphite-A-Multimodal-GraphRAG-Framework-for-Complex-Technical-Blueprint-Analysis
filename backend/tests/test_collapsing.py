from pathlib import Path
import pytest
from graphite.core.parser import parse_graphml
from graphite.core.collapsing import collapse_connectors


def test_collapse_open100_diagram():
    file_path = Path("data/PID2Graph/Complete/PID2Graph OPEN100/0.graphml")
    if not file_path.exists():
        pytest.skip("Dataset file not available")

    raw_graph = parse_graphml(file_path)
    collapsed = collapse_connectors(raw_graph, remove_crossings=True)

    assert collapsed.is_collapsed is True
    # In OPEN100 0.graphml, physical nodes = 137, collapsed edges = 60
    assert len(collapsed.nodes) == 137
    assert len(collapsed.edges) == 60

    # Ensure no connector or crossing remains
    for node in collapsed.nodes.values():
        assert node.label not in ("connector", "crossing", "background")

    # Check edges have valid waypoints and positive length
    for edge in collapsed.edges:
        assert len(edge.waypoints) >= 2
        assert edge.length > 0.0
        assert edge.hops >= 1

    summary = collapsed.summary()
    assert summary["physical_nodes"] == 137
    assert summary["total_edges"] == 60


def test_collapse_dataset_pid_diagram():
    file_path = Path("data/PID2Graph/Complete/Dataset PID/0.graphml")
    if not file_path.exists():
        pytest.skip("Dataset file not available")

    raw_graph = parse_graphml(file_path)
    collapsed = collapse_connectors(raw_graph, remove_crossings=True)

    assert collapsed.is_collapsed is True
    # Ensure all nodes are physical
    for node in collapsed.nodes.values():
        assert node.is_physical is True
