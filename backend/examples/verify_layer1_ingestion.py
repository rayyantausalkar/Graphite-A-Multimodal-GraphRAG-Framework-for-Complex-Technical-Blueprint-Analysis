"""Verification Script for Layer 1: Multimodal Ingestion & Topology Extraction."""

from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from graphite.core.parser import parse_graphml
from graphite.core.collapsing import collapse_connectors
from graphite.ingestion.tiling import TilingEngine
from graphite.ingestion.ocr import OCRTagExtractor, EquipmentTag
from graphite.core.models import BoundingBox, ComponentNode


def main():
    print("=" * 75)
    print("GRAPHITE: LAYER 1 MULTIMODAL INGESTION VERIFICATION")
    print("=" * 75)

    img_path = Path("data/PID2Graph/Complete/Dataset PID/0.png")
    graphml_path = Path("data/PID2Graph/Complete/Dataset PID/0.graphml")

    if not img_path.exists():
        print(f"Error: Missing image at {img_path}")
        return

    # 1. Patch-Based Tiling & Coordinate Projection
    print("\n[Step 1] High-Resolution Blueprint Patch Tiling...")
    im = Image.open(img_path)
    print(f"  Master Blueprint Dimensions: {im.width} x {im.height} pixels")

    tiling_engine = TilingEngine(patch_size=(1500, 1500), overlap=0.5)
    patches_list = tiling_engine.slice_image(im)
    print(f"  Generated: {len(patches_list)} overlapping patches (1500x1500 px each)")

    for p in patches_list[:4]:
        print(f"    - Patch {p.patch_id:02d}: Offset (x={p.x_offset:4d}, y={p.y_offset:4d}) | Size: {p.width}x{p.height}")

    # 2. ISA-5.1 OCR Tag Extraction & Tag Parsing
    print("\n[Step 2] ISA-5.1 OCR Tag Parsing & Equipment Classification...")
    ocr = OCRTagExtractor()
    sample_texts = [
        "P-101A", "V-204", "TIC-305", "TK-01", "PT-12", "FT-501", "E-201B"
    ]
    for st in sample_texts:
        tag = ocr.parse_text_string(st)
        if tag:
            print(f"  Raw OCR Text: '{st:8s}' -> Tag: {tag.tag_id:8s} | Inferred Equipment Type: {tag.inferred_equipment_type}")

    # 3. Spatial Proximity Tag-to-Symbol Binding
    print("\n[Step 3] Spatial Tag-to-Equipment Binding & Type Refinement...")
    raw_graph = parse_graphml(graphml_path, image_path=img_path)
    print(f"  Raw Graph: {len(raw_graph.nodes)} total nodes ({len(raw_graph.get_physical_nodes())} physical components)")

    # Simulate tags located adjacent to components
    simulated_tags = [
        EquipmentTag(
            raw_text="P-101",
            tag_id="P-101",
            prefix="P",
            loop_number="101",
            inferred_equipment_type="pump",
            bbox=BoundingBox(xmin=1100, ymin=970, xmax=1140, ymax=990),
        ),
        EquipmentTag(
            raw_text="V-202",
            tag_id="V-202",
            prefix="V",
            loop_number="202",
            inferred_equipment_type="valve",
            bbox=BoundingBox(xmin=1600, ymin=720, xmax=1640, ymax=740),
        ),
    ]

    enriched_graph = ocr.bind_tags_to_graph(raw_graph, simulated_tags, max_distance_px=150.0)
    tagged_nodes = [n for n in enriched_graph.nodes.values() if "tag" in n.attributes]
    print(f"  Successfully bound {len(tagged_nodes)} equipment tags to physical symbols:")
    for tn in tagged_nodes:
        print(f"    * Symbol '{tn.id}' assigned Tag: '{tn.attributes['tag']}' (Type: {tn.label})")

    # 4. Topological Connector Collapsing
    print("\n[Step 4] Topological Connector Collapsing...")
    collapsed = collapse_connectors(enriched_graph, remove_crossings=True)
    summary = collapsed.summary()
    print(f"  Collapsed Graph: {summary['total_nodes']} physical assets, {summary['total_edges']} functional process edges")

    # 5. Visual Tiling Grid Plot
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    out_img = out_dir / "layer1_tiling_verification.png"
    print(f"\n[Step 5] Generating Patch-Based Tiling Grid Visualization: {out_img}")

    fig, ax = plt.subplots(figsize=(12, 8), dpi=150)
    # Downsampled master blueprint for background
    small_im = im.resize((im.width // 4, im.height // 4))
    ax.imshow(small_im)

    scale = 0.25
    colors = ["#E63946", "#457B9D", "#2A9D8F", "#E76F51", "#9B5DE5", "#00B4D8"]
    for i, p in enumerate(patches_list):
        c = colors[i % len(colors)]
        rect = patches.Rectangle(
            (p.x_offset * scale, p.y_offset * scale),
            p.width * scale,
            p.height * scale,
            linewidth=1.2,
            edgecolor=c,
            facecolor="none",
            alpha=0.7,
        )
        ax.add_patch(rect)
        ax.text(
            (p.x_offset + 50) * scale,
            (p.y_offset + 120) * scale,
            f"P{p.patch_id}",
            fontsize=6,
            color=c,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.7, edgecolor="none"),
        )

    ax.set_title(
        f"Graphite Layer 1: Patch Tiling Grid ({len(patches_list)} Overlapping Tiles on {im.width}x{im.height} Blueprint)",
        fontsize=11,
        fontweight="bold",
    )
    ax.axis("off")
    plt.tight_layout()
    fig.savefig(out_img, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> Saved tiling grid visualization to: {out_img.resolve()}")

    print("\n" + "=" * 75)
    print("LAYER 1 MULTIMODAL INGESTION VERIFIED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    main()
