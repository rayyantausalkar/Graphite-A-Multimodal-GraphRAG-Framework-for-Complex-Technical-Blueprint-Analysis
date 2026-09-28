"""Verification Script for Layer 2: The Graphite Multimodal Knowledge Graph (MMKG)."""

from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from graphite.core.parser import parse_graphml
from graphite.core.collapsing import collapse_connectors
from graphite.mmkg.builder import MMKGBuilder


def main():
    print("=" * 75)
    print("GRAPHITE: LAYER 2 MULTIMODAL KNOWLEDGE GRAPH (MMKG) VERIFICATION")
    print("=" * 75)

    graphml_path = Path("data/PID2Graph/Complete/PID2Graph OPEN100/0.graphml")
    img_path = Path("data/PID2Graph/Complete/PID2Graph OPEN100/0.png")

    if not graphml_path.exists():
        print(f"Error: Missing {graphml_path}")
        return

    # 1. Parse and collapse
    raw_graph = parse_graphml(graphml_path, image_path=img_path)
    collapsed = collapse_connectors(raw_graph, remove_crossings=True)
    print(f"\n[Step 1] Ingested Collapsed Graph: {len(collapsed.nodes)} physical nodes, {len(collapsed.edges)} pipe lines")

    # 2. Build the Multimodal Knowledge Graph
    print("\n[Step 2] Building MMKG: Extracting Visual Crops, Computing Embeddings & Partitioning Subsystems...")
    crops_dir = Path("outputs/mmkg_crops")
    builder = MMKGBuilder(device="cpu")

    # Sample equipment specifications simulating data sheets
    sample_specs = {
        "general13": {"tag": "P-101", "type": "Centrifugal Feed Pump", "flow": "85 m3/hr", "head": "60 m"},
        "valve99": {"tag": "V-101", "type": "Isolation Gate Valve", "rating": "300# ANSI", "material": "SS316"},
        "tank70": {"tag": "TK-01", "type": "Main Storage Vessel", "capacity": "50000 L", "pressure": "Atmospheric"},
    }

    mmkg = builder.build_mmkg(
        collapsed,
        blueprint_image_path=img_path,
        crop_output_dir=crops_dir,
        equipment_specs=sample_specs,
    )

    print(f"  MMKG Generated: {len(mmkg.nodes)} Multimodal Nodes, {len(mmkg.edges)} Process Edges")
    saved_crops = list(crops_dir.glob("*.png"))
    print(f"  Visual Symbol Crops Saved: {len(saved_crops)} crops in '{crops_dir}'")

    # 3. Inspect Subsystems Partitioning
    print("\n[Step 3] Hierarchical Subsystem Partitioning (Louvain Modularity)...")
    print(f"  Total Functional Subsystems Discovered: {len(mmkg.subsystems)}")
    for sub_id, sub_info in list(mmkg.subsystems.items())[:4]:
        print(f"\n  * {sub_info['name']}")
        print(f"    - Equipment Count: {len(sub_info['component_ids'])} assets ({sub_info['equipment_count_by_type']})")
        print(f"    - Boundary Isolation Valves: {sub_info['boundary_valves']}")
        print(f"    - Internal Pipe Length: {sub_info['internal_pipe_length']:.1f} pixels")

    # 4. Multi-Modal Vector & Natural Language Similarity Search
    print("\n[Step 4] Multimodal Vector Similarity Search...")
    sample_node = mmkg.nodes["general13"]
    print(f"  Querying nearest equipment to: '{sample_node.id}' (Tag: {sample_node.tag}, Type: {sample_node.label})")

    top_matches = mmkg.search_by_embedding(sample_node.multimodal_embedding, top_k=4)
    for rank, (matched_node, sim) in enumerate(top_matches):
        print(f"    Rank {rank+1}: Node '{matched_node.id}' (Type: {matched_node.label}) | Cosine Similarity: {sim:.4f}")

    print("\n  Natural Language Query: 'Centrifugal Pump Feed'")
    text_matches = mmkg.search_by_text("Centrifugal Pump Feed", top_k=3)
    for rank, (matched_node, sim) in enumerate(text_matches):
        print(f"    Rank {rank+1}: Node '{matched_node.id}' (Tag: {matched_node.tag}, Type: {matched_node.label}) | Sim: {sim:.4f}")

    # Inspect Plant-Level Hierarchy Tree
    print("\n[Step 5] Plant-Level Subsystem Hierarchy Tree (Global Retrieval Structure):")
    hierarchy = mmkg.get_subsystem_hierarchy()
    for domain, subs in hierarchy["domains"].items():
        if subs:
            print(f"  * Domain [{domain}]: {len(subs)} subsystems")
            for s in subs[:2]:
                print(f"      - {s['name']} ({s['component_count']} components)")

    # 6. Visualizing Partitioned Subsystems
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    out_img = out_dir / "layer2_subsystems_verification.png"
    print(f"\n[Step 6] Generating Subsystem-Colored Blueprint Rendering: {out_img}")

    fig, ax = plt.subplots(figsize=(14, 10), dpi=150)
    if img_path.exists():
        bg = Image.open(img_path)
        ax.imshow(bg, alpha=0.35)
        ax.set_xlim(0, bg.width)
        ax.set_ylim(bg.height, 0)

    # Subsystem palette
    palette = ["#E63946", "#457B9D", "#2A9D8F", "#E76F51", "#9B5DE5", "#F4A261", "#00B4D8", "#8338EC"]

    # Draw edges
    for e in mmkg.edges:
        if len(e.waypoints) >= 2:
            xs = [p[0] for p in e.waypoints]
            ys = [p[1] for p in e.waypoints]
            ax.plot(xs, ys, color="#2B2D42", linewidth=1.2, alpha=0.6, zorder=2)

    # Draw nodes color-coded by subsystem
    for nid, node in mmkg.nodes.items():
        cx, cy = node.get_center()
        sub_id = node.subsystem_id if node.subsystem_id is not None else 0
        c = palette[sub_id % len(palette)]

        if node.bbox:
            bb = node.bbox
            rect = patches.Rectangle(
                (bb.xmin, bb.ymin), bb.width, bb.height,
                linewidth=1.5, edgecolor=c, facecolor=c, alpha=0.3, zorder=3
            )
            ax.add_patch(rect)

        ax.scatter([cx], [cy], s=30, color=c, edgecolors="#14213D", linewidth=0.8, zorder=4)

    ax.set_title(
        f"Graphite Layer 2 MMKG: Hierarchical Subsystem Partitioning ({len(mmkg.subsystems)} Subsystems)",
        fontsize=12, fontweight="bold", pad=12
    )
    ax.axis("off")
    plt.tight_layout()
    fig.savefig(out_img, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> Saved subsystem visualization to: {out_img.resolve()}")

    # 7. Save JSON & GraphML
    json_path = out_dir / "master_mmkg_0.json"
    mmkg.save_json(json_path)
    print(f"  -> Exported MMKG structure & vector metadata to: {json_path.resolve()}")

    graphml_path = out_dir / "master_mmkg_0.graphml"
    mmkg.save_graphml(graphml_path)
    print(f"  -> Exported MMKG GraphML network to: {graphml_path.resolve()}")

    print("\n" + "=" * 75)
    print("LAYER 2 MMKG VERIFICATION COMPLETED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    main()
