"""Multimodal Knowledge Graph (MMKG) data structures for blueprints."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import networkx as nx
import numpy as np
from pydantic import BaseModel, Field

from graphite.core.models import BlueprintGraph, BoundingBox, ComponentNode, PipeEdge


class MultimodalNode(BaseModel):
    """An equipment node enriched with visual crops, technical specs, and multimodal embeddings."""
    id: str
    label: str
    tag: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    center: Optional[Tuple[float, float]] = None
    visual_crop_path: Optional[str] = None
    visual_embedding: Optional[List[float]] = None
    text_embedding: Optional[List[float]] = None
    multimodal_embedding: Optional[List[float]] = None
    subsystem_id: Optional[int] = None
    subsystem_name: Optional[str] = None
    specs: Dict[str, Any] = Field(default_factory=dict)
    attributes: Dict[str, Any] = Field(default_factory=dict)

    def get_center(self) -> Tuple[float, float]:
        if self.center is not None:
            return self.center
        if self.bbox is not None:
            return self.bbox.center
        return (0.0, 0.0)

    def get_display_name(self) -> str:
        return self.tag if self.tag else self.id


class MultimodalKnowledgeGraph(BaseModel):
    """The master Multimodal Knowledge Graph (MMKG) uniting vision, topology, and specs."""
    name: str = "master_mmkg"
    image_path: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    nodes: Dict[str, MultimodalNode] = Field(default_factory=dict)
    edges: List[PipeEdge] = Field(default_factory=list)
    subsystems: Dict[int, Dict[str, Any]] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_node(self, node: MultimodalNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: PipeEdge) -> None:
        self.edges.append(edge)

    def get_node_by_tag(self, tag: str) -> Optional[MultimodalNode]:
        for n in self.nodes.values():
            if n.tag == tag or n.id == tag:
                return n
        return None

    def search_by_embedding(
        self,
        query_vector: Union[List[float], np.ndarray],
        top_k: int = 5,
        modality: str = "multimodal",
    ) -> List[Tuple[MultimodalNode, float]]:
        """Search equipment by cosine similarity in multimodal or visual/text embedding space."""
        q_vec = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []
        q_vec = q_vec / q_norm

        results = []
        for node in self.nodes.values():
            vec = None
            if modality == "visual":
                vec = node.visual_embedding
            elif modality == "text":
                vec = node.text_embedding
            else:
                vec = node.multimodal_embedding

            if vec is not None and len(vec) == len(q_vec):
                v_arr = np.array(vec, dtype=np.float32)
                v_norm = np.linalg.norm(v_arr)
                if v_norm > 0:
                    sim = float(np.dot(q_vec, v_arr / v_norm))
                    results.append((node, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def search_by_text(
        self,
        query: str,
        text_encoder: Optional[Any] = None,
        top_k: int = 5,
        modality: str = "multimodal",
    ) -> List[Tuple[MultimodalNode, float]]:
        """Search equipment using natural language queries (e.g. 'Centrifugal pump', 'Gate valve 300#')."""
        if text_encoder is None:
            from graphite.mmkg.embeddings import TextEncoder
            text_encoder = TextEncoder()

        q_vec = text_encoder.encode_text(query)
        return self.search_by_embedding(q_vec, top_k=top_k, modality=modality)

    def search_by_image(
        self,
        image_or_crop: Any,
        visual_encoder: Optional[Any] = None,
        top_k: int = 5,
    ) -> List[Tuple[MultimodalNode, float]]:
        """Search equipment visually using an image crop (find similar symbols on blueprint)."""
        from PIL import Image
        if visual_encoder is None:
            from graphite.mmkg.embeddings import VisualEncoder
            visual_encoder = VisualEncoder()

        if isinstance(image_or_crop, (str, Path)):
            pil_crop = Image.open(str(image_or_crop))
        else:
            pil_crop = image_or_crop

        q_vec = visual_encoder.encode_crop(pil_crop)
        return self.search_by_embedding(q_vec, top_k=top_k, modality="visual")

    def get_subsystem_hierarchy(self) -> Dict[str, Any]:
        """Export plant-wide hierarchical subsystem tree for Layer 3 Global Retrieval.
        
        Returns:
            Dict structuring Plant -> Domain Categories (Process, Utility, Storage, Safety) -> Subsystems.
        """
        domains: Dict[str, List[Dict[str, Any]]] = {
            "Process": [],
            "Utility": [],
            "Storage & Separation": [],
            "Safety & Control": [],
        }

        for sub_id, sub_info in self.subsystems.items():
            category = sub_info.get("domain_category", "Process")
            if category not in domains:
                domains[category] = []

            domains[category].append({
                "subsystem_id": sub_id,
                "name": sub_info.get("name", f"Subsystem-{sub_id}"),
                "primary_function": sub_info.get("primary_function", "Process Unit"),
                "component_count": len(sub_info.get("component_ids", [])),
                "equipment_breakdown": sub_info.get("equipment_count_by_type", {}),
                "boundary_valves": sub_info.get("boundary_valves", []),
                "internal_pipe_length": sub_info.get("internal_pipe_length", 0.0),
            })

        return {
            "plant_name": self.name,
            "total_subsystems": len(self.subsystems),
            "domains": domains,
        }

    def to_networkx(self) -> nx.Graph:
        """Convert MMKG to a NetworkX Graph carrying all multimodal attributes."""
        G = nx.Graph()
        G.graph["name"] = self.name
        G.graph["image_path"] = self.image_path

        for nid, node in self.nodes.items():
            cx, cy = node.get_center()
            G.add_node(
                nid,
                label=node.label,
                tag=node.tag,
                cx=cx,
                cy=cy,
                subsystem_id=node.subsystem_id,
                subsystem_name=node.subsystem_name,
                bbox=node.bbox.to_tuple() if node.bbox else None,
                visual_crop_path=node.visual_crop_path,
                has_multimodal_embedding=node.multimodal_embedding is not None,
                specs=node.specs,
                **node.attributes,
            )

        for edge in self.edges:
            G.add_edge(
                edge.source,
                edge.target,
                edge_label=edge.edge_label,
                hops=edge.hops,
                length=edge.length,
                waypoints=edge.waypoints,
                intermediate_nodes=edge.intermediate_nodes,
                **edge.attributes,
            )

        return G

    def to_graphml_graph(self) -> nx.Graph:
        """Convert MMKG to a strictly scalar-attribute GraphML-serializable NetworkX graph."""
        G = nx.Graph()
        G.graph["name"] = str(self.name)
        if self.image_path:
            G.graph["image_path"] = str(self.image_path)

        for nid, node in self.nodes.items():
            cx, cy = node.get_center()
            attrs = {
                "label": str(node.label),
                "tag": str(node.tag or ""),
                "cx": float(cx),
                "cy": float(cy),
                "subsystem_id": int(node.subsystem_id) if node.subsystem_id is not None else -1,
                "subsystem_name": str(node.subsystem_name or ""),
                "visual_crop_path": str(node.visual_crop_path or ""),
                "has_multimodal_embedding": bool(node.multimodal_embedding is not None),
                "specs_json": json.dumps(node.specs),
            }
            if node.bbox:
                attrs["bbox_xmin"] = float(node.bbox.xmin)
                attrs["bbox_ymin"] = float(node.bbox.ymin)
                attrs["bbox_xmax"] = float(node.bbox.xmax)
                attrs["bbox_ymax"] = float(node.bbox.ymax)
            G.add_node(str(nid), **attrs)

        for edge in self.edges:
            attrs = {
                "edge_label": str(edge.edge_label or "pipe"),
                "hops": int(edge.hops),
                "length": float(edge.length),
                "waypoints_json": json.dumps(edge.waypoints),
                "intermediate_nodes_json": json.dumps(edge.intermediate_nodes),
            }
            G.add_edge(str(edge.source), str(edge.target), **attrs)

        return G

    def save_graphml(self, output_path: Union[str, Path]) -> None:
        """Export MMKG to standard GraphML XML format."""
        p = Path(output_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        G = self.to_graphml_graph()
        nx.write_graphml(G, str(p))

    def save_json(self, output_path: Union[str, Path]) -> None:
        """Persist MMKG structure and metadata to JSON."""
        p = Path(output_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load_json(cls, input_path: Union[str, Path]) -> "MultimodalKnowledgeGraph":
        """Load MMKG from JSON."""
        p = Path(input_path).resolve()
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
