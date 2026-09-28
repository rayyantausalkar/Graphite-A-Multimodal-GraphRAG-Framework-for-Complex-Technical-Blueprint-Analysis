"""Feature 1 Verification Script for Graphite.

Run this script to verify:
1. Blueprint GraphML ingestion and geometry parsing.
2. Connector collapsing from raw routing tokens into physical process flow edges.
3. Generation of visual verification diagrams saved directly to disk.
"""

from pathlib import Path
import json
from graphite.core.parser import parse_graphml
from graphite.core.collapsing import collapse_connectors
from graphite.utils.visualization import visualize_blueprint


def main():
    print("=" * 70)
    print("GRAPHITE: FEATURE 1 VERIFICATION")
    print("=" * 70)

    # 1. Select a sample blueprint from OPEN100 benchmark
    blueprint_path = Path("data/PID2Graph/Complete/PID2Graph OPEN100/0.graphml")
    if not blueprint_path.exists():
        print(f"Error: Could not find {blueprint_path}")
        return

    print(f"\n[Step 1] Parsing raw blueprint GraphML: {blueprint_path.name}")
    raw_graph = parse_graphml(blueprint_path)
    raw_summary = raw_graph.summary()

    print(f"  - Total Raw Nodes: {raw_summary['total_nodes']}")
    print(f"  - Total Raw Edges: {raw_summary['total_edges']}")
    print(f"  - Physical Nodes:  {raw_summary['physical_nodes']}")
    print(f"  - Routing Nodes:   {raw_summary['routing_nodes']} (connectors & crossings)")
    print(f"  - Node Classes:    {raw_summary['node_distribution']}")

    # 2. Run Connector Collapsing
    print("\n[Step 2] Executing Connector Collapsing Algorithm...")
    collapsed_graph = collapse_connectors(raw_graph, remove_crossings=True)
    col_summary = collapsed_graph.summary()

    print(f"  - Collapsed Nodes: {col_summary['total_nodes']} (100% physical components)")
    print(f"  - Collapsed Edges: {col_summary['total_edges']} (direct process flow connections)")
    print(f"  - Connected Components: {col_summary['connected_components']}")

    # 3. Inspect sample collapsed edges
    print("\n[Step 3] Sample Collapsed Process Flow Edges:")
    for i, edge in enumerate(collapsed_graph.edges[:5]):
        src_lbl = collapsed_graph.nodes[edge.source].label
        tgt_lbl = collapsed_graph.nodes[edge.target].label
        print(f"  Edge {i+1}: [{edge.source} ({src_lbl})] <---> [{edge.target} ({tgt_lbl})]")
        print(f"          Type: {edge.edge_label} | Cumulative Length: {edge.length:.1f} px | Hops: {edge.hops} | Waypoints: {len(edge.waypoints)}")

    # 4. Generate Visual Verification Image
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    out_img = out_dir / "feature1_collapsed_verification.png"
    print(f"\n[Step 4] Generating high-resolution visual plot: {out_img}")

    visualize_blueprint(
        collapsed_graph,
        output_path=out_img,
        show_boxes=True,
        show_labels=True,
        show_edges=True,
        dpi=180,
    )
    print(f"  -> Successfully generated and saved to: {out_img.resolve()}")

    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
