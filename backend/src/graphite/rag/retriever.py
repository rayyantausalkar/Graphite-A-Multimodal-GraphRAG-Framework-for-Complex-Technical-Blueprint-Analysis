"""Dual-Mode GraphRAG Retriever: Implements Component-Level Local and Plant-Level Global Retrieval."""

from typing import Any, Dict, List, Optional, Tuple, Union
import re
import networkx as nx

from graphite.core.models import BlueprintGraph
from graphite.mmkg.representation import MultimodalKnowledgeGraph, MultimodalNode
from graphite.reasoning.engine import TopologicalReasoningEngine
from graphite.rag.context import LocalRetrievalContext, GlobalRetrievalContext


class LocalRetriever:
    """Component-level retriever extracting K-hop topological subgraphs, visual crops, and exact line paths."""

    def __init__(self, mmkg: MultimodalKnowledgeGraph, reasoning_engine: Optional[TopologicalReasoningEngine] = None):
        self.mmkg = mmkg
        if reasoning_engine is not None:
            self.engine = reasoning_engine
        else:
            # Construct reasoning engine from MMKG edges and nodes
            bp_graph = BlueprintGraph(
                name=mmkg.name,
                image_path=mmkg.image_path,
                image_width=mmkg.image_width,
                image_height=mmkg.image_height,
            )
            for nid, node in mmkg.nodes.items():
                from graphite.core.models import ComponentNode
                bp_graph.add_node(ComponentNode(
                    id=node.id,
                    label=node.label,
                    bbox=node.bbox,
                    center=node.get_center(),
                    attributes={**node.attributes, "tag": node.tag} if node.tag else node.attributes,
                ))
            for edge in mmkg.edges:
                bp_graph.add_edge(edge)
            self.engine = TopologicalReasoningEngine(bp_graph)

    def resolve_node_id(self, query_or_id: str) -> Optional[str]:
        """Resolve a query string, tag, or ID to a specific MultimodalNode ID."""
        cleaned = query_or_id.strip()
        # 1. Exact node ID match
        if cleaned in self.mmkg.nodes:
            return cleaned

        # 2. Tag match (e.g. 'P-101', 'V-101')
        for nid, node in self.mmkg.nodes.items():
            if node.tag and node.tag.lower() == cleaned.lower():
                return nid

        # 3. Direct word match against known node IDs or tags in query string
        tokens = re.findall(r"\b[A-Za-z0-9_\-\/]+\b", cleaned)
        for t in tokens:
            if t in self.mmkg.nodes:
                return t
            for nid, node in self.mmkg.nodes.items():
                if node.tag and node.tag.lower() == t.lower():
                    return nid

        # 4. Check for ISA tag in the query string
        tag_match = re.search(r"\b([A-Z]{1,4}[-_]?[0-9]{2,4}[A-Z]?)\b", cleaned, re.IGNORECASE)
        if tag_match:
            candidate_tag = tag_match.group(1).upper()
            for nid, node in self.mmkg.nodes.items():
                if node.tag and node.tag.upper() == candidate_tag:
                    return nid

        # 5. Semantic similarity fallback
        results = self.mmkg.search_by_text(cleaned, top_k=1)
        if results and results[0][1] > 0.15:
            return results[0][0].id

        return None

    def retrieve(self, target_query_or_id: str, k_hop: int = 2) -> Optional[LocalRetrievalContext]:
        """Perform Component-Level Local Retrieval."""
        target_id = self.resolve_node_id(target_query_or_id)
        if not target_id or target_id not in self.mmkg.nodes:
            return None

        node = self.mmkg.nodes[target_id]

        # 1. K-hop subgraph extraction
        subgraph_nodes = []
        subgraph_edges = []
        try:
            subgraph = self.engine.extract_k_hop_subgraph(target_id, k=k_hop)
            for snid, snode in subgraph.nodes.items():
                m_node = self.mmkg.nodes.get(snid)
                subgraph_nodes.append({
                    "id": snid,
                    "tag": m_node.tag if m_node else None,
                    "label": snode.label,
                    "center": snode.get_center(),
                    "visual_crop_path": m_node.visual_crop_path if m_node else None,
                    "specs": m_node.specs if m_node else {},
                })
            for sedge in subgraph.edges:
                subgraph_edges.append({
                    "source": sedge.source,
                    "target": sedge.target,
                    "length": sedge.length,
                    "waypoints": sedge.waypoints,
                })
        except Exception:
            pass

        # 2. Algorithmic flow tracing (upstream & downstream)
        upstream = []
        downstream = []
        try:
            upstream = self.engine.trace_upstream(target_id)
            downstream = self.engine.trace_downstream(target_id)
        except Exception:
            pass

        # 3. Containment isolation valves
        isolation_valves = []
        try:
            isolation_valves = self.engine.find_containment_valves(target_id)
        except Exception:
            pass

        # 4. Redundant bypass paths around this component
        bypasses = []
        try:
            bypasses = self.engine.find_bypasses(target_id)
        except Exception:
            pass

        bbox_tuple = node.bbox.to_tuple() if node.bbox else None

        return LocalRetrievalContext(
            target_node_id=node.id,
            target_tag=node.tag,
            target_label=node.label,
            target_specs=node.specs,
            visual_crop_path=node.visual_crop_path,
            bounding_box=bbox_tuple,
            k_hop=k_hop,
            subsystem_id=node.subsystem_id,
            subsystem_name=node.subsystem_name,
            subgraph_nodes=subgraph_nodes,
            subgraph_edges=subgraph_edges,
            upstream_equipment=upstream,
            downstream_equipment=downstream,
            isolation_valves=isolation_valves,
            active_bypasses=bypasses,
        )


class GlobalRetriever:
    """Plant-level retriever extracting hierarchical subsystem summaries, domain categorizations, and critical cut-valves."""

    def __init__(self, mmkg: MultimodalKnowledgeGraph, reasoning_engine: Optional[TopologicalReasoningEngine] = None):
        self.mmkg = mmkg
        if reasoning_engine is not None:
            self.engine = reasoning_engine
        else:
            bp_graph = BlueprintGraph(name=mmkg.name)
            for nid, node in mmkg.nodes.items():
                from graphite.core.models import ComponentNode
                bp_graph.add_node(ComponentNode(
                    id=node.id,
                    label=node.label,
                    bbox=node.bbox,
                    center=node.get_center(),
                    attributes=node.attributes,
                ))
            for edge in mmkg.edges:
                bp_graph.add_edge(edge)
            self.engine = TopologicalReasoningEngine(bp_graph)

    def retrieve(self, filter_domain: Optional[str] = None) -> GlobalRetrievalContext:
        """Perform Plant-Level Global Retrieval with domain hierarchy."""
        hierarchy = self.mmkg.get_subsystem_hierarchy()
        domains = hierarchy["domains"]

        if filter_domain and filter_domain in domains:
            domains = {filter_domain: domains[filter_domain]}

        # Critical cut-valves across entire plant
        critical_valves = []
        try:
            critical_valves = self.engine.find_critical_cut_valves()
        except Exception:
            pass

        subsystem_summaries = []
        for sub_id, sub_info in self.mmkg.subsystems.items():
            subsystem_summaries.append({
                "subsystem_id": sub_id,
                "name": sub_info.get("name"),
                "domain": sub_info.get("domain_category"),
                "primary_function": sub_info.get("primary_function"),
                "components": len(sub_info.get("component_ids", [])),
                "boundary_valves": sub_info.get("boundary_valves", []),
                "pipe_length": sub_info.get("internal_pipe_length", 0.0),
            })

        return GlobalRetrievalContext(
            plant_name=self.mmkg.name,
            total_equipment_count=len(self.mmkg.nodes),
            total_pipe_segments=len(self.mmkg.edges),
            total_subsystems=len(self.mmkg.subsystems),
            domains=domains,
            critical_cut_valves=critical_valves,
            subsystem_summaries=subsystem_summaries,
        )


class DualModeGraphRAGRetriever:
    """Unified Dual-Mode GraphRAG Retriever routing between Local and Global retrieval."""

    def __init__(self, mmkg: MultimodalKnowledgeGraph, reasoning_engine: Optional[TopologicalReasoningEngine] = None):
        self.mmkg = mmkg
        self.local_retriever = LocalRetriever(mmkg, reasoning_engine)
        self.global_retriever = GlobalRetriever(mmkg, reasoning_engine)

    def route_query(self, query: str) -> str:
        """Classify query into 'local' (component-level) or 'global' (plant-level)."""
        q_lower = query.lower()

        # Check for explicit global indicators
        global_keywords = [
            "plant", "overview", "all subsystems", "summary", "architecture",
            "hierarchy", "domains", "how many subsystems", "entire", "list all",
            "utilities", "safety systems", "water treatment", "cooling system"
        ]
        for kw in global_keywords:
            if kw in q_lower:
                return "global"

        # Check for ISA tag pattern or component query
        if re.search(r"\b([a-z]{1,4}[-_]?[0-9]{2,4}[a-z]?)\b", q_lower):
            return "local"

        # Check for specific component names
        local_keywords = ["isolate", "downstream", "upstream", "bypass", "connected to", "valve", "pump", "tank"]
        for kw in local_keywords:
            if kw in q_lower:
                return "local"

        return "global"

    def retrieve(
        self,
        query: str,
        mode: str = "auto",
        target_id: Optional[str] = None,
        k_hop: int = 2,
    ) -> Tuple[str, Union[LocalRetrievalContext, GlobalRetrievalContext]]:
        """Retrieve grounded context according to determined or specified mode."""
        chosen_mode = mode
        if chosen_mode == "auto":
            chosen_mode = self.route_query(query)

        if chosen_mode == "local":
            target = target_id or query
            ctx = self.local_retriever.retrieve(target, k_hop=k_hop)
            if ctx is not None:
                return "local", ctx
            # Fallback to global if target node couldn't be resolved
            return "global", self.global_retriever.retrieve()

        return "global", self.global_retriever.retrieve()
