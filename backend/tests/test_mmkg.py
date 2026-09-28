"""Unit tests for Layer 2: Multimodal Knowledge Graph (MMKG)."""

from pathlib import Path
from PIL import Image
import numpy as np
import pytest

from graphite.core.parser import parse_graphml
from graphite.core.collapsing import collapse_connectors
from graphite.mmkg.representation import MultimodalNode, MultimodalKnowledgeGraph
from graphite.mmkg.embeddings import VisualEncoder, TextEncoder, MultimodalFusionEngine
from graphite.mmkg.subsystems import SubsystemPartitioner
from graphite.mmkg.builder import MMKGBuilder


def test_visual_and_text_encoders():
    vis_enc = VisualEncoder(device="cpu")
    txt_enc = TextEncoder(embedding_dim=512)
    fusion = MultimodalFusionEngine(visual_weight=0.5)

    # 1. Test visual encoding
    crop = Image.new("RGB", (64, 64), color="blue")
    v_vec = vis_enc.encode_crop(crop)
    assert len(v_vec) == 512
    assert abs(np.linalg.norm(v_vec) - 1.0) < 1e-3

    # 2. Test text encoding
    t_vec = txt_enc.encode_text("P-101 Centrifugal Pump, Flow: 50 m3/hr, Pressure: 10 bar")
    assert len(t_vec) == 512
    assert abs(np.linalg.norm(t_vec) - 1.0) < 1e-3

    # 3. Test multimodal fusion
    f_vec = fusion.fuse(v_vec, t_vec)
    assert len(f_vec) == 512
    assert abs(np.linalg.norm(f_vec) - 1.0) < 1e-3


def test_subsystem_partitioning():
    file_path = Path("data/PID2Graph/Complete/PID2Graph OPEN100/0.graphml")
    if not file_path.exists():
        pytest.skip("Dataset file not available")

    raw = parse_graphml(file_path)
    collapsed = collapse_connectors(raw)

    partitioner = SubsystemPartitioner(seed=42)
    subsystems = partitioner.partition_graph(collapsed)

    assert len(subsystems) > 0
    # Every subsystem should have an ID, name, component list, and type count
    for sub in subsystems.values():
        assert sub.subsystem_id >= 0
        assert len(sub.name) > 0
        assert len(sub.component_ids) > 0
        assert isinstance(sub.equipment_count_by_type, dict)


def test_mmkg_builder_and_vector_search(tmp_path):
    file_path = Path("data/PID2Graph/Complete/PID2Graph OPEN100/0.graphml")
    if not file_path.exists():
        pytest.skip("Dataset file not available")

    raw = parse_graphml(file_path)
    collapsed = collapse_connectors(raw)

    builder = MMKGBuilder(device="cpu")
    sample_specs = {
        "valve99": {"tag": "V-101", "pressure_rating": "150#", "type": "gate"},
        "general13": {"tag": "P-101", "type": "centrifugal_pump", "flow": "80 m3/h"},
    }

    mmkg = builder.build_mmkg(
        collapsed,
        crop_output_dir=tmp_path / "crops",
        equipment_specs=sample_specs,
    )

    assert len(mmkg.nodes) == len(collapsed.nodes)
    assert len(mmkg.edges) == len(collapsed.edges)
    assert len(mmkg.subsystems) > 0

    # Test vector search
    sample_node = list(mmkg.nodes.values())[0]
    assert sample_node.multimodal_embedding is not None

    top_matches = mmkg.search_by_embedding(sample_node.multimodal_embedding, top_k=3)
    assert len(top_matches) > 0
    # The top match should be the node itself with similarity ~ 1.0
    assert top_matches[0][0].id == sample_node.id
    assert abs(top_matches[0][1] - 1.0) < 1e-3

    # Test text-based query search
    text_matches = mmkg.search_by_text("P-101 Centrifugal Feed Pump", top_k=3)
    assert len(text_matches) > 0

    # Test image-based search
    sample_crop = Image.new("RGB", (32, 32), color="red")
    img_matches = mmkg.search_by_image(sample_crop, top_k=3)
    assert len(img_matches) > 0

    # Test plant-level subsystem hierarchy
    hierarchy = mmkg.get_subsystem_hierarchy()
    assert hierarchy["total_subsystems"] == len(mmkg.subsystems)
    assert "domains" in hierarchy
    assert all(k in hierarchy["domains"] for k in ["Process", "Utility", "Storage & Separation", "Safety & Control"])

    # Test GraphML export
    graphml_out = tmp_path / "test_export.graphml"
    mmkg.save_graphml(graphml_out)
    assert graphml_out.exists()
    assert graphml_out.stat().st_size > 0

    # Test crop coordinate clamping safety on degenerate / out-of-bounds bbox
    from graphite.core.models import BoundingBox
    vis_enc = VisualEncoder(device="cpu")
    dummy_img = Image.new("RGB", (100, 100), color="white")
    # Inverted bbox outside bounds
    bad_bbox = BoundingBox(xmin=150, ymin=150, xmax=120, ymax=120)
    feat, _ = vis_enc.crop_and_encode(dummy_img, bad_bbox)
    assert len(feat) == 512

