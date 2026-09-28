"""Failure isolation and minimal boundary valve discovery for plant safety."""

from collections import deque
from typing import Dict, List, Optional, Set, Tuple
import networkx as nx
from pydantic import BaseModel, Field

from graphite.core.models import BlueprintGraph


class IsolationPlan(BaseModel):
    """Safety isolation perimeter and minimal valve cut-set."""
    target_node: str
    target_label: str
    isolation_valves: List[str]
    isolated_components: List[str]
    is_fully_isolated: bool
    unisolated_escape_routes: List[str] = Field(default_factory=list)
    impacted_equipment_by_type: Dict[str, List[str]] = Field(default_factory=dict)


class IsolationAnalyzer:
    """Computes safety isolation perimeters and emergency shutdown boundaries."""

    def __init__(self, graph: BlueprintGraph):
        self.blueprint = graph
        self.nx_graph = graph.to_networkx(directed=False)

    def compute_isolation_perimeter(
        self,
        target_component: str,
        valve_labels: Optional[Set[str]] = None,
    ) -> IsolationPlan:
        """Find the minimal set of valves to isolate a target component or leak.

        Explores outwards from target_component until encountering an isolation valve
        on each branch. If a branch reaches an external boundary (inlet/outlet or dead-end)
        without an intervening valve, flags the containment breach.

        Args:
            target_component: Node ID of failing/leaking component.
            valve_labels: Labels treated as isolatable valves (defaults to {'valve'}).

        Returns:
            IsolationPlan detailing valves to close and trapped components.
        """
        if target_component not in self.nx_graph:
            raise KeyError(f"Target component '{target_component}' not in blueprint.")

        valves_to_match = valve_labels or {"valve"}
        target_lbl = self.nx_graph.nodes[target_component].get("label", "unknown")

        # If the target itself is a valve, closing it isolates itself, but we also find adjacent lines
        isolation_valves: Set[str] = set()
        isolated_components: Set[str] = {target_component}
        unisolated_escapes: List[str] = []

        visited: Set[str] = {target_component}
        queue = deque([target_component])

        while queue:
            curr = queue.popleft()
            neighbors = list(self.nx_graph.neighbors(curr))

            if not neighbors and curr != target_component:
                # Dead end reached without valve
                unisolated_escapes.append(curr)

            for nbr in neighbors:
                if nbr in visited:
                    continue

                nbr_lbl = self.nx_graph.nodes[nbr].get("label", "unknown")

                # If neighbor is a valve, it acts as a boundary barrier
                is_valve = (
                    any(v in nbr_lbl.lower() for v in valves_to_match)
                    if valve_labels
                    else ("valve" in nbr_lbl.lower())
                )
                if is_valve and nbr != target_component:
                    isolation_valves.add(nbr)
                    visited.add(nbr)
                    # Halt expansion past this valve!
                else:
                    # Non-valve component is engulfed in the isolation zone
                    isolated_components.add(nbr)
                    visited.add(nbr)
                    queue.append(nbr)

        # Check if any branch escaped to inlet/outlet
        for comp in isolated_components:
            lbl = self.nx_graph.nodes[comp].get("label", "")
            if lbl in ("inlet/outlet", "arrow") and self.nx_graph.degree(comp) <= 1:
                unisolated_escapes.append(comp)

        is_fully_isolated = len(unisolated_escapes) == 0

        # Group impacted equipment
        by_type: Dict[str, List[str]] = {}
        for nid in isolated_components:
            lbl = self.nx_graph.nodes[nid].get("label", "unknown")
            by_type.setdefault(lbl, []).append(nid)

        return IsolationPlan(
            target_node=target_component,
            target_label=target_lbl,
            isolation_valves=sorted(list(isolation_valves)),
            isolated_components=sorted(list(isolated_components)),
            is_fully_isolated=is_fully_isolated,
            unisolated_escape_routes=sorted(unisolated_escapes),
            impacted_equipment_by_type=by_type,
        )
