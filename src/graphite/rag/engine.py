"""Master Dual-Mode GraphRAG Engine coordinating retrieval and grounded generation."""

from typing import Any, Dict, List, Optional, Tuple, Union

from graphite.mmkg.representation import MultimodalKnowledgeGraph
from graphite.reasoning.engine import TopologicalReasoningEngine
from graphite.rag.context import LocalRetrievalContext, GlobalRetrievalContext, GraphRAGResponse
from graphite.rag.retriever import DualModeGraphRAGRetriever
from graphite.rag.generator import GraphRAGGenerator


class GraphRAGEngine:
    """End-to-end Dual-Mode GraphRAG Engine for engineering blueprints."""

    def __init__(
        self,
        mmkg: MultimodalKnowledgeGraph,
        reasoning_engine: Optional[TopologicalReasoningEngine] = None,
        llm_client: Optional[Any] = None,
    ):
        self.mmkg = mmkg
        self.retriever = DualModeGraphRAGRetriever(mmkg, reasoning_engine)
        self.generator = GraphRAGGenerator(llm_client)

    def query(
        self,
        query_str: str,
        mode: str = "auto",
        target_id: Optional[str] = None,
        k_hop: int = 2,
    ) -> GraphRAGResponse:
        """Process user query through dual-mode retrieval and grounded generation."""
        retrieval_mode, context = self.retriever.retrieve(
            query=query_str,
            mode=mode,
            target_id=target_id,
            k_hop=k_hop,
        )
        return self.generator.generate_grounded_answer(
            query=query_str,
            context=context,
            mode=retrieval_mode,
        )
