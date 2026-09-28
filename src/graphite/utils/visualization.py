"""High-resolution blueprint and graph visualization utilities."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image

from graphite.core.models import BlueprintGraph


CATEGORY_COLORS: Dict[str, str] = {
    "valve": "#E63946",            # Crimson Red
    "instrumentation": "#1D3557",  # Royal Navy Blue
    "general": "#2A9D8F",          # Emerald Green
    "tank": "#6A0572",             # Deep Purple
    "arrow": "#F4A261",            # Sandy Orange
    "inlet/outlet": "#0077B6",     # Electric Teal
    "connector": "#A8DADC",        # Soft Cyan
    "crossing": "#E9C46A",         # Gold
    "default": "#457B9D",          # Steel Blue
}


def visualize_blueprint(
    graph: BlueprintGraph,
    output_path: Optional[Union[str, Path]] = None,
    show_boxes: bool = True,
    show_labels: bool = False,
    show_edges: bool = True,
    highlight_nodes: Optional[List[str]] = None,
    highlight_path: Optional[List[str]] = None,
    figsize: Tuple[int, int] = (16, 12),
    dpi: int = 200,
    background_alpha: float = 0.5,
) -> plt.Figure:
    """Render the blueprint with overlaid nodes, bounding boxes, and pipe routes.

    Args:
        graph: BlueprintGraph (raw or collapsed).
        output_path: Optional file path to save the rendering (e.g. .png).
        show_boxes: Whether to draw component bounding boxes.
        show_labels: Whether to render text ID labels next to components.
        show_edges: Whether to render pipe connection lines.
        highlight_nodes: List of component IDs to emphasize in bright gold.
        highlight_path: Ordered list of component IDs defining a traced path to glow.
        figsize: Matplotlib figure size in inches.
        dpi: Output resolution.
        background_alpha: Opacity of the background blueprint diagram image.

    Returns:
        The matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    # 1. Draw Background Blueprint Image if available
    img_loaded = False
    img_w, img_h = 1000, 1000
    if graph.image_path and Path(graph.image_path).exists():
        try:
            bg_img = Image.open(graph.image_path)
            img_w, img_h = bg_img.size
            ax.imshow(bg_img, alpha=background_alpha)
            img_loaded = True
        except Exception:
            pass

    if not img_loaded:
        # Determine canvas size from node bounding boxes
        all_xs = [n.get_center()[0] for n in graph.nodes.values()]
        all_ys = [n.get_center()[1] for n in graph.nodes.values()]
        max_x = max(all_xs) if all_xs else 1000
        max_y = max(all_ys) if all_ys else 1000
        img_w = int(max_x * 1.05)
        img_h = int(max_y * 1.05)
        ax.set_facecolor("#F8F9FA")

    ax.set_xlim(0, img_w)
    ax.set_ylim(img_h, 0)  # Invert Y for image coordinate system (0,0 at top-left)

    highlight_set = set(highlight_nodes or [])

    # 2. Draw Edges / Pipe Routes
    if show_edges:
        for edge in graph.edges:
            pts = edge.waypoints
            if len(pts) < 2:
                p1 = graph.nodes[edge.source].get_center() if edge.source in graph.nodes else None
                p2 = graph.nodes[edge.target].get_center() if edge.target in graph.nodes else None
                if p1 and p2:
                    pts = [p1, p2]

            if len(pts) >= 2:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                linestyle = "-" if edge.edge_label == "solid" else "--"
                ax.plot(
                    xs,
                    ys,
                    color="#2B2D42",
                    linestyle=linestyle,
                    linewidth=1.2,
                    alpha=0.7,
                    zorder=2,
                )

    # 3. Draw Highlighted Path if specified
    if highlight_path and len(highlight_path) >= 2:
        for i in range(len(highlight_path) - 1):
            u, v = highlight_path[i], highlight_path[i + 1]
            p1 = graph.nodes[u].get_center() if u in graph.nodes else None
            p2 = graph.nodes[v].get_center() if v in graph.nodes else None
            if p1 and p2:
                # Find matching edge waypoints if available
                matching_waypoints = [p1, p2]
                for edge in graph.edges:
                    if {edge.source, edge.target} == {u, v} and len(edge.waypoints) >= 2:
                        matching_waypoints = edge.waypoints
                        break
                xs = [p[0] for p in matching_waypoints]
                ys = [p[1] for p in matching_waypoints]
                # Glow effect
                ax.plot(xs, ys, color="#FFB703", linewidth=4.0, alpha=0.9, zorder=5)
                ax.plot(xs, ys, color="#FB8500", linewidth=2.0, alpha=1.0, zorder=6)

    # 4. Draw Component Nodes and Bounding Boxes
    for nid, node in graph.nodes.items():
        cx, cy = node.get_center()
        is_highlighted = nid in highlight_set
        color = "#FFD166" if is_highlighted else CATEGORY_COLORS.get(node.label, CATEGORY_COLORS["default"])

        # Bounding box
        if show_boxes and node.bbox:
            bb = node.bbox
            rect = patches.Rectangle(
                (bb.xmin, bb.ymin),
                bb.width,
                bb.height,
                linewidth=2.0 if is_highlighted else 1.2,
                edgecolor=color,
                facecolor=color,
                alpha=0.4 if is_highlighted else 0.2,
                zorder=3,
            )
            ax.add_patch(rect)

        # Center point marker
        marker_size = 40 if is_highlighted else 20
        ax.scatter([cx], [cy], s=marker_size, color=color, edgecolors="#14213D", linewidth=1.0, zorder=4)

        # Text label
        if show_labels or is_highlighted:
            ax.text(
                cx + 6,
                cy - 6,
                nid,
                fontsize=7 if not is_highlighted else 9,
                fontweight="bold" if is_highlighted else "normal",
                color="#000814",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8, edgecolor="none"),
                zorder=7,
            )

    title_status = "Collapsed Process Flow Graph" if graph.is_collapsed else "Raw Digitized Blueprint Graph"
    ax.set_title(
        f"Graphite | {graph.name} ({title_status}) — {len(graph.nodes)} Nodes, {len(graph.edges)} Edges",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )
    ax.axis("off")
    plt.tight_layout()

    if output_path is not None:
        p_out = Path(output_path).resolve()
        p_out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(p_out), dpi=dpi, bbox_inches="tight")

    return fig
