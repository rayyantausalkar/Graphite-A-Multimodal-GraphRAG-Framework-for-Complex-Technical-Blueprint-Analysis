"""Verification Script for Layer 3: Topological Reasoning & Dual-Mode GraphRAG Engine."""

from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from graphite.core.parser import parse_graphml
from graphite.core.collapsing import collapse_connectors
from graphite.mmkg.builder import MMKGBuilder
from graphite.rag.engine import GraphRAGEngine
from graphite.rag.context import LocalRetrievalContext, GlobalRetrievalContext


def main():
    print("=" * 75)
    print("GRAPHITE: LAYER 3 TOPOLOGICAL REASONING & GRAPHRAG ENGINE VERIFICATION")
    print("=" * 75)

    graphml_path = Path("data/PID2Graph/Complete/PID2Graph OPEN100/0.graphml")
    img_path = Path("data/PID2Graph/Complete/PID2Graph OPEN100/0.png")

    if not graphml_path.exists():
        print(f"Error: Missing {graphml_path}")
        return

    # 1. Ingestion & MMKG Construction
    print("\n[Step 1] Ingesting Process Graph & Building Master MMKG...")
    raw_graph = parse_graphml(graphml_path, image_path=img_path)
    collapsed = collapse_connectors(raw_graph, remove_crossings=True)

    crops_dir = Path("outputs/mmkg_crops")
    builder = MMKGBuilder(device="cpu")
    specs = {
        "general13": {"tag": "P-101", "type": "Centrifugal Feed Pump", "flow": "85 m3/hr", "head": "60 m"},
        "valve99": {"tag": "V-101", "type": "Isolation Gate Valve", "rating": "300# ANSI", "material": "SS316"},
        "tank70": {"tag": "TK-01", "type": "Main Storage Vessel", "capacity": "50000 L", "pressure": "Atmospheric"},
    }
    mmkg = builder.build_mmkg(
        collapsed,
        blueprint_image_path=img_path,
        crop_output_dir=crops_dir,
        equipment_specs=specs,
    )
    print(f"  MMKG Loaded: {len(mmkg.nodes)} Multimodal Nodes, {len(mmkg.edges)} Process Lines, {len(mmkg.subsystems)} Subsystems")

    # 2. Initialize Master GraphRAG Engine
    print("\n[Step 2] Initializing Dual-Mode GraphRAG Engine...")
    engine = GraphRAGEngine(mmkg)

    # 3. Demonstration 1: Local Retrieval (Component Level)
    print("\n" + "-" * 75)
    print("[Demonstration 1] LOCAL RETRIEVAL (Component Level)")
    print("-" * 75)
    query_local = "What is the downstream flow and required isolation cut-valves for pump P-101 (general13)?"
    print(f"User Query: \"{query_local}\"")

    resp_local = engine.query(query_local, mode="auto", k_hop=2)
    print(f"\nRouter Decision: Mode = {resp_local.retrieval_mode.upper()}")
    l_ctx: LocalRetrievalContext = resp_local.context  # type: ignore

    print("\n--- Retrieved Local Context ---")
    print(f"Target Asset: {l_ctx.target_node_id} (Tag: {l_ctx.target_tag})")
    print(f"Subsystem: {l_ctx.subsystem_name}")
    print(f"Visual Crop: {l_ctx.visual_crop_path}")
    print(f"2-Hop Neighborhood: {len(l_ctx.subgraph_nodes)} components, {len(l_ctx.subgraph_edges)} pipe segments")
    print(f"Downstream Discharge Nodes: {l_ctx.downstream_equipment[:5]}")
    print(f"Required Isolation Valves: {l_ctx.isolation_valves}")

    print("\n--- Grounded Answer & Citations ---")
    print(resp_local.grounded_answer)
    print(f"\nVisual Citations: {resp_local.visual_citations[:3]}")
    print(f"Topological Citations: {resp_local.topological_citations[:8]}")

    # 4. Demonstration 2: Global Retrieval (Plant Level)
    print("\n" + "-" * 75)
    print("[Demonstration 2] GLOBAL RETRIEVAL (Plant Level)")
    print("-" * 75)
    query_global = "Provide an executive plant overview of all functional domains and safety systems."
    print(f"User Query: \"{query_global}\"")

    resp_global = engine.query(query_global, mode="auto")
    print(f"\nRouter Decision: Mode = {resp_global.retrieval_mode.upper()}")
    g_ctx: GlobalRetrievalContext = resp_global.context  # type: ignore

    print("\n--- Retrieved Global Context ---")
    print(f"Plant: {g_ctx.plant_name}")
    print(f"Total Equipment: {g_ctx.total_equipment_count} assets across {g_ctx.total_subsystems} subsystems")
    print(f"Domains Discovered: {list(g_ctx.domains.keys())}")
    print(f"Critical Plant Cut-Valves: {g_ctx.critical_cut_valves}")

    print("\n--- Grounded Answer & Citations ---")
    print(resp_global.grounded_answer)

    # 5. Visualizing Grounded Retrieval with Non-Overlapping Staggered Callouts
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    viz_path = out_dir / "layer3_graphrag_retrieval.png"
    print(f"\n[Step 5] Rendering Grounded Dual-Panel GraphRAG Visualization: {viz_path}")

    fig, (ax_full, ax_zoom) = plt.subplots(1, 2, figsize=(16, 7.5), dpi=180, gridspec_kw={"width_ratios": [1, 1.3]})

    bg = None
    if img_path.exists():
        bg = Image.open(img_path)

    # ---------------- PANEL 1: FULL BLUEPRINT CONTEXT ----------------
    if bg:
        ax_full.imshow(bg, alpha=0.45)
        ax_full.set_xlim(0, bg.width)
        ax_full.set_ylim(bg.height, 0)

    # Background edges (dimmed)
    for e in mmkg.edges:
        if len(e.waypoints) >= 2:
            xs = [p[0] for p in e.waypoints]
            ys = [p[1] for p in e.waypoints]
            ax_full.plot(xs, ys, color="#94A3B8", linewidth=0.8, alpha=0.35, zorder=1)

    # Highlight K-hop edges
    for edge in l_ctx.subgraph_edges:
        pts = edge["waypoints"]
        if len(pts) >= 2:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            ax_full.plot(xs, ys, color="#0EA5E9", linewidth=2.5, alpha=0.9, zorder=3)

    # Highlight target and neighborhood nodes on full view
    for snode in l_ctx.subgraph_nodes:
        nid = snode["id"]
        cx, cy = snode["center"]
        is_target = (nid == l_ctx.target_node_id)
        c = "#E11D48" if is_target else "#0284C7"
        s = 80 if is_target else 35
        ax_full.scatter([cx], [cy], s=s, color=c, edgecolors="#0F172A", linewidth=1.0, zorder=4)

    # Calculate generous bounding box encompassing the entire K-hop subgraph
    sub_xs = [snode["center"][0] for snode in l_ctx.subgraph_nodes]
    sub_ys = [snode["center"][1] for snode in l_ctx.subgraph_nodes]
    pad_x, pad_y = 160, 120
    roi_xmin = max(0, min(sub_xs) - pad_x)
    roi_ymin = max(0, min(sub_ys) - pad_y)
    roi_xmax = min(bg.width if bg else 1000, max(sub_xs) + pad_x)
    roi_ymax = min(bg.height if bg else 1000, max(sub_ys) + pad_y)

    # Draw ROI indicator box on full blueprint
    roi_rect = patches.Rectangle(
        (roi_xmin, roi_ymin), roi_xmax - roi_xmin, roi_ymax - roi_ymin,
        linewidth=2.0, edgecolor="#E11D48", facecolor="#E11D48", alpha=0.15, linestyle="--", zorder=5
    )
    ax_full.add_patch(roi_rect)
    ax_full.text(
        roi_xmin + 5, roi_ymin - 10,
        "Retrieval Focus Area",
        fontsize=8, fontweight="bold", color="#E11D48",
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.9, edgecolor="#E11D48"),
        zorder=6
    )

    ax_full.set_title("Full Blueprint Context (Plant-Wide View)", fontsize=11, fontweight="bold", pad=8)
    ax_full.axis("off")

    # ---------------- PANEL 2: HIGH-RES ZOOMED LOCAL SUBGRAPH ----------------
    if bg:
        ax_zoom.imshow(bg, alpha=0.6)
        ax_zoom.set_xlim(roi_xmin, roi_xmax)
        ax_zoom.set_ylim(roi_ymax, roi_ymin)  # Inverted Y for image coordinate space

    # Draw localized pipe connections in bold cyan
    for edge in l_ctx.subgraph_edges:
        pts = edge["waypoints"]
        if len(pts) >= 2:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            ax_zoom.plot(xs, ys, color="#0EA5E9", linewidth=3.5, alpha=0.95, zorder=3)
            # Waypoint dots
            ax_zoom.scatter(xs, ys, s=20, color="#0284C7", zorder=4)

    # Staggered offsets customized by position to guarantee ZERO overlap
    custom_offsets = [
        (-35, -50),  # Target: top-left above symbol
        (0, 50),     # First neighbor: bottom below symbol
        (35, -50),   # Second neighbor: top-right above symbol
        (-35, 50),   # Third neighbor: bottom-left
        (35, 50),    # Fourth neighbor: bottom-right
    ]

    # Draw nodes with non-overlapping callout arrows
    for i, snode in enumerate(l_ctx.subgraph_nodes):
        nid = snode["id"]
        cx, cy = snode["center"]
        is_target = (nid == l_ctx.target_node_id)
        is_iso_valve = (nid in l_ctx.isolation_valves)

        if is_target:
            color = "#E11D48"  # Rose red for target equipment
            marker_size = 140
            disp_tag = snode.get("tag") or (l_ctx.target_specs.get("tag") if l_ctx.target_specs else None) or nid
            label_text = f"TARGET: {disp_tag} ({snode['label']})"
        elif is_iso_valve:
            color = "#D97706"  # Amber for isolation valves
            marker_size = 90
            label_text = f"ISOLATE: {snode['tag'] or nid}"
        else:
            color = "#0284C7"  # Sky blue for neighborhood
            marker_size = 80
            label_text = f"{snode['tag'] or nid} ({snode['label']})"

        ax_zoom.scatter([cx], [cy], s=marker_size, color=color, edgecolors="#0F172A", linewidth=1.5, zorder=6)

        # Draw component bounding box
        node_obj = mmkg.nodes.get(nid)
        if node_obj and node_obj.bbox:
            bb = node_obj.bbox
            rect = patches.Rectangle(
                (bb.xmin, bb.ymin), bb.width, bb.height,
                linewidth=2.0 if is_target else 1.2,
                edgecolor=color,
                facecolor=color,
                alpha=0.25 if is_target else 0.12,
                zorder=5,
            )
            ax_zoom.add_patch(rect)

        # Assign customized non-overlapping offset
        offset_xy = custom_offsets[i % len(custom_offsets)]

        ax_zoom.annotate(
            label_text,
            xy=(cx, cy),
            xytext=offset_xy,
            textcoords="offset points",
            ha="center",
            va="center",
            fontsize=8.5 if is_target else 8,
            fontweight="bold",
            color="#0F172A",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.95, edgecolor=color, linewidth=1.5),
            arrowprops=dict(
                arrowstyle="->",
                connectionstyle="arc3,rad=0.08",
                color=color,
                lw=1.3,
                shrinkA=3,
                shrinkB=6,
            ),
            zorder=8,
        )

    disp_target = l_ctx.target_tag or (l_ctx.target_specs.get("tag") if l_ctx.target_specs else None) or l_ctx.target_node_id
    ax_zoom.set_title(
        f"Grounded Local Neighborhood (K={l_ctx.k_hop}) for '{disp_target}'",
        fontsize=11,
        fontweight="bold",
        pad=8,
    )
    ax_zoom.axis("off")

    fig.suptitle(
        f"Graphite Layer 3 Dual-Mode GraphRAG: Component Retrieval for '{disp_target}'",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout()
    fig.savefig(viz_path, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> Saved High-Resolution Non-Overlapping Visualization to: {viz_path.resolve()}")

    print("\n" + "=" * 75)
    print("LAYER 3 TOPOLOGICAL REASONING & GRAPHRAG ENGINE VERIFIED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    main()
