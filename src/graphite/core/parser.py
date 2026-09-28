"""Parser for technical blueprint GraphML representations."""

from pathlib import Path
from typing import Dict, Optional, Union
import xml.etree.ElementTree as ET
from PIL import Image

from graphite.core.models import BlueprintGraph, BoundingBox, ComponentNode, PipeEdge


def parse_graphml(
    file_path: Union[str, Path],
    image_path: Optional[Union[str, Path]] = None,
) -> BlueprintGraph:
    """Parse a GraphML file into a typed BlueprintGraph.

    Supports PID2Graph, OPEN100, and Synthetic benchmark formats.
    Auto-detects associated image if not explicitly provided.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"GraphML file not found: {path}")

    # Auto-resolve matching image file (.png, .jpg, .jpeg)
    if image_path is None:
        for ext in [".png", ".jpg", ".jpeg"]:
            cand = path.with_suffix(ext)
            if cand.exists():
                image_path = cand
                break

    img_w, img_h = None, None
    resolved_img_path = None
    if image_path is not None:
        p_img = Path(image_path).resolve()
        if p_img.exists():
            resolved_img_path = str(p_img)
            try:
                with Image.open(p_img) as img:
                    img_w, img_h = img.size
            except Exception:
                pass

    tree = ET.parse(str(path))
    root = tree.getroot()
    ns = {"g": "http://graphml.graphdrawing.org/xmlns"}

    # Dynamically extract key attribute mappings from XML header
    node_key_map: Dict[str, str] = {}
    edge_key_map: Dict[str, str] = {}
    for k_elem in root.findall(".//g:key", ns):
        kid = k_elem.attrib.get("id", "")
        kfor = k_elem.attrib.get("for", "")
        kname = k_elem.attrib.get("attr.name", "")
        if kfor == "node":
            node_key_map[kid] = kname.strip().lower()
        elif kfor == "edge":
            edge_key_map[kid] = kname.strip().lower()

    graph = BlueprintGraph(
        name=path.stem,
        image_path=resolved_img_path,
        image_width=img_w,
        image_height=img_h,
        is_collapsed=False,
    )

    # 1. Parse Nodes
    for node_elem in root.findall(".//g:node", ns):
        nid = node_elem.attrib["id"]
        label = "unknown"
        coords: Dict[str, float] = {}
        attributes: Dict[str, str] = {}

        for d_elem in node_elem.findall("g:data", ns):
            k = d_elem.attrib.get("key", "")
            val = d_elem.text or ""
            attr_name = node_key_map.get(k, k)

            if attr_name == "label":
                label = val.strip().lower()
            elif attr_name in ("xmin", "ymin", "xmax", "ymax"):
                try:
                    coords[attr_name] = float(val)
                except ValueError:
                    pass
            else:
                attributes[attr_name] = val

        bbox = None
        center = None
        if all(k in coords for k in ("xmin", "ymin", "xmax", "ymax")):
            xmin = min(coords["xmin"], coords["xmax"])
            xmax = max(coords["xmin"], coords["xmax"])
            ymin = min(coords["ymin"], coords["ymax"])
            ymax = max(coords["ymin"], coords["ymax"])
            bbox = BoundingBox(xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax)
            center = bbox.center

        comp_node = ComponentNode(
            id=nid,
            label=label,
            bbox=bbox,
            center=center,
            attributes=attributes,
        )
        graph.add_node(comp_node)

    # 2. Parse Edges
    for edge_elem in root.findall(".//g:edge", ns):
        src = edge_elem.attrib["source"]
        tgt = edge_elem.attrib["target"]
        edge_label = "solid"
        attributes = {}

        for d_elem in edge_elem.findall("g:data", ns):
            k = d_elem.attrib.get("key", "")
            val = d_elem.text or ""
            attr_name = edge_key_map.get(k, k)
            if attr_name == "edge_label":
                edge_label = val.strip().lower()
            else:
                attributes[attr_name] = val

        # Compute initial segment length if nodes exist
        p1 = graph.nodes[src].get_center() if src in graph.nodes else (0.0, 0.0)
        p2 = graph.nodes[tgt].get_center() if tgt in graph.nodes else (0.0, 0.0)
        import math
        dist = math.hypot(p1[0] - p2[0], p1[1] - p2[1])

        edge = PipeEdge(
            source=src,
            target=tgt,
            edge_label=edge_label,
            waypoints=[p1, p2],
            hops=1,
            length=dist,
            attributes=attributes,
        )
        graph.add_edge(edge)

    return graph
