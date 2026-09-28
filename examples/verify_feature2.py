"""Feature 2 Verification Script for Graphite: Deterministic Topological Reasoning Engine."""

from pathlib import Path
from graphite.core.parser import parse_graphml
from graphite.core.collapsing import collapse_connectors
from graphite.reasoning.engine import TopologicalReasoningEngine
from graphite.utils.visualization import visualize_blueprint


def main():
    print("=" * 75)
    print("GRAPHITE: FEATURE 2 REASONING ENGINE VERIFICATION")
    print("=" * 75)

    blueprint_path = Path("data/PID2Graph/Complete/PID2Graph OPEN100/0.graphml")
    if not blueprint_path.exists():
        print(f"Error: Could not find {blueprint_path}")
        return

    # Ingest and collapse
    raw_graph = parse_graphml(blueprint_path)
    graph = collapse_connectors(raw_graph, remove_crossings=True)
    engine = TopologicalReasoningEngine(graph)

    print(f"\nInitialized Reasoning Engine on '{graph.name}' ({len(graph.nodes)} physical nodes, {len(graph.edges)} edges)")

    # 1. Flow & Reachability Tracing
    print("\n" + "-" * 50)
    print("[1] FLOW & REACHABILITY TRACING")
    print("-" * 50)
    connected_nodes = [n for n, deg in graph.to_networkx().degree() if deg > 1]
    origin = connected_nodes[0]
    origin_lbl = graph.nodes[origin].label
    print(f"Tracing flow originating at component: '{origin}' ({origin_lbl})")

    unblocked_res = engine.trace_flow(origin)
    print(f"  - Unblocked reachability: {len(unblocked_res.reachable_nodes)} components reachable")
    print(f"  - Equipment breakdown: {unblocked_res.components_by_type}")

    # Now block an adjacent node
    block_target = list(graph.to_networkx().neighbors(origin))[0]
    print(f"\nSimulating CLOSED valve at: '{block_target}'")
    blocked_res = engine.trace_flow(origin, closed_valves={block_target})
    print(f"  - Reachable components after closing valve: {len(blocked_res.reachable_nodes)}")
    print(f"  - Halted at barrier: {blocked_res.blocked_nodes}")

    # 2. Component Failure Isolation & Minimal Boundary Valves
    print("\n" + "-" * 50)
    print("[2] FAILURE ISOLATION & EMERGENCY SHUTDOWN BOUNDARY")
    print("-" * 50)
    target_comp = connected_nodes[1]
    print(f"Computing emergency isolation perimeter for damaged equipment: '{target_comp}'")
    plan = engine.isolate_component(target_comp)
    print(f"  - Target Component: {plan.target_node} ({plan.target_label})")
    print(f"  - Minimal Boundary Isolation Valves to Close: {plan.isolation_valves}")
    print(f"  - Components trapped inside isolated perimeter: {plan.isolated_components}")
    print(f"  - Full containment achieved: {plan.is_fully_isolated}")
    if plan.unisolated_escape_routes:
        print(f"  - Open/unisolated escape paths: {plan.unisolated_escape_routes}")

    # 3. Pathfinding & Path Tracing
    print("\n" + "-" * 50)
    print("[3] PHYSICAL PATHFINDING & ROUTE TRACING")
    print("-" * 50)
    edges = list(graph.to_networkx().edges())
    u, v = edges[0]
    # Pick a node 2 hops away if possible
    nbrs = list(graph.to_networkx().neighbors(v))
    target_node = nbrs[0] if nbrs and nbrs[0] != u else v

    path_res = engine.find_shortest_path(u, target_node)
    if path_res:
        print(f"Shortest path from '{u}' to '{target_node}':")
        print(f"  - Route: {' -> '.join(path_res.nodes)}")
        print(f"  - Hops: {path_res.hops} segments")
        print(f"  - Cumulative Pipe Length: {path_res.total_length:.1f} pixels")
        print(f"  - Valves on Path: {path_res.valves_on_path}")

    # 4. Bypass Loop Detection & Recirculation Cycles
    print("\n" + "-" * 50)
    print("[4] REDUNDANCY & BYPASS LOOP DISCOVERY")
    print("-" * 50)
    cycles = engine.path_finder.find_all_cycles()
    print(f"  - Fundamental closed cycles/loops in blueprint: {len(cycles)}")
    if cycles:
        print(f"  - Sample cycle: {' -> '.join(cycles[0])}")

    # Search for bypass around valves
    bypassed_valves = []
    for nid, node in graph.nodes.items():
        if node.label == "valve":
            bps = engine.detect_bypasses(nid)
            if bps:
                bypassed_valves.append((nid, bps))

    print(f"  - Total valves equipped with redundant bypass loops: {len(bypassed_valves)}")
    for v_id, bps in bypassed_valves[:2]:
        print(f"    * Valve '{v_id}' has bypass: {' -> '.join(bps[0].bypass_path)} (len={bps[0].bypass_length:.1f} px)")

    # 5. Industrial Engineering Compliance Audit
    print("\n" + "-" * 50)
    print("[5] ENGINEERING COMPLIANCE & ANOMALY AUDIT")
    print("-" * 50)
    report = engine.audit_compliance()
    print(f"Checked {report.total_components_checked} physical components.")
    print(f"Rules Passed: {len(report.passed_rules)}")
    print(f"Anomalies Flagged: {len(report.anomalies)}")
    for a in report.anomalies[:4]:
        print(f"  [{a.severity}] {a.rule_id} on {a.component_id} ({a.component_label}): {a.description}")

    # 6. Generate Annotated Reasoning Image
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    out_img = out_dir / "feature2_reasoning_verification.png"
    print(f"\n[6] Generating visualization with highlighted path and isolation zone: {out_img}")

    sample_path = path_res.nodes if path_res else [u, v]
    highlight_nodes = list(set(sample_path) | set(plan.isolation_valves) | {plan.target_node})

    visualize_blueprint(
        graph,
        output_path=out_img,
        show_boxes=True,
        show_labels=True,
        show_edges=True,
        highlight_nodes=highlight_nodes,
        highlight_path=sample_path,
        dpi=180,
    )
    print(f"  -> Saved visualization to: {out_img.resolve()}")

    print("\n" + "=" * 75)
    print("FEATURE 2 VERIFICATION COMPLETED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    main()
