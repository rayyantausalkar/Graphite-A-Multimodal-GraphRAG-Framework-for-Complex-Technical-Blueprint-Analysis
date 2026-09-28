"""Grounded prompt engineering and answer generator for Dual-Mode GraphRAG."""

from typing import Any, Dict, List, Optional, Tuple, Union

from graphite.rag.context import LocalRetrievalContext, GlobalRetrievalContext, GraphRAGResponse


class GraphRAGGenerator:
    """Synthesizes grounded engineering answers with visual and topological citations."""

    def __init__(self, llm_client: Optional[Any] = None, model_name: str = "graphite-reasoner"):
        self.llm_client = llm_client
        self.model_name = model_name

    def build_prompt(
        self,
        query: str,
        context: Union[LocalRetrievalContext, GlobalRetrievalContext],
        mode: str,
    ) -> str:
        """Construct a grounded prompt incorporating topological context, specs, and visual metadata."""
        if mode == "local" and isinstance(context, LocalRetrievalContext):
            prompt = f"""You are Graphite, an AI Process Engineering Assistant analyzing high-resolution technical blueprints (P&IDs).

GROUNDED TOPOLOGICAL & MULTIMODAL CONTEXT:
Target Component: {context.target_node_id} (Tag: {context.target_tag or 'None'}, Type: {context.target_label})
Subsystem: {context.subsystem_name or 'Unassigned'}
Technical Data Sheet Specs: {context.target_specs}
Visual Symbol Crop: {context.visual_crop_path or 'None'}

Topological Relations ({context.k_hop}-Hop Subgraph):
- Subgraph Equipment Nodes: {[n['id'] for n in context.subgraph_nodes]}
- Upstream Supply Equipment: {context.upstream_equipment}
- Downstream Receiving Equipment: {context.downstream_equipment}
- Required Isolation Cut-Valves: {context.isolation_valves}
- Available Redundant Bypasses: {context.active_bypasses}

USER QUERY:
{query}

INSTRUCTIONS:
1. Provide a rigorous, grounded engineering answer using the topological and multimodal facts above.
2. Directly cite equipment tags and failure isolation valves.
3. Reference the visual crop for component visual verification.
"""
            return prompt
        else:
            g_ctx: GlobalRetrievalContext = context  # type: ignore
            prompt = f"""You are Graphite, an AI Process Engineering Assistant analyzing high-resolution technical blueprints (P&IDs).

GROUNDED PLANT-LEVEL HIERARCHY CONTEXT:
Plant: {g_ctx.plant_name}
Total Equipment: {g_ctx.total_equipment_count} units across {g_ctx.total_pipe_segments} pipe segments
Total Subsystems: {g_ctx.total_subsystems}
Critical Cut-Valves: {g_ctx.critical_cut_valves}

Hierarchical Domains Breakdown:
"""
            for domain, subs in g_ctx.domains.items():
                prompt += f"\nDomain: {domain} ({len(subs)} subsystems)\n"
                for s in subs:
                    prompt += f"  - {s['name']}: {s['component_count']} components | Boundary Valves: {s.get('boundary_valves', [])}\n"

            prompt += f"""
USER QUERY:
{query}

INSTRUCTIONS:
1. Provide a comprehensive plant-wide summary grounded in the hierarchical domains and subsystem units above.
2. Detail the functional distribution across process, utility, and safety systems.
"""
            return prompt

    def generate_grounded_answer(
        self,
        query: str,
        context: Union[LocalRetrievalContext, GlobalRetrievalContext],
        mode: str,
    ) -> GraphRAGResponse:
        """Generate response with exact topological and visual citations."""
        visual_citations: List[str] = []
        topological_citations: List[str] = []

        if mode == "local" and isinstance(context, LocalRetrievalContext):
            # Collect citations
            if context.visual_crop_path:
                visual_citations.append(context.visual_crop_path)
            for snode in context.subgraph_nodes:
                if snode.get("visual_crop_path") and snode["visual_crop_path"] not in visual_citations:
                    visual_citations.append(snode["visual_crop_path"])
                if snode.get("tag"):
                    topological_citations.append(snode["tag"])
                else:
                    topological_citations.append(snode["id"])

            for v in context.isolation_valves:
                if v not in topological_citations:
                    topological_citations.append(v)

            # Synthesize grounded answer
            target_disp = context.target_tag or context.target_node_id
            answer_parts = [
                f"### Analysis for Equipment {target_disp} ({context.target_label.upper()})\n",
                f"- **Subsystem Affiliation**: {context.subsystem_name or 'Unassigned'}",
            ]
            if context.target_specs:
                spec_str = ", ".join(f"{k}: {v}" for k, v in context.target_specs.items())
                answer_parts.append(f"- **Technical Specifications**: {spec_str}")

            if context.upstream_equipment:
                answer_parts.append(f"- **Upstream Supply Inflow**: {', '.join(context.upstream_equipment)}")
            if context.downstream_equipment:
                answer_parts.append(f"- **Downstream Discharge Path**: {', '.join(context.downstream_equipment)}")

            if context.isolation_valves:
                answer_parts.append(
                    f"- **Safety Containment**: To isolate {target_disp} during maintenance or leak events, "
                    f"close boundary valve(s): **{', '.join(context.isolation_valves)}**."
                )
            else:
                answer_parts.append(
                    f"- **Safety Containment**: No dedicated isolation boundary valves detected in immediate vicinity."
                )

            if context.active_bypasses:
                bp_strs = [" -> ".join(p) for p in context.active_bypasses]
                answer_parts.append(f"- **Redundant Bypass Paths**: Available via: {'; '.join(bp_strs)}")

            grounded_answer = "\n".join(answer_parts)

        else:
            g_ctx: GlobalRetrievalContext = context  # type: ignore
            # Global synthesis
            for s in g_ctx.subsystem_summaries:
                topological_citations.append(s["name"])

            answer_parts = [
                f"### Plant-Wide Topological Summary: {g_ctx.plant_name}\n",
                f"The facility contains **{g_ctx.total_equipment_count} physical equipment assets** interconnected across **{g_ctx.total_pipe_segments} process pipe lines**, partitioned into **{g_ctx.total_subsystems} functional subsystems**.\n",
                "#### Functional Domain Breakdown:",
            ]

            for domain, subs in g_ctx.domains.items():
                if subs:
                    answer_parts.append(f"\n**{domain} ({len(subs)} Subsystems):**")
                    for s in subs:
                        b_valves = f" [Boundary Valves: {', '.join(s['boundary_valves'])}]" if s.get("boundary_valves") else ""
                        answer_parts.append(f"- **{s['name']}**: {s['component_count']} components{b_valves}")

            if g_ctx.critical_cut_valves:
                answer_parts.append(
                    f"\n**Critical Plant Articulation Valves**: The following cut-valves maintain topological plant continuity: "
                    f"**{', '.join(g_ctx.critical_cut_valves)}**."
                )

            grounded_answer = "\n".join(answer_parts)

        return GraphRAGResponse(
            query=query,
            retrieval_mode=mode,
            grounded_answer=grounded_answer,
            context=context,
            visual_citations=visual_citations,
            topological_citations=topological_citations,
        )
