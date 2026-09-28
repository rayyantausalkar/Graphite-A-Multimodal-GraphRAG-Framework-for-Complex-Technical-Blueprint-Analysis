"""Visual, textual, and multimodal fusion encoders for blueprint equipment."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import math
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms

from graphite.core.models import BoundingBox


class VisualEncoder:
    """Extracts 512-dimensional visual feature embeddings from cropped equipment symbols."""

    def __init__(self, device: Optional[str] = None):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # Use ResNet18 backbone, stripping the final classification FC layer
        backbone = models.resnet18(weights=None)
        # We use the convolutional trunk + adaptive average pooling to get 512-dim vector
        self.feature_extractor = nn.Sequential(*list(backbone.children())[:-1]).to(self.device)
        self.feature_extractor.eval()

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

    def encode_crop(self, pil_crop: Image.Image) -> List[float]:
        """Encode a PIL image crop into a normalized 512-dim visual embedding."""
        if pil_crop.mode != "RGB":
            pil_crop = pil_crop.convert("RGB")

        tensor = self.transform(pil_crop).unsqueeze(0).to(self.device)
        with torch.no_grad():
            feat = self.feature_extractor(tensor)  # (1, 512, 1, 1)
            feat = feat.squeeze().cpu().numpy()

        norm = np.linalg.norm(feat)
        if norm > 0:
            feat = feat / norm
        return feat.tolist()

    def crop_and_encode(
        self,
        full_image: Image.Image,
        bbox: BoundingBox,
        save_path: Optional[Union[str, Path]] = None,
        padding_px: int = 10,
    ) -> Tuple[List[float], Optional[str]]:
        """Crop symbol from master blueprint and encode visual features."""
        w, h = full_image.size
        # Clamped bounding box with padding
        x1 = max(0, min(int(bbox.xmin - padding_px), w - 5))
        y1 = max(0, min(int(bbox.ymin - padding_px), h - 5))
        x2 = min(w, max(int(bbox.xmax + padding_px), x1 + 5))
        y2 = min(h, max(int(bbox.ymax + padding_px), y1 + 5))

        crop = full_image.crop((x1, y1, x2, y2))
        saved_file = None

        if save_path is not None:
            p = Path(save_path).resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            crop.save(str(p))
            saved_file = str(p)

        embedding = self.encode_crop(crop)
        return embedding, saved_file


class TextEncoder:
    """Encodes engineering equipment specifications and textual descriptions into 512-dim vectors."""

    def __init__(self, embedding_dim: int = 512):
        self.embedding_dim = embedding_dim

    def encode_text(self, text: str) -> List[float]:
        """Generate a deterministic semantic embedding vector for equipment specifications."""
        import hashlib
        words = text.lower().replace("-", " ").replace("_", " ").split()
        vec = np.zeros(self.embedding_dim, dtype=np.float32)

        if not words:
            return vec.tolist()

        for w in words:
            # Deterministic word projection hash
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
            for i in range(8):
                idx = (h >> (i * 16)) % self.embedding_dim
                val = (((h >> (i * 16 + 8)) % 256) / 128.0) - 1.0
                vec[idx] += val

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()


class MultimodalFusionEngine:
    """Fuses visual and textual embeddings into a unified multimodal representation."""

    def __init__(self, visual_weight: float = 0.5):
        self.visual_weight = visual_weight

    def fuse(
        self,
        visual_vec: Optional[List[float]],
        text_vec: Optional[List[float]],
    ) -> List[float]:
        """Combine visual feature vector and text specification vector into a unified embedding."""
        if visual_vec is None and text_vec is None:
            return [0.0] * 512
        if visual_vec is None:
            return text_vec  # type: ignore
        if text_vec is None:
            return visual_vec

        v_arr = np.array(visual_vec, dtype=np.float32)
        t_arr = np.array(text_vec, dtype=np.float32)

        # Pad or match dimensions if necessary
        dim = max(len(v_arr), len(t_arr))
        if len(v_arr) < dim:
            v_arr = np.pad(v_arr, (0, dim - len(v_arr)))
        if len(t_arr) < dim:
            t_arr = np.pad(t_arr, (0, dim - len(t_arr)))

        alpha = self.visual_weight
        fused = alpha * v_arr + (1.0 - alpha) * t_arr
        norm = np.linalg.norm(fused)
        if norm > 0:
            fused = fused / norm
        return fused.tolist()
