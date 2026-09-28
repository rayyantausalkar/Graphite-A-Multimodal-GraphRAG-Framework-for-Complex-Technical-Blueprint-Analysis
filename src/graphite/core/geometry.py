"""Geometric utilities for blueprint coordinates, bounding boxes, and path lengths."""

from typing import List, Optional, Tuple
import math
from shapely.geometry import Point, LineString, Polygon
from graphite.core.models import BoundingBox, ComponentNode


def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Euclidean distance between two 2D points."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def path_length(points: List[Tuple[float, float]]) -> float:
    """Compute cumulative Euclidean length along an ordered sequence of 2D waypoints."""
    if len(points) < 2:
        return 0.0
    total = 0.0
    for i in range(len(points) - 1):
        total += euclidean_distance(points[i], points[i + 1])
    return total


def find_nearest_node(
    point: Tuple[float, float],
    nodes: List[ComponentNode],
    max_distance: Optional[float] = None,
) -> Optional[Tuple[ComponentNode, float]]:
    """Find the nearest component node to a query coordinate."""
    if not nodes:
        return None
    px, py = point
    best_node = None
    best_dist = float("inf")

    for node in nodes:
        cx, cy = node.get_center()
        dist = math.hypot(cx - px, cy - py)
        if dist < best_dist:
            best_dist = dist
            best_node = node

    if max_distance is not None and best_dist > max_distance:
        return None
    return (best_node, best_dist) if best_node is not None else None


def line_intersects_bbox(
    p1: Tuple[float, float], p2: Tuple[float, float], bbox: BoundingBox
) -> bool:
    """Check if line segment (p1, p2) intersects a bounding box."""
    line = LineString([p1, p2])
    poly = bbox.to_shapely()
    return line.intersects(poly)
