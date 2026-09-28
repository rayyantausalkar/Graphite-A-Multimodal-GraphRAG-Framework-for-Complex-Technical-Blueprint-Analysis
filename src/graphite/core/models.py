"""Data models for technical blueprints and engineering graphs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple
import math
import networkx as nx
from pydantic import BaseModel, Field
from shapely.geometry import Polygon, box as shapely_box


# Canonical physical component classes vs routing / auxiliary classes
ROUTING_CLASSES: Set[str] = {"connector", "crossing"}
IGNORED_CLASSES: Set[str] = {"background"}


class BoundingBox(BaseModel):
    """Bounding box coordinates for a blueprint component."""
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    @property
    def width(self) -> float:
        return max(0.0, self.xmax - self.xmin)

    @property
    def height(self) -> float:
        return max(0.0, self.ymax - self.ymin)

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.xmin + self.xmax) / 2.0, (self.ymin + self.ymax) / 2.0)

    @property
    def area(self) -> float:
        return self.width * self.height

    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.xmin, self.ymin, self.xmax, self.ymax)

    def to_shapely(self) -> Polygon:
        return shapely_box(self.xmin, self.ymin, self.xmax, self.ymax)

    def iou(self, other: BoundingBox) -> float:
        """Compute Intersection over Union (IoU) with another bounding box."""
        inter_xmin = max(self.xmin, other.xmin)
        inter_ymin = max(self.ymin, other.ymin)
        inter_xmax = min(self.xmax, other.xmax)
        inter_ymax = min(self.ymax, other.ymax)

        inter_w = max(0.0, inter_xmax - inter_xmin)
        inter_h = max(0.0, inter_ymax - inter_ymin)
        inter_area = inter_w * inter_h

        if inter_area <= 0:
            return 0.0

        union_area = self.area + other.area - inter_area
        return inter_area / union_area if union_area > 0 else 0.0

    def contains_point(self, x: float, y: float) -> bool:
        return self.xmin <= x <= self.xmax and self.ymin <= y <= self.ymax


class ComponentNode(BaseModel):
    """A node in the engineering blueprint graph."""
    id: str
    label: str
    bbox: Optional[BoundingBox] = None
    center: Optional[Tuple[float, float]] = None
    subsystem: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_physical(self) -> bool:
        """Returns True if the component is physical equipment, False if routing/auxiliary."""
        return self.label not in ROUTING_CLASSES and self.label not in IGNORED_CLASSES

    @property
    def is_routing(self) -> bool:
        return self.label in ROUTING_CLASSES

    def get_center(self) -> Tuple[float, float]:
        if self.center is not None:
            return self.center
        if self.bbox is not None:
            return self.bbox.center
        return (0.0, 0.0)


class PipeEdge(BaseModel):
    """A connection between two blueprint components."""
    source: str
    target: str
    edge_label: str = "solid"
    waypoints: List[Tuple[float, float]] = Field(default_factory=list)
    intermediate_nodes: List[str] = Field(default_factory=list)
    hops: int = 1
    length: float = 0.0
    attributes: Dict[str, Any] = Field(default_factory=dict)

    @property
    def key(self) -> Tuple[str, str]:
        """Undirected edge key sorted alphabetically."""
        return tuple(sorted([self.source, self.target]))  # type: ignore


class BlueprintGraph(BaseModel):
    """Full representation of a blueprint diagram graph."""
    name: str = "blueprint"
    image_path: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    is_collapsed: bool = False
    nodes: Dict[str, ComponentNode] = Field(default_factory=dict)
    edges: List[PipeEdge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_node(self, node: ComponentNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: PipeEdge) -> None:
        self.edges.append(edge)

    def get_physical_nodes(self) -> Dict[str, ComponentNode]:
        """Return only physical components (excluding connector, crossing, background)."""
        return {nid: n for nid, n in self.nodes.items() if n.is_physical}

    def get_routing_nodes(self) -> Dict[str, ComponentNode]:
        """Return auxiliary routing nodes (connector, crossing)."""
        return {nid: n for nid, n in self.nodes.items() if n.is_routing}

    def to_networkx(self, directed: bool = False) -> nx.Graph:
        """Convert to a NetworkX Graph or DiGraph for topological algorithms."""
        G = nx.DiGraph() if directed else nx.Graph()
        G.graph["name"] = self.name
        G.graph["is_collapsed"] = self.is_collapsed
        G.graph["image_path"] = self.image_path

        for nid, node in self.nodes.items():
            cx, cy = node.get_center()
            G.add_node(
                nid,
                label=node.label,
                is_physical=node.is_physical,
                cx=cx,
                cy=cy,
                subsystem=node.subsystem,
                bbox=node.bbox.to_tuple() if node.bbox else None,
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

    @classmethod
    def from_networkx(cls, G: nx.Graph, name: str = "blueprint", is_collapsed: bool = False) -> BlueprintGraph:
        """Construct BlueprintGraph from a NetworkX graph."""
        bg = cls(
            name=name,
            image_path=G.graph.get("image_path"),
            is_collapsed=is_collapsed,
        )
        for nid, data in G.nodes(data=True):
            lbl = data.get("label", "unknown")
            bbox_t = data.get("bbox")
            bbox = BoundingBox(xmin=bbox_t[0], ymin=bbox_t[1], xmax=bbox_t[2], ymax=bbox_t[3]) if bbox_t else None
            cx = data.get("cx")
            cy = data.get("cy")
            center = (cx, cy) if cx is not None and cy is not None else None
            node = ComponentNode(
                id=str(nid),
                label=lbl,
                bbox=bbox,
                center=center,
                subsystem=data.get("subsystem"),
            )
            bg.add_node(node)

        for u, v, data in G.edges(data=True):
            edge = PipeEdge(
                source=str(u),
                target=str(v),
                edge_label=data.get("edge_label", "solid"),
                hops=data.get("hops", 1),
                length=data.get("length", 0.0),
                waypoints=data.get("waypoints", []),
                intermediate_nodes=data.get("intermediate_nodes", []),
            )
            bg.add_edge(edge)

        return bg

    def summary(self) -> Dict[str, Any]:
        """Return graph statistics."""
        labels = {}
        for n in self.nodes.values():
            labels[n.label] = labels.get(n.label, 0) + 1

        edge_types = {}
        for e in self.edges:
            edge_types[e.edge_label] = edge_types.get(e.edge_label, 0) + 1

        G_nx = self.to_networkx()
        num_cc = nx.number_connected_components(G_nx) if len(G_nx) > 0 else 0

        return {
            "name": self.name,
            "total_nodes": len(self.nodes),
            "physical_nodes": len(self.get_physical_nodes()),
            "routing_nodes": len(self.get_routing_nodes()),
            "total_edges": len(self.edges),
            "connected_components": num_cc,
            "is_collapsed": self.is_collapsed,
            "node_distribution": labels,
            "edge_distribution": edge_types,
        }
