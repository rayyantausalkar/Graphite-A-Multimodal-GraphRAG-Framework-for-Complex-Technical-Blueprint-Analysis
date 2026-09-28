"""Hierarchical subsystem partitioning using Louvain community detection."""

from collections import Counter
from typing import Dict, List, Optional, Set, Tuple
import math
import networkx as nx
from networkx.algorithms.community import louvain_communities
from pydantic import BaseModel, Field

from graphite.core.models import BlueprintGraph


class SubsystemCommunity(BaseModel):
    """A functional plant subsystem partitioned via community detection."""
    subsystem_id: int
    name: str
    primary_function: str
    domain_category: str = "Process"  # "Process", "Utility", "Storage", "Safety & Control"
    level: int = 1
    component_ids: List[str]
    equipment_count_by_type: Dict[str, int] = Field(default_factory=dict)
    boundary_valves: List[str] = Field(default_factory=list)
    internal_pipe_length: float = 0.0


class SubsystemPartitioner:
    """Partitions process flow graphs into hierarchical functional plant subsystems."""

    def __init__(self, resolution: float = 1.0, seed: int = 42, merge_singletons: bool = True):
        self.resolution = resolution
        self.seed = seed
        self.merge_singletons = merge_singletons

    def infer_subsystem_name(self, components_by_type: Dict[str, int], sub_id: int) -> Tuple[str, str, str]:
        """Infer semantic engineering name and high-level domain category based on equipment profile."""
        has_tank = components_by_type.get("tank", 0) > 0 or components_by_type.get("vessel", 0) > 0
        has_pump = components_by_type.get("pump", 0) > 0
        has_hex = components_by_type.get("heat_exchanger", 0) > 0
        has_inst = components_by_type.get("instrumentation", 0) > 0
        valves = components_by_type.get("valve", 0)

        if has_hex:
            func = "Heat Exchange & Thermal Unit"
            domain = "Utility"
        elif has_tank and has_pump:
            func = "Storage & Feed Pumping Unit"
            domain = "Storage & Separation"
        elif has_tank:
            func = "Vessel & Storage Unit"
            domain = "Storage & Separation"
        elif has_pump:
            func = "Fluid Transfer & Pumping System"
            domain = "Process"
        elif valves >= 4:
            func = "Flow Distribution Manifold"
            domain = "Process"
        elif has_inst and valves >= 1:
            func = "Process Monitoring & Control Loop"
            domain = "Safety & Control"
        else:
            func = "Process Unit"
            domain = "Process"

        name = f"Subsystem-{sub_id:02d}: {func}"
        return name, func, domain

    def partition_graph(self, graph: BlueprintGraph) -> Dict[int, SubsystemCommunity]:
        """Partition blueprint graph into functional subsystems using Louvain modularity."""
        G = graph.to_networkx(directed=False)
        if len(G) == 0:
            return {}

        # 1. Run Louvain community detection
        raw_communities = [set(c) for c in louvain_communities(G, resolution=self.resolution, seed=self.seed)]

        # 2. Optional: merge singletons into nearest spatial multi-node community
        if self.merge_singletons:
            major_comms = [c for c in raw_communities if len(c) >= 2]
            singletons = [c for c in raw_communities if len(c) < 2]

            if major_comms and singletons:
                # Merge each singleton into the closest major community by center-point Euclidean distance
                for s_comm in singletons:
                    s_node_id = next(iter(s_comm))
                    if s_node_id not in graph.nodes:
                        continue
                    scx, scy = graph.nodes[s_node_id].get_center()

                    best_comm = major_comms[0]
                    best_dist = float("inf")

                    for m_comm in major_comms:
                        for m_nid in m_comm:
                            if m_nid in graph.nodes:
                                mcx, mcy = graph.nodes[m_nid].get_center()
                                dist = math.hypot(scx - mcx, scy - mcy)
                                if dist < best_dist:
                                    best_dist = dist
                                    best_comm = m_comm

                    best_comm.add(s_node_id)

                raw_communities = major_comms

        # Sort communities by size descending
        raw_communities = sorted(raw_communities, key=lambda c: len(c), reverse=True)

        # 3. Extract detailed subsystem properties, domain hierarchy, and boundary valves
        subsystems: Dict[int, SubsystemCommunity] = {}

        for sub_id, comm in enumerate(raw_communities):
            comp_list = sorted(list(comm))
            type_counts = Counter(
                graph.nodes[nid].label for nid in comp_list if nid in graph.nodes
            )

            # Detect boundary valves connecting this subsystem to other subsystems
            boundary_valves: Set[str] = set()
            internal_len = 0.0

            for u in comp_list:
                for v in G.neighbors(u):
                    e_len = G[u][v].get("length", 0.0)
                    if v in comm:
                        internal_len += e_len / 2.0  # undirected edge counted once
                    else:
                        # Inter-subsystem boundary connection
                        if u in graph.nodes and "valve" in graph.nodes[u].label.lower():
                            boundary_valves.add(u)
                        if v in graph.nodes and "valve" in graph.nodes[v].label.lower():
                            boundary_valves.add(v)

            name, primary_func, domain_cat = self.infer_subsystem_name(dict(type_counts), sub_id + 1)

            subsystems[sub_id] = SubsystemCommunity(
                subsystem_id=sub_id,
                name=name,
                primary_function=primary_func,
                domain_category=domain_cat,
                level=1,
                component_ids=comp_list,
                equipment_count_by_type=dict(type_counts),
                boundary_valves=sorted(list(boundary_valves)),
                internal_pipe_length=round(internal_len, 1),
            )

        return subsystems
