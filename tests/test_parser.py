from pathlib import Path
import pytest
from graphite.core.parser import parse_graphml
from graphite.core.models import BlueprintGraph, BoundingBox


def test_bounding_box_geometry():
    box1 = BoundingBox(xmin=10, ymin=10, xmax=30, ymax=30)
    box2 = BoundingBox(xmin=20, ymin=20, xmax=40, ymax=40)

    assert box1.width == 20.0
    assert box1.height == 20.0
    assert box1.area == 400.0
    assert box1.center == (20.0, 20.0)

    # IoU: intersection is 10x10 = 100, union is 400 + 400 - 100 = 700
    iou = box1.iou(box2)
    assert abs(iou - 100.0 / 700.0) < 1e-4

    assert box1.contains_point(15, 15) is True
    assert box1.contains_point(35, 35) is False


def test_parse_open100_graphml():
    file_path = Path("data/PID2Graph/Complete/PID2Graph OPEN100/0.graphml")
    if not file_path.exists():
        pytest.skip("Dataset file not available")

    graph = parse_graphml(file_path)
    assert isinstance(graph, BlueprintGraph)
    assert len(graph.nodes) == 437
    assert len(graph.edges) == 433

    physical = graph.get_physical_nodes()
    routing = graph.get_routing_nodes()

    assert len(physical) == 137
    assert len(routing) == 437 - 137 - 4  # 4 background nodes

    # Verify NetworkX conversion
    nx_graph = graph.to_networkx()
    assert nx_graph.number_of_nodes() == 437
    assert nx_graph.number_of_edges() == 433
