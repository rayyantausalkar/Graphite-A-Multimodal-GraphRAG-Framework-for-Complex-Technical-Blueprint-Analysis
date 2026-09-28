"""Multimodal Ingestion Pipeline (Layer 1 of Graphite Architecture).

Coordinates:
1. Patch-Based Tiling & Coordinate Projection (handling 4K-8K blueprints).
2. Symbol Detection & OCR Tag Extraction (binding P-101, V-202 to equipment).
3. Line Style Classification (Process solid, Utility dashed, Signal dotted).
4. Topological Connector Collapsing into clean process flow graphs.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from PIL import Image

from graphite.core.models import BlueprintGraph
from graphite.core.collapsing import collapse_connectors
from graphite.core.parser import parse_graphml
from graphite.ingestion.tiling import TilingEngine, BlueprintPatch
from graphite.ingestion.ocr import OCRTagExtractor, EquipmentTag


class MultimodalIngestionPipeline:
    """Master orchestrator for Layer 1 ingestion and topology extraction."""

    def __init__(
        self,
        patch_size: Tuple[int, int] = (1500, 1500),
        overlap: float = 0.5,
        enable_ocr: bool = True,
    ):
        self.tiling_engine = TilingEngine(patch_size=patch_size, overlap=overlap)
        self.ocr_extractor = OCRTagExtractor() if enable_ocr else None

    def ingest_blueprint(
        self,
        blueprint_image_path: Union[str, Path],
        graphml_path: Optional[Union[str, Path]] = None,
        extract_ocr_tags: bool = True,
    ) -> Tuple[BlueprintGraph, BlueprintGraph, List[BlueprintPatch]]:
        """Run the complete Layer 1 pipeline on a blueprint.

        Args:
            blueprint_image_path: Path to the high-resolution blueprint (PNG/JPG).
            graphml_path: Path to the digitized GraphML file (if available).
            extract_ocr_tags: Whether to run OCR tag extraction.

        Returns:
            Tuple of:
            - raw_stitched_graph: Master uncollapsed graph in global coordinates.
            - collapsed_process_graph: Final semantic process graph after connector collapsing.
            - patches: List of generated BlueprintPatch objects.
        """
        img_path = Path(blueprint_image_path).resolve()
        if not img_path.exists():
            raise FileNotFoundError(f"Blueprint image not found: {img_path}")

        # 1. Patch-Based Tiling & Coordinate Projection
        patches = self.tiling_engine.slice_image(img_path)

        # 2. Parse master or patch graphs
        if graphml_path is not None:
            raw_graph = parse_graphml(graphml_path, image_path=img_path)
        else:
            raw_graph = BlueprintGraph(name=img_path.stem, image_path=str(img_path))

        # 3. OCR Tag Extraction & Spatial Binding
        if extract_ocr_tags and self.ocr_extractor is not None:
            try:
                tags = self.ocr_extractor.extract_tags_from_image(img_path)
                if tags:
                    raw_graph = self.ocr_extractor.bind_tags_to_graph(raw_graph, tags)
            except Exception as e:
                print(f"OCR note: {e}")

        # 4. Topological Connector Collapsing
        collapsed_graph = collapse_connectors(raw_graph, remove_crossings=True)

        return raw_graph, collapsed_graph, patches
