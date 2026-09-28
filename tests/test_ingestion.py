"""Unit tests for Layer 1 Multimodal Ingestion Pipeline."""

from pathlib import Path
from PIL import Image
import pytest

from graphite.core.models import BlueprintGraph, BoundingBox, ComponentNode, PipeEdge
from graphite.ingestion.tiling import TilingEngine, BlueprintPatch
from graphite.ingestion.ocr import OCRTagExtractor, EquipmentTag
from graphite.ingestion.pipeline import MultimodalIngestionPipeline


def test_tiling_engine_slicing():
    # Create synthetic 3000x2000 test image
    img = Image.new("RGB", (3000, 2000), color="white")
    engine = TilingEngine(patch_size=(1000, 1000), overlap=0.5)

    patches = engine.slice_image(img)
    assert len(patches) > 0

    # Verify coordinate projection roundtrip
    patch0 = patches[0]
    local_pt = (150.0, 200.0)
    global_pt = patch0.local_to_global(*local_pt)
    assert patch0.global_to_local(*global_pt) == local_pt

    # Test BBox projection
    local_bbox = BoundingBox(xmin=10, ymin=10, xmax=50, ymax=50)
    global_bbox = patch0.project_bbox_to_global(local_bbox)
    assert global_bbox.xmin == local_bbox.xmin + patch0.x_offset
    assert global_bbox.ymin == local_bbox.ymin + patch0.y_offset


def test_patch_stitching_with_nms():
    engine = TilingEngine(patch_size=(1000, 1000), overlap=0.5)

    # Simulate 2 overlapping patches with duplicate detection of a valve
    patch_a = BlueprintPatch(patch_id=0, x_offset=0, y_offset=0, width=1000, height=1000)
    patch_b = BlueprintPatch(patch_id=1, x_offset=500, y_offset=0, width=1000, height=1000)

    # In patch A: valve at global (600, 300) -> local (600, 300)
    graph_a = BlueprintGraph(name="patch_a")
    graph_a.add_node(ComponentNode(
        id="v1",
        label="valve",
        bbox=BoundingBox(xmin=590, ymin=290, xmax=610, ymax=310),
    ))

    # In patch B: same valve at global (600, 300) -> local (100, 300)
    graph_b = BlueprintGraph(name="patch_b")
    graph_b.add_node(ComponentNode(
        id="v1_dup",
        label="valve",
        bbox=BoundingBox(xmin=92, ymin=292, xmax=112, ymax=312),
    ))

    master = engine.stitch_patch_graphs([graph_a, graph_b], [patch_a, patch_b], iou_threshold=0.3)
    # The two overlapping detections should be merged into 1 canonical node!
    assert len(master.nodes) == 1


def test_ocr_tag_parsing():
    extractor = OCRTagExtractor()

    # Test standard equipment tags
    tag_pump = extractor.parse_text_string("P-101A")
    assert tag_pump is not None
    assert tag_pump.tag_id == "P-101A"
    assert tag_pump.prefix == "P"
    assert tag_pump.inferred_equipment_type == "pump"

    tag_valve = extractor.parse_text_string("XV-204")
    assert tag_valve is not None
    assert tag_valve.inferred_equipment_type == "isolation_valve"

    tag_inst = extractor.parse_text_string("TIC-305")
    assert tag_inst is not None
    assert tag_inst.inferred_equipment_type == "temperature_indicator_controller"


def test_spatial_tag_binding_and_type_refinement():
    extractor = OCRTagExtractor()

    # Create graph with generic equipment
    graph = BlueprintGraph(name="test_plant")
    node = ComponentNode(
        id="comp1",
        label="general",  # Generic detector label
        bbox=BoundingBox(xmin=100, ymin=100, xmax=150, ymax=150),
    )
    graph.add_node(node)

    # Tag positioned adjacent to the equipment
    tag = EquipmentTag(
        raw_text="P-101",
        tag_id="P-101",
        prefix="P",
        loop_number="101",
        inferred_equipment_type="pump",
        bbox=BoundingBox(xmin=155, ymin=100, xmax=190, ymax=120),
    )

    enriched = extractor.bind_tags_to_graph(graph, [tag], max_distance_px=80.0)
    updated_node = enriched.nodes["comp1"]

    assert updated_node.attributes.get("tag") == "P-101"
    # Generic "general" label should be refined to "pump"!
    assert updated_node.label == "pump"


def test_optimal_bipartite_tag_matching():
    """Verify that global distance sorting prevents greedy order-dependent misassignments."""
    extractor = OCRTagExtractor()
    graph = BlueprintGraph(name="test_bipartite")

    # Node A is at (100, 100), Node B is at (120, 100)
    node_a = ComponentNode(id="node_a", label="valve", bbox=BoundingBox(xmin=95, ymin=95, xmax=105, ymax=105))
    node_b = ComponentNode(id="node_b", label="pump", bbox=BoundingBox(xmin=115, ymin=95, xmax=125, ymax=105))
    graph.add_node(node_a)
    graph.add_node(node_b)

    # Tag 1 is at (119, 100) -> 1px from Node B, 19px from Node A
    tag1 = EquipmentTag(
        raw_text="P-101", tag_id="P-101", prefix="P", loop_number="101",
        inferred_equipment_type="pump", bbox=BoundingBox(xmin=118, ymin=99, xmax=120, ymax=101)
    )
    # Tag 2 is at (98, 100) -> 2px from Node A, 22px from Node B
    tag2 = EquipmentTag(
        raw_text="V-101", tag_id="V-101", prefix="V", loop_number="101",
        inferred_equipment_type="valve", bbox=BoundingBox(xmin=97, ymin=99, xmax=99, ymax=101)
    )

    enriched = extractor.bind_tags_to_graph(graph, [tag1, tag2], max_distance_px=50.0)

    # Node B must get Tag 1 (closest), Node A must get Tag 2 (closest)
    assert enriched.nodes["node_b"].attributes.get("tag") == "P-101"
    assert enriched.nodes["node_a"].attributes.get("tag") == "V-101"

