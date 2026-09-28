"""Patch-based tiling and coordinate projection engine for high-resolution blueprints."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

from graphite.core.models import BlueprintGraph, BoundingBox, ComponentNode, PipeEdge


class BlueprintPatch(BaseModel):
    """An individual image tile extracted from a master high-resolution blueprint."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    patch_id: int
    x_offset: int
    y_offset: int
    width: int
    height: int
    image_path: Optional[str] = None

    def local_to_global(self, local_x: float, local_y: float) -> Tuple[float, float]:
        """Convert patch-local coordinate to master blueprint coordinate."""
        return (local_x + self.x_offset, local_y + self.y_offset)

    def global_to_local(self, global_x: float, global_y: float) -> Tuple[float, float]:
        """Convert master blueprint coordinate to patch-local coordinate."""
        return (global_x - self.x_offset, global_y - self.y_offset)

    def project_bbox_to_global(self, bbox: BoundingBox) -> BoundingBox:
        """Project a patch-local bounding box to global coordinates."""
        return BoundingBox(
            xmin=bbox.xmin + self.x_offset,
            ymin=bbox.ymin + self.y_offset,
            xmax=bbox.xmax + self.x_offset,
            ymax=bbox.ymax + self.y_offset,
        )


class TilingEngine:
    """Handles high-resolution blueprint tiling, coordinate projection, and patch stitching."""

    def __init__(
        self,
        patch_size: Tuple[int, int] = (1500, 1500),
        overlap: float = 0.5,
    ):
        """Args:

        patch_size: (width, height) of each patch in pixels.
        overlap: Fraction of overlap between adjacent patches (default 0.5 = 50% overlap).
        """
        self.patch_width, self.patch_height = patch_size
        self.overlap = overlap
        self.stride_x = int(self.patch_width * (1.0 - overlap))
        self.stride_y = int(self.patch_height * (1.0 - overlap))

    def slice_image(
        self,
        image_input: Union[str, Path, Image.Image],
        output_dir: Optional[Union[str, Path]] = None,
    ) -> List[BlueprintPatch]:
        """Slice a massive blueprint (4K-12K) into overlapping tiles with tracked offsets."""
        if isinstance(image_input, (str, Path)):
            pil_img = Image.open(str(image_input))
            source_path = str(image_input)
        else:
            pil_img = image_input
            source_path = None

        img_w, img_h = pil_img.size
        patches: List[BlueprintPatch] = []

        if output_dir:
            out_p = Path(output_dir)
            out_p.mkdir(parents=True, exist_ok=True)

        patch_idx = 0
        y_shifts = list(range(0, max(1, img_h - self.patch_height + 1), self.stride_y))
        if not y_shifts or y_shifts[-1] + self.patch_height < img_h:
            y_shifts.append(max(0, img_h - self.patch_height))

        x_shifts = list(range(0, max(1, img_w - self.patch_width + 1), self.stride_x))
        if not x_shifts or x_shifts[-1] + self.patch_width < img_w:
            x_shifts.append(max(0, img_w - self.patch_width))

        for x in sorted(list(set(x_shifts))):
            for y in sorted(list(set(y_shifts))):
                box = (x, y, min(img_w, x + self.patch_width), min(img_h, y + self.patch_height))
                tile = pil_img.crop(box)
                saved_path = None

                if output_dir:
                    saved_path = str(out_p / f"{patch_idx}.png")
                    tile.save(saved_path)

                patch = BlueprintPatch(
                    patch_id=patch_idx,
                    x_offset=x,
                    y_offset=y,
                    width=tile.width,
                    height=tile.height,
                    image_path=saved_path,
                )
                patches.append(patch)
                patch_idx += 1

        return patches

    def stitch_patch_graphs(
        self,
        patch_graphs: List[BlueprintGraph],
        patches: List[BlueprintPatch],
        iou_threshold: float = 0.5,
        master_name: str = "master_stitched_blueprint",
    ) -> BlueprintGraph:
        """Stitch subgraphs detected in individual patches back into a unified master blueprint graph.

        Resolves boundary overlap duplicates via spatial IoU clustering (Non-Maximum Suppression).
        """
        assert len(patch_graphs) == len(patches), "Mismatch between patch graphs and patch metadata"

        # 1. Project all nodes and edges to global coordinates
        projected_nodes: List[Tuple[ComponentNode, int]] = []  # (node, patch_id)
        raw_edges_with_hops: List[Dict] = []

        for p_graph, patch in zip(patch_graphs, patches):
            for node in p_graph.nodes.values():
                global_bbox = patch.project_bbox_to_global(node.bbox) if node.bbox else None
                global_center = patch.local_to_global(*node.get_center())

                proj_node = ComponentNode(
                    id=f"p{patch.patch_id}_{node.id}",
                    label=node.label,
                    bbox=global_bbox,
                    center=global_center,
                    attributes={**node.attributes, "origin_patch": patch.patch_id},
                )
                projected_nodes.append((proj_node, patch.patch_id))

            for edge in p_graph.edges:
                global_waypoints = [
                    patch.local_to_global(pt[0], pt[1]) for pt in edge.waypoints
                ]
                raw_edges_with_hops.append({
                    "src": f"p{patch.patch_id}_{edge.source}",
                    "tgt": f"p{patch.patch_id}_{edge.target}",
                    "label": edge.edge_label,
                    "waypoints": global_waypoints,
                    "length": edge.length,
                    "hops": edge.hops,
                })

        # 2. Deduplicate boundary nodes using IoU clustering
        merged_nodes: Dict[str, ComponentNode] = {}
        node_remap: Dict[str, str] = {}  # old_id -> canonical_id
        used: set = set()

        for i, (node_a, patch_a) in enumerate(projected_nodes):
            if node_a.id in used:
                continue

            canonical_id = node_a.id
            cluster = [node_a]
            used.add(node_a.id)

            for j in range(i + 1, len(projected_nodes)):
                node_b, patch_b = projected_nodes[j]
                if node_b.id in used:
                    continue
                if node_a.label == node_b.label and node_a.bbox and node_b.bbox:
                    if node_a.bbox.iou(node_b.bbox) >= iou_threshold:
                        cluster.append(node_b)
                        used.add(node_b.id)
                        node_remap[node_b.id] = canonical_id

            node_remap[canonical_id] = canonical_id

            # Merge bounding box of the cluster
            if len(cluster) == 1:
                merged_nodes[canonical_id] = node_a
            else:
                avg_xmin = sum(n.bbox.xmin for n in cluster) / len(cluster)
                avg_ymin = sum(n.bbox.ymin for n in cluster) / len(cluster)
                avg_xmax = sum(n.bbox.xmax for n in cluster) / len(cluster)
                avg_ymax = sum(n.bbox.ymax for n in cluster) / len(cluster)
                merged_bbox = BoundingBox(xmin=avg_xmin, ymin=avg_ymin, xmax=avg_xmax, ymax=avg_ymax)
                merged_nodes[canonical_id] = ComponentNode(
                    id=canonical_id,
                    label=node_a.label,
                    bbox=merged_bbox,
                    center=merged_bbox.center,
                    attributes={**node_a.attributes, "merged_cluster_size": len(cluster)},
                )

        # 3. Re-link edges using remapped canonical node IDs
        stitched_edges: Dict[Tuple[str, str], PipeEdge] = {}
        for e in raw_edges_with_hops:
            u_canon = node_remap.get(e["src"])
            v_canon = node_remap.get(e["tgt"])

            if u_canon and v_canon and u_canon != v_canon:
                key = tuple(sorted([u_canon, v_canon]))
                if key not in stitched_edges:
                    stitched_edges[key] = PipeEdge(
                        source=key[0],
                        target=key[1],
                        edge_label=e["label"],
                        waypoints=e["waypoints"],
                        length=e["length"],
                        hops=e["hops"],
                    )

        # 4. Return stitched master BlueprintGraph
        master_graph = BlueprintGraph(
            name=master_name,
            is_collapsed=False,
            metadata={"num_patches_stitched": len(patches)},
        )
        for n in merged_nodes.values():
            master_graph.add_node(n)
        for edge in stitched_edges.values():
            master_graph.add_edge(edge)

        return master_graph
