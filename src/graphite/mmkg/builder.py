"""MMKG Builder: Constructs full Multimodal Knowledge Graphs uniting vision, topology, and specs."""

from pathlib import Path
from typing import Dict, List, Optional, Union
from PIL import Image

from graphite.core.models import BlueprintGraph
from graphite.mmkg.representation import MultimodalNode, MultimodalKnowledgeGraph
from graphite.mmkg.embeddings import VisualEncoder, TextEncoder, MultimodalFusionEngine
from graphite.mmkg.subsystems import SubsystemPartitioner


class MMKGBuilder:
    """Constructs the Graphite Multimodal Knowledge Graph from process graphs and raster blueprints."""

    def __init__(
        self,
        enable_visual_embeddings: bool = True,
        enable_text_embeddings: bool = True,
        enable_subsystems: bool = True,
        device: Optional[str] = None,
    ):
        self.visual_encoder = VisualEncoder(device=device) if enable_visual_embeddings else None
        self.text_encoder = TextEncoder() if enable_text_embeddings else None
        self.fusion_engine = MultimodalFusionEngine()
        self.partitioner = SubsystemPartitioner() if enable_subsystems else None

    def build_mmkg(
        self,
        graph: BlueprintGraph,
        blueprint_image_path: Optional[Union[str, Path]] = None,
        crop_output_dir: Optional[Union[str, Path]] = None,
        equipment_specs: Optional[Dict[str, Dict]] = None,
    ) -> MultimodalKnowledgeGraph:
        """Construct enriched MultimodalKnowledgeGraph.

        Args:
            graph: Collapsed BlueprintGraph.
            blueprint_image_path: Path to the full blueprint image (PNG/JPG).
            crop_output_dir: Folder to save cropped symbol PNG images.
            equipment_specs: Optional dict mapping node ID or tag to data sheet specs.

        Returns:
            MultimodalKnowledgeGraph with visual crops, fused embeddings, and subsystems.
        """
        img_p = blueprint_image_path or graph.image_path
        pil_img = None
        if img_p and Path(img_p).exists():
            pil_img = Image.open(str(img_p))

        crops_dir = Path(crop_output_dir) if crop_output_dir else None
        if crops_dir:
            crops_dir.mkdir(parents=True, exist_ok=True)

        specs_lookup = equipment_specs or {}

        # 1. Subsystem Partitioning
        subsystems_map = {}
        node_to_sub = {}
        if self.partitioner is not None:
            subsystems_map = self.partitioner.partition_graph(graph)
            for sub_id, sub_comm in subsystems_map.items():
                for nid in sub_comm.component_ids:
                    node_to_sub[nid] = (sub_id, sub_comm.name)

        mmkg = MultimodalKnowledgeGraph(
            name=f"{graph.name}_mmkg",
            image_path=str(img_p) if img_p else None,
            image_width=pil_img.width if pil_img else graph.image_width,
            image_height=pil_img.height if pil_img else graph.image_height,
            subsystems={k: v.model_dump() for k, v in subsystems_map.items()},
            metadata={**graph.metadata, "is_multimodal": True},
        )

        # 2. Process Nodes: Visual Crops + Embeddings + Specs
        for nid, node in graph.nodes.items():
            tag = node.attributes.get("tag")
            specs = specs_lookup.get(tag, specs_lookup.get(nid, {}))

            # Visual Embedding & Crop
            vis_vec = None
            crop_file = None
            if pil_img and node.bbox and self.visual_encoder:
                safe_nid = nid.replace("/", "_").replace("\\", "_")
                save_f = crops_dir / f"{safe_nid}.png" if crops_dir else None
                try:
                    vis_vec, crop_file = self.visual_encoder.crop_and_encode(
                        pil_img, node.bbox, save_path=save_f
                    )
                except Exception:
                    pass

            # Text Specification Embedding
            text_vec = None
            if self.text_encoder:
                desc_parts = [f"{tag or nid}", f"{node.label}"]
                for k, v in specs.items():
                    desc_parts.append(f"{k}: {v}")
                text_desc = ", ".join(desc_parts)
                text_vec = self.text_encoder.encode_text(text_desc)

            # Fused Multimodal Embedding
            mm_vec = self.fusion_engine.fuse(vis_vec, text_vec)

            sub_info = node_to_sub.get(nid, (None, None))

            mm_node = MultimodalNode(
                id=nid,
                label=node.label,
                tag=tag,
                bbox=node.bbox,
                center=node.get_center(),
                visual_crop_path=crop_file,
                visual_embedding=vis_vec,
                text_embedding=text_vec,
                multimodal_embedding=mm_vec,
                subsystem_id=sub_info[0],
                subsystem_name=sub_info[1],
                specs=specs,
                attributes=node.attributes,
            )
            mmkg.add_node(mm_node)

        # 3. Add Edges
        for edge in graph.edges:
            mmkg.add_edge(edge)

        return mmkg
