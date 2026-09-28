"""Graphite ingestion module: patch tiling, coordinate projection, OCR tag extraction, and stitching."""

from graphite.ingestion.tiling import TilingEngine, BlueprintPatch
from graphite.ingestion.ocr import OCRTagExtractor, EquipmentTag
from graphite.ingestion.pipeline import MultimodalIngestionPipeline

__all__ = [
    "TilingEngine",
    "BlueprintPatch",
    "OCRTagExtractor",
    "EquipmentTag",
    "MultimodalIngestionPipeline",
]
