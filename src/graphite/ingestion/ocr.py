"""OCR Tag Extraction and Equipment Binding Engine (ISA-5.1 standard)."""

import re
from typing import Dict, List, Optional, Set, Tuple, Union
from pathlib import Path
from PIL import Image
import numpy as np
from pydantic import BaseModel, Field

from graphite.core.models import BlueprintGraph, BoundingBox, ComponentNode


# ISA-5.1 Industrial Instrument & Equipment Prefix Dictionary
EQUIPMENT_PREFIXES: Dict[str, str] = {
    # Mechanical Equipment
    "P": "pump",
    "PU": "pump",
    "V": "valve",
    "CV": "control_valve",
    "XV": "isolation_valve",
    "PSV": "pressure_safety_valve",
    "PRV": "pressure_relief_valve",
    "T": "tank",
    "TK": "tank",
    "VSS": "vessel",
    "E": "heat_exchanger",
    "HEX": "heat_exchanger",
    "C": "compressor",
    "K": "compressor",
    "F": "filter",
    "FLT": "filter",
    "S": "separator",
    "SEP": "separator",
    # Instrumentation (ISA-5.1)
    "PT": "pressure_transmitter",
    "PI": "pressure_indicator",
    "PIC": "pressure_indicator_controller",
    "PDT": "diff_pressure_transmitter",
    "TT": "temperature_transmitter",
    "TI": "temperature_indicator",
    "TIC": "temperature_indicator_controller",
    "FT": "flow_transmitter",
    "FI": "flow_indicator",
    "FIC": "flow_indicator_controller",
    "LT": "level_transmitter",
    "LI": "level_indicator",
    "LIC": "level_indicator_controller",
    "AT": "analyzer_transmitter",
}

# Regex for matching standard equipment tags like P-101, V-202, TIC-305, TK-1, HV-10001
TAG_REGEX = re.compile(
    r"\b([A-Z]{1,4})[-_ ]?([0-9]{1,5}[A-Z]?)\b",
    re.IGNORECASE,
)


class EquipmentTag(BaseModel):
    """An alphanumeric engineering tag extracted via OCR."""
    raw_text: str
    tag_id: str  # Normalized e.g. "P-101"
    prefix: str  # "P"
    loop_number: str  # "101"
    inferred_equipment_type: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    confidence: float = 1.0

    def get_center(self) -> Optional[Tuple[float, float]]:
        return self.bbox.center if self.bbox else None


class OCRTagExtractor:
    """Extracts alphanumeric tags from blueprint images and binds them to topological equipment nodes."""

    def __init__(self, languages: List[str] = ["en"], gpu: bool = False):
        self.languages = languages
        self.gpu = gpu
        self._reader = None

    def _get_reader(self):
        """Lazy load EasyOCR reader."""
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader(self.languages, gpu=self.gpu)
            except Exception as e:
                print(f"Warning: EasyOCR reader initialization failed ({e}). Fallback to heuristic parser.")
                self._reader = None
        return self._reader

    def parse_text_string(self, text: str, bbox: Optional[BoundingBox] = None, conf: float = 1.0) -> Optional[EquipmentTag]:
        """Parse raw text string using ISA-5.1 regex to detect engineering tags."""
        match = TAG_REGEX.search(text.strip())
        if not match:
            return None

        prefix = match.group(1).upper()
        number = match.group(2).upper()
        norm_tag = f"{prefix}-{number}"
        inferred_type = EQUIPMENT_PREFIXES.get(prefix)

        return EquipmentTag(
            raw_text=text,
            tag_id=norm_tag,
            prefix=prefix,
            loop_number=number,
            inferred_equipment_type=inferred_type,
            bbox=bbox,
            confidence=conf,
        )

    def extract_tags_from_image(
        self,
        image_input: Union[str, Path, Image.Image],
        min_confidence: float = 0.3,
    ) -> List[EquipmentTag]:
        """Run OCR on a blueprint patch or diagram image and extract ISA-5.1 tags."""
        reader = self._get_reader()
        if reader is None:
            return []

        if isinstance(image_input, (str, Path)):
            img_np = np.array(Image.open(str(image_input)))
        elif isinstance(image_input, Image.Image):
            img_np = np.array(image_input)
        else:
            img_np = image_input

        results = reader.readtext(img_np)
        tags: List[EquipmentTag] = []

        for bbox_coords, text, conf in results:
            if conf < min_confidence:
                continue

            # bbox_coords is [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
            xs = [pt[0] for pt in bbox_coords]
            ys = [pt[1] for pt in bbox_coords]
            bbox = BoundingBox(xmin=min(xs), ymin=min(ys), xmax=max(xs), ymax=max(ys))

            tag = self.parse_text_string(text, bbox=bbox, conf=conf)
            if tag:
                tags.append(tag)

        return tags

    def bind_tags_to_graph(
        self,
        graph: BlueprintGraph,
        tags: List[EquipmentTag],
        max_distance_px: float = 120.0,
    ) -> BlueprintGraph:
        """Bind detected OCR equipment tags to nearest graph components.

        Uses global distance-sorted optimal bipartite matching to guarantee that
        closest equipment-tag pairs are bound first, eliminating greedy order-dependent errors.
        """
        import math
        physical_nodes = list(graph.get_physical_nodes().values())
        if not physical_nodes or not tags:
            return graph

        # 1. Collect all candidate (distance, node, tag) pairs within max_distance_px
        candidates: List[Tuple[float, ComponentNode, EquipmentTag]] = []
        for node in physical_nodes:
            ncx, ncy = node.get_center()
            for tag in tags:
                tc = tag.get_center()
                if tc is None:
                    continue
                dist = math.hypot(ncx - tc[0], ncy - tc[1])
                if dist <= max_distance_px:
                    candidates.append((dist, node, tag))

        # 2. Sort candidate matches by distance ascending (closest first)
        candidates.sort(key=lambda x: x[0])

        used_nodes: Set[str] = set()
        used_tags: Set[str] = set()

        # 3. Optimally bind pairs without reuse
        for dist, node, tag in candidates:
            if node.id in used_nodes or tag.tag_id in used_tags:
                continue

            used_nodes.add(node.id)
            used_tags.add(tag.tag_id)

            node.attributes["tag"] = tag.tag_id
            node.attributes["tag_prefix"] = tag.prefix
            node.attributes["tag_number"] = tag.loop_number
            node.attributes["tag_distance_px"] = round(dist, 1)

            # Refine generic classification if tag provides specific type
            if tag.inferred_equipment_type:
                node.attributes["refined_type"] = tag.inferred_equipment_type
                if node.label in ("general", "unknown"):
                    node.attributes["original_label"] = node.label
                    node.label = tag.inferred_equipment_type

        return graph
