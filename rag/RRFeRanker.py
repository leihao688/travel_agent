"""
RRF (Reciprocal Rank Fusion) 重排序器

加权 RRF 公式：RRF_score(doc) = Σ(weight_i / (k + rank_i))
其中 k 是常数（通常取60），rank_i 是文档在第 i 个检索结果中的排名，
weight_i 是该检索器的权重。
"""

from typing import List, Dict, Optional
from langchain_core.documents import Document


class RRFRanker:
    """RRF 重排序器（支持加权）"""

    def __init__(self, k: int = 60):
        self.k = k

    def rank_fusion(
            self,
            doc_lists: List[List[Document]],
            top_k: int = 5,
            weights: Optional[List[float]] = None
    ) -> List[Document]:
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        if weights is None:
            weights = [1.0] * len(doc_lists)

        for doc_list, weight in zip(doc_lists, weights):
            for rank, doc in enumerate(doc_list, start=1):
                parent_id = doc.metadata.get('parent_chunk_id', '')
                sub_idx = doc.metadata.get('sub_chunk_index', '')
                if parent_id and sub_idx != '':
                    doc_id = f"{parent_id}_{sub_idx}"
                else:
                    doc_id = doc.metadata.get('id', doc.page_content[:100])

                if doc_id not in rrf_scores:
                    rrf_scores[doc_id] = 0.0
                    doc_map[doc_id] = doc

                rrf_scores[doc_id] += weight / (self.k + rank)

        sorted_doc_ids = sorted(
            rrf_scores.keys(),
            key=lambda x: rrf_scores[x],
            reverse=True
        )

        result_docs = []
        for doc_id in sorted_doc_ids[:top_k]:
            doc = doc_map[doc_id]
            doc.metadata['rrf_score'] = rrf_scores[doc_id]
            result_docs.append(doc)

        return result_docs

    def rerank(
            self,
            query: str,
            retrievers: List,
            top_k: int = 5,
            weights: Optional[List[float]] = None
    ) -> List[Document]:
        doc_lists = []
        for retriever in retrievers:
            docs = retriever.invoke(query)
            doc_lists.append(docs)

        return self.rank_fusion(doc_lists, top_k, weights)
