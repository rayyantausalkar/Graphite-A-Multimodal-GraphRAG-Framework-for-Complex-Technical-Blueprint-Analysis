"""Pathfinding, redundant route discovery, and bypass loop analysis."""

from typing import Dict, List, Optional, Set, Tuple
import networkx as nx
from pydantic import BaseModel, Field

from graphite.core.models import BlueprintGraph


class PathResult(BaseModel):
    """Result of pathfinding between two components."""
    source: str
    target: str
    nodes: List[str]
    hops: int
    total_length: float
    waypoint_coordinates: List[Tuple[float, float]] = Field(default_factory=list)
    valves_on_path: List[str] = Field(default_factory=list)


class BypassLoop(BaseModel):
    """A bypass route around a component."""
    target_component: str
    bypass_path: List[str]
    bypass_length: float
    valves_on_bypass: List[str] = Field(default_factory=list)


class PathFinder:
    """Path search, routing redundancy, and loop detection engine."""

    def __init__(self, graph: BlueprintGraph):
        self.blueprint = graph
        self.nx_graph = graph.to_networkx(directed=False)

    def find_shortest_path(
        self,
        source: str,
        target: str,
        weight: str = "length",
        blocked_nodes: Optional[Set[str]] = None,
    ) -> Optional[PathResult]:
        """Find the shortest physical path between two blueprint assets.

        Args:
            source: Starting component ID.
            target: Destination component ID.
            weight: Edge weight attribute ('length' for pixel distance, None for hops).
            blocked_nodes: Nodes that cannot be traversed (e.g. closed valves).

        Returns:
            PathResult with path nodes, cumulative length, and waypoints, or None if disconnected.
        """
        if source not in self.nx_graph or target not in self.nx_graph:
            return None

        G = self.nx_graph
        if blocked_nodes:
            blocked_set = set(blocked_nodes) - {source, target}
            G = G.copy()
            G.remove_nodes_from(blocked_set)

        try:
            path = nx.shortest_path(G, source=source, target=target, weight=weight)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

        # Gather cumulative length and continuous waypoints
        total_len = 0.0
        waypoints: List[Tuple[float, float]] = []
        valves: List[str] = []

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge_data = G[u][v]
            total_len += edge_data.get("length", 1.0)
            edge_pts = edge_data.get("waypoints", [])
            if edge_pts:
                # Append waypoints avoiding duplication of junction vertex
                if not waypoints:
                    waypoints.extend(edge_pts)
                else:
                    waypoints.extend(edge_pts[1:])

        for n in path:
            if "valve" in G.nodes[n].get("label", "").lower():
                valves.append(n)

        return PathResult(
            source=source,
            target=target,
            nodes=path,
            hops=len(path) - 1,
            total_length=total_len,
            waypoint_coordinates=waypoints,
            valves_on_path=valves,
        )

    def find_all_simple_paths(
        self,
        source: str,
        target: str,
        cutoff: int = 10,
    ) -> List[PathResult]:
        """Find all alternate simple paths between two components within a hop cutoff."""
        if source not in self.nx_graph or target not in self.nx_graph:
            return []

        results = []
        try:
            for path in nx.all_simple_paths(self.nx_graph, source, target, cutoff=cutoff):
                total_len = sum(
                    self.nx_graph[path[i]][path[i + 1]].get("length", 1.0)
                    for i in range(len(path) - 1)
                )
                valves = [n for n in path if "valve" in self.nx_graph.nodes[n].get("label", "").lower()]
                results.append(
                    PathResult(
                        source=source,
                        target=target,
                        nodes=path,
                        hops=len(path) - 1,
                        total_length=total_len,
                        valves_on_path=valves,
                    )
                )
        except Exception:
            pass

        return sorted(results, key=lambda p: p.total_length)

    def detect_bypass_loops(self, component_id: str) -> List[BypassLoop]:
        """Detect redundant bypass loops around a specific component.

        In process engineering, a bypass line allows fluid to circumvent an equipment
        (e.g., control valve, meter, filter) when it is taken offline for maintenance.
        Mathematically, this exists if there is an alternative path between the component's
        adjacent neighbors that does NOT pass through component_id.
        """
        if component_id not in self.nx_graph:
            return []

        neighbors = list(self.nx_graph.neighbors(component_id))
        if len(neighbors) < 2:
            return []

        # Graph without the component
        G_without = self.nx_graph.copy()
        G_without.remove_node(component_id)

        bypasses: List[BypassLoop] = []
        seen_paths: Set[Tuple[str, ...]] = set()

        # Check each pair of neighbors
        for i in range(len(neighbors)):
            for j in range(i + 1, len(neighbors)):
                u, v = neighbors[i], neighbors[j]
                if nx.has_path(G_without, u, v):
                    try:
                        path = nx.shortest_path(G_without, u, v, weight="length")
                        path_tuple = tuple(path)
                        if path_tuple not in seen_paths:
                            seen_paths.add(path_tuple)
                            p_len = sum(
                                G_without[path[k]][path[k + 1]].get("length", 1.0)
                                for k in range(len(path) - 1)
                            )
                            valves = [
                                n for n in path if "valve" in G_without.nodes[n].get("label", "").lower()
                            ]
                            bypasses.append(
                                BypassLoop(
                                    target_component=component_id,
                                    bypass_path=path,
                                    bypass_length=p_len,
                                    valves_on_bypass=valves,
                                )
                            )
                    except Exception:
                        pass

        return bypasses

    def find_all_cycles(self) -> List[List[str]]:
        """Identify fundamental recirculating loops and closed fluid cycles."""
        return nx.cycle_basis(self.nx_graph)
