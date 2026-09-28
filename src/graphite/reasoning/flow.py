"""Topological flow and reachability tracing for blueprint process graphs."""

from collections import deque
from typing import Dict, List, Optional, Set, Tuple
import networkx as nx
from pydantic import BaseModel, Field

from graphite.core.models import BlueprintGraph, ComponentNode, PipeEdge


class FlowTraceResult(BaseModel):
    """Result of a flow reachability traversal."""
    origin_node: str
    reachable_nodes: List[str]
    traversed_edges: List[Tuple[str, str]]
    components_by_type: Dict[str, List[str]] = Field(default_factory=dict)
    distances: Dict[str, float] = Field(default_factory=dict)
    blocked_nodes: List[str] = Field(default_factory=list)


class FlowTracer:
    """Deterministic flow reachability and neighborhood extractor."""

    def __init__(self, graph: BlueprintGraph):
        self.blueprint = graph
        self.nx_graph = graph.to_networkx(directed=False)
        self.di_graph = graph.to_networkx(directed=True)

    def trace_downstream(
        self,
        origin: str,
        blocked_nodes: Optional[Set[str]] = None,
        max_depth: Optional[int] = None,
    ) -> List[str]:
        """Trace forward downstream fluid/gas flow through DiGraph successors."""
        if origin not in self.di_graph:
            return []

        blocked = set(blocked_nodes or [])
        visited: Set[str] = set()
        queue = deque([(origin, 0)])

        while queue:
            curr, depth = queue.popleft()
            if max_depth is not None and depth >= max_depth:
                continue

            for succ in self.di_graph.successors(curr):
                if succ in visited:
                    continue
                if succ in blocked:
                    visited.add(succ)
                    continue
                visited.add(succ)
                queue.append((succ, depth + 1))

        return sorted(list(visited))

    def trace_upstream(
        self,
        origin: str,
        blocked_nodes: Optional[Set[str]] = None,
        max_depth: Optional[int] = None,
    ) -> List[str]:
        """Trace reverse upstream supply fluid/gas inflow through DiGraph predecessors."""
        if origin not in self.di_graph:
            return []

        blocked = set(blocked_nodes or [])
        visited: Set[str] = set()
        queue = deque([(origin, 0)])

        while queue:
            curr, depth = queue.popleft()
            if max_depth is not None and depth >= max_depth:
                continue

            for pred in self.di_graph.predecessors(curr):
                if pred in visited:
                    continue
                if pred in blocked:
                    visited.add(pred)
                    continue
                visited.add(pred)
                queue.append((pred, depth + 1))

        return sorted(list(visited))

    def trace_reachability(
        self,
        origin: str,
        blocked_nodes: Optional[Set[str]] = None,
        max_depth: Optional[int] = None,
        allowed_edge_types: Optional[Set[str]] = None,
    ) -> FlowTraceResult:
        """Trace fluid or signal propagation from an origin component.

        Args:
            origin: Node ID where fluid originates.
            blocked_nodes: Set of node IDs that halt flow (e.g. closed valves).
            max_depth: Maximum number of hops from origin.
            allowed_edge_types: Allowed edge labels (e.g. {'solid'} to follow main process pipes).

        Returns:
            FlowTraceResult containing all reachable assets and path statistics.
        """
        if origin not in self.nx_graph:
            raise KeyError(f"Origin node '{origin}' not found in blueprint graph.")

        blocked = set(blocked_nodes or [])
        visited_nodes: Set[str] = {origin}
        traversed_edges: List[Tuple[str, str]] = []
        distances: Dict[str, float] = {origin: 0.0}

        # Queue: (current_node, current_hop, cumulative_distance)
        queue = deque([(origin, 0, 0.0)])

        while queue:
            curr, hop, dist = queue.popleft()

            if max_depth is not None and hop >= max_depth:
                continue

            for nbr in self.nx_graph.neighbors(curr):
                edge_data = self.nx_graph[curr][nbr]
                e_type = edge_data.get("edge_label", "solid")

                if allowed_edge_types is not None and e_type not in allowed_edge_types:
                    continue

                edge_key = tuple(sorted([curr, nbr]))
                if edge_key not in traversed_edges:
                    traversed_edges.append(edge_key)  # type: ignore

                # If neighbor is blocked (e.g. closed valve), record it as reached, but DO NOT propagate beyond it
                if nbr in blocked:
                    visited_nodes.add(nbr)
                    if nbr not in distances:
                        edge_len = edge_data.get("length", 1.0)
                        distances[nbr] = dist + edge_len
                    continue

                if nbr not in visited_nodes:
                    visited_nodes.add(nbr)
                    edge_len = edge_data.get("length", 1.0)
                    new_dist = dist + edge_len
                    distances[nbr] = new_dist
                    queue.append((nbr, hop + 1, new_dist))

        # Group components by category
        by_type: Dict[str, List[str]] = {}
        for nid in visited_nodes:
            lbl = self.nx_graph.nodes[nid].get("label", "unknown")
            by_type.setdefault(lbl, []).append(nid)

        return FlowTraceResult(
            origin_node=origin,
            reachable_nodes=sorted(list(visited_nodes)),
            traversed_edges=traversed_edges,
            components_by_type=by_type,
            distances=distances,
            blocked_nodes=sorted(list(blocked.intersection(visited_nodes))),
        )

    def extract_k_hop_subgraph(self, center_node: str, k: int = 2) -> BlueprintGraph:
        """Extract localized k-hop neighborhood around a component for local GraphRAG."""
        if center_node not in self.nx_graph:
            raise KeyError(f"Node '{center_node}' not found in blueprint graph.")

        nodes_in_k_hop = {center_node}
        current_frontier = {center_node}

        for _ in range(k):
            next_frontier = set()
            for u in current_frontier:
                for nbr in self.nx_graph.neighbors(u):
                    if nbr not in nodes_in_k_hop:
                        nodes_in_k_hop.add(nbr)
                        next_frontier.add(nbr)
            current_frontier = next_frontier

        subgraph_nx = self.nx_graph.subgraph(nodes_in_k_hop).copy()
        return BlueprintGraph.from_networkx(
            subgraph_nx,
            name=f"{self.blueprint.name}_{center_node}_k{k}",
            is_collapsed=self.blueprint.is_collapsed,
        )
