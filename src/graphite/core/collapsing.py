"""Connector Collapsing Algorithm for engineering blueprints.

Transforms raw routing graphs (containing hundreds of auxiliary line bend/waypoint
nodes such as 'connector' and 'crossing') into clean, semantically meaningful
process flow graphs directly connecting physical engineering equipment.
"""

from collections import Counter
from typing import Dict, List, Set, Tuple
import networkx as nx

from graphite.core.geometry import path_length
from graphite.core.models import BlueprintGraph, ComponentNode, PipeEdge


def collapse_connectors(
    graph: BlueprintGraph,
    remove_crossings: bool = True,
    remove_isolated_physical: bool = False,
) -> BlueprintGraph:
    """Collapse connector chains into direct semantic edges between physical equipment.

    Follows the canonical P&ID digitization paradigm established in SynthPID
    (Prasad & Mahapatra, IIT Bombay) and DLR IEEE DSAA 2025:
    1. Crossings (non-connecting 2D line crossings) are removed.
    2. Connector chains (intermediate pipe bends) are contracted into direct edges.
    3. The majority edge type (e.g. 'solid', 'dashed') is assigned to the collapsed edge.
    4. Waypoint coordinates are preserved along the route for visual path rendering.

    Args:
        graph: The raw uncollapsed BlueprintGraph.
        remove_crossings: If True, delete crossing nodes prior to contraction.
        remove_isolated_physical: If True, remove physical components with degree 0.

    Returns:
        A new BlueprintGraph containing only physical components and collapsed edges.
    """
    raw_nx = graph.to_networkx()

    # Step 1: Remove auxiliary crossing nodes if requested
    if remove_crossings:
        crossings = [
            n for n, d in raw_nx.nodes(data=True) if d.get("label") == "crossing"
        ]
        raw_nx.remove_nodes_from(crossings)

    # Step 2: Identify physical components vs connector routing nodes
    physical_nodes: Dict[str, ComponentNode] = graph.get_physical_nodes()
    # Filter to nodes currently in raw_nx (in case any were removed)
    physical_ids: Set[str] = set(physical_nodes.keys()).intersection(raw_nx.nodes())

    # Step 3: Retain existing direct edges between physical components
    collapsed_edges: Dict[Tuple[str, str], PipeEdge] = {}

    for u, v, data in raw_nx.edges(data=True):
        if u in physical_ids and v in physical_ids:
            key = tuple(sorted([u, v]))  # type: ignore
            p1 = graph.nodes[u].get_center()
            p2 = graph.nodes[v].get_center()
            edge = PipeEdge(
                source=key[0],
                target=key[1],
                edge_label=data.get("edge_label", "solid"),
                waypoints=[p1, p2],
                intermediate_nodes=[],
                hops=1,
                length=path_length([p1, p2]),
            )
            collapsed_edges[key] = edge

    # Step 4: Traverse through connector chains from each physical component
    for start_id in physical_ids:
        # State: (current_node, visited_nodes_set, path_nodes_list, edge_types_list)
        start_center = graph.nodes[start_id].get_center()
        queue = [(start_id, {start_id}, [start_id], [])]

        while queue:
            curr, visited, path_nodes, edge_types = queue.pop(0)

            for nbr in raw_nx.neighbors(curr):
                if nbr in visited:
                    continue

                nbr_lbl = raw_nx.nodes[nbr].get("label", "unknown")
                e_type = raw_nx[curr][nbr].get("edge_label", "solid")
                cur_types = edge_types + [e_type]
                cur_visited = visited | {nbr}
                cur_path = path_nodes + [nbr]

                if nbr_lbl == "connector":
                    # Continue tracing through connector waypoint
                    queue.append((nbr, cur_visited, cur_path, cur_types))
                elif nbr in physical_ids and nbr != start_id:
                    # Found connection to another physical component!
                    key = tuple(sorted([start_id, nbr]))  # type: ignore

                    # Collect waypoints
                    waypoints = [
                        graph.nodes[node_id].get_center()
                        for node_id in cur_path
                        if node_id in graph.nodes
                    ]
                    route_len = path_length(waypoints)

                    # Majority edge label along this chain
                    maj_label = (
                        Counter(cur_types).most_common(1)[0][0]
                        if cur_types
                        else "solid"
                    )

                    intermediate = [nid for nid in cur_path[1:-1]]

                    # If an edge between these two components was already found, keep the shorter path
                    if key in collapsed_edges:
                        if route_len < collapsed_edges[key].length:
                            collapsed_edges[key] = PipeEdge(
                                source=key[0],
                                target=key[1],
                                edge_label=maj_label,
                                waypoints=waypoints,
                                intermediate_nodes=intermediate,
                                hops=len(cur_path) - 1,
                                length=route_len,
                            )
                    else:
                        collapsed_edges[key] = PipeEdge(
                            source=key[0],
                            target=key[1],
                            edge_label=maj_label,
                            waypoints=waypoints,
                            intermediate_nodes=intermediate,
                            hops=len(cur_path) - 1,
                            length=route_len,
                        )

    # Step 5: Construct the new collapsed BlueprintGraph
    collapsed_graph = BlueprintGraph(
        name=f"{graph.name}_collapsed",
        image_path=graph.image_path,
        image_width=graph.image_width,
        image_height=graph.image_height,
        is_collapsed=True,
        metadata={
            **graph.metadata,
            "raw_total_nodes": len(graph.nodes),
            "raw_total_edges": len(graph.edges),
            "collapsed_edge_count": len(collapsed_edges),
        },
    )

    # Add physical nodes
    for pid in physical_ids:
        node = graph.nodes[pid]
        collapsed_graph.add_node(node)

    # Add collapsed edges
    for edge in collapsed_edges.values():
        collapsed_graph.add_edge(edge)

    # Optionally remove isolated physical nodes
    if remove_isolated_physical:
        active_endpoints = set()
        for e in collapsed_graph.edges:
            active_endpoints.add(e.source)
            active_endpoints.add(e.target)
        isolated = [
            nid for nid in collapsed_graph.nodes if nid not in active_endpoints
        ]
        for iso_id in isolated:
            del collapsed_graph.nodes[iso_id]

    return collapsed_graph
