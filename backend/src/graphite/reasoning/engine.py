"""Unified Topological Reasoning Engine for technical blueprints."""

from typing import Any, Dict, List, Optional, Set
from graphite.core.models import BlueprintGraph
from graphite.reasoning.flow import FlowTracer, FlowTraceResult
from graphite.reasoning.isolation import IsolationAnalyzer, IsolationPlan
from graphite.reasoning.pathfinding import PathFinder, PathResult, BypassLoop
from graphite.reasoning.rules import BlueprintRuleChecker, ComplianceReport


class TopologicalReasoningEngine:
    """Master engine orchestrating all topological analysis, flow tracing,

    safety isolation, pathfinding, and compliance auditing.
    """

    def __init__(self, graph: BlueprintGraph):
        self.graph = graph
        self.flow_tracer = FlowTracer(graph)
        self.isolation_analyzer = IsolationAnalyzer(graph)
        self.path_finder = PathFinder(graph)
        self.rule_checker = BlueprintRuleChecker(graph)

    def trace_flow(
        self,
        origin: str,
        closed_valves: Optional[Set[str]] = None,
        max_depth: Optional[int] = None,
    ) -> FlowTraceResult:
        """Trace downstream/upstream reachability from a starting equipment."""
        return self.flow_tracer.trace_reachability(
            origin=origin,
            blocked_nodes=closed_valves,
            max_depth=max_depth,
        )

    def isolate_component(self, target_id: str) -> IsolationPlan:
        """Find the minimal valve boundary required to safely seal off a component."""
        return self.isolation_analyzer.compute_isolation_perimeter(target_id)

    def find_shortest_path(
        self,
        source: str,
        target: str,
        blocked_nodes: Optional[Set[str]] = None,
    ) -> Optional[PathResult]:
        """Find the shortest physical piping route between two components."""
        return self.path_finder.find_shortest_path(
            source=source,
            target=target,
            blocked_nodes=blocked_nodes,
        )

    def find_all_paths(
        self,
        source: str,
        target: str,
        cutoff: int = 10,
    ) -> List[PathResult]:
        """Find all alternate simple paths between two components."""
        return self.path_finder.find_all_simple_paths(
            source=source,
            target=target,
            cutoff=cutoff,
        )

    def detect_bypasses(self, component_id: str) -> List[BypassLoop]:
        """Check if an equipment has an active/standby bypass loop around it."""
        return self.path_finder.detect_bypass_loops(component_id)

    def audit_compliance(self) -> ComplianceReport:
        """Run industrial engineering compliance rules."""
        return self.rule_checker.run_all_checks()

    def extract_k_hop_subgraph(self, center_node: str, k: int = 2) -> BlueprintGraph:
        """Extract localized k-hop neighborhood around a component."""
        return self.flow_tracer.extract_k_hop_subgraph(center_node, k=k)

    def trace_upstream(self, origin: str) -> List[str]:
        """Trace incoming flow origins reaching this component."""
        return self.flow_tracer.trace_upstream(origin)

    def trace_downstream(self, origin: str) -> List[str]:
        """Trace discharge path and receiving equipment."""
        return self.flow_tracer.trace_downstream(origin)

    def find_containment_valves(self, target_id: str) -> List[str]:
        """Find the minimal valve boundary required to safely isolate this component."""
        plan = self.isolation_analyzer.compute_isolation_perimeter(target_id)
        return plan.isolation_valves

    def find_bypasses(self, component_id: str) -> List[List[str]]:
        """Find active redundant bypass paths around this component."""
        loops = self.path_finder.detect_bypass_loops(component_id)
        return [loop.bypass_path for loop in loops]

    def find_critical_cut_valves(self) -> List[str]:
        """Identify critical articulation valves maintaining plant network continuity."""
        import networkx as nx
        G = self.graph.to_networkx(directed=False)
        art_points = set(nx.articulation_points(G))
        return sorted([
            nid for nid in art_points
            if nid in self.graph.nodes and "valve" in self.graph.nodes[nid].label.lower()
        ])

    def get_k_hop_context(self, component_id: str, k: int = 2) -> Dict[str, Any]:
        """Extract structured local neighborhood context for GraphRAG prompt conditioning."""
        subgraph = self.flow_tracer.extract_k_hop_subgraph(component_id, k=k)
        return {
            "center_component": component_id,
            "k_hops": k,
            "total_local_nodes": len(subgraph.nodes),
            "total_local_edges": len(subgraph.edges),
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "bbox": n.bbox.to_tuple() if n.bbox else None,
                    "center": n.get_center(),
                }
                for n in subgraph.nodes.values()
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "type": e.edge_label,
                    "length": round(e.length, 2),
                }
                for e in subgraph.edges
            ],
        }
