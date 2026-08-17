import re
import time
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func
from backend.database.models import DocumentChunk, DocumentVersion, Document
from backend.embeddings.provider import embedding_provider
from backend.config import settings


class HybridSearcher:
    def __init__(self):
        pass

    @staticmethod
    def _terms(text: str) -> List[str]:
        return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1]

    def _lexical_score(self, query: str, content: str, filename: str) -> float:
        query_terms = set(self._terms(query))
        if not query_terms:
            return 0.0
        doc_terms = set(self._terms(f"{filename} {content}"))
        return len(query_terms & doc_terms) / len(query_terms)

    def search(self, db: Session, query: str, filters: Dict[str, Any] = None, top_k: int = 15, organization_id: str = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        filters = filters or {}
        t0 = time.perf_counter()
        query_embedding = embedding_provider.embed_text(query)

        base_query = (
            select(
                DocumentChunk,
                DocumentVersion,
                Document,
                DocumentChunk.embedding.cosine_distance(query_embedding).label("vector_distance")
            )
            .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(DocumentVersion.is_current_version == True)
        )

        if "partner" in filters:
            base_query = base_query.where(Document.partner == filters["partner"])
        if "business_domain" in filters:
            base_query = base_query.where(
                (Document.business_domain == filters["business_domain"]) |
                (Document.business_domain.is_(None)) |
                (Document.business_domain == "")
            )
        if organization_id:
            base_query = base_query.where(Document.organization_id == organization_id)

        t1 = time.perf_counter()
        vector_candidates = db.execute(base_query.order_by("vector_distance").limit(top_k * 3)).all()
        t2 = time.perf_counter()

        ts_query_str = " & ".join([word for word in query.replace("'", "").split() if word.isalnum()])
        keyword_candidates = []
        if ts_query_str:
            kw_query = (
                select(
                    DocumentChunk,
                    DocumentVersion,
                    Document,
                    func.ts_rank(DocumentChunk.fts_vector, func.to_tsquery("english", ts_query_str)).label("rank")
                )
                .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
                .join(Document, DocumentVersion.document_id == Document.id)
                .where(DocumentVersion.is_current_version == True)
                .where(DocumentChunk.fts_vector.op("@@")(func.to_tsquery("english", ts_query_str)))
            )
            if "partner" in filters:
                kw_query = kw_query.where(Document.partner == filters["partner"])
            if "business_domain" in filters:
                kw_query = kw_query.where(
                    (Document.business_domain == filters["business_domain"]) |
                    (Document.business_domain.is_(None)) |
                    (Document.business_domain == "")
                )
            if organization_id:
                kw_query = kw_query.where(Document.organization_id == organization_id)
            keyword_candidates = db.execute(kw_query.order_by(desc("rank")).limit(top_k * 2)).all()

        t3 = time.perf_counter()
        merged_results = {}

        for chunk, version, doc, distance in vector_candidates:
            similarity = max(0.0, 1.0 - (distance / 2.0))
            merged_results[chunk.id] = {
                "chunk": chunk, "version": version, "doc": doc,
                "vector_score": similarity, "keyword_score": 0.0
            }

        for chunk, version, doc, rank in keyword_candidates:
            normalized_rank = min(1.0, float(rank))
            if chunk.id in merged_results:
                merged_results[chunk.id]["keyword_score"] = max(
                    merged_results[chunk.id]["keyword_score"], normalized_rank
                )
            else:
                merged_results[chunk.id] = {
                    "chunk": chunk, "version": version, "doc": doc,
                    "vector_score": 0.0, "keyword_score": normalized_rank
                }

        final_list = []
        for data in merged_results.values():
            chunk = data["chunk"]
            doc = data["doc"]
            lexical_score = self._lexical_score(query, chunk.content, doc.filename)
            combined = (
                settings.VECTOR_WEIGHT * data["vector_score"] +
                settings.KEYWORD_WEIGHT * data["keyword_score"] +
                settings.LEXICAL_WEIGHT * lexical_score
            )
            data["lexical_score"] = lexical_score
            data["combined_score"] = combined
            final_list.append(data)

        final_list.sort(key=lambda x: x["combined_score"], reverse=True)
        t4 = time.perf_counter()

        metrics = {
            "query_analysis_latency_ms": int((t1 - t0) * 1000),
            "vector_search_latency_ms": int((t2 - t1) * 1000),
            "keyword_search_latency_ms": int((t3 - t2) * 1000),
            "merge_latency_ms": int((t4 - t3) * 1000),
            "candidate_count": len(final_list)
        }

        formatted_results = []
        for item in final_list[:top_k]:
            chunk = item["chunk"]
            doc = item["doc"]
            formatted_results.append({
                "id": str(chunk.id),
                "content": chunk.content,
                "metadata": chunk.chunk_metadata,
                "page_number": chunk.page_number,
                "section": chunk.section,
                "document_name": doc.filename,
                "partner": doc.partner,
                "business_domain": doc.business_domain,
                "score": item["combined_score"],
                "vector_score": item["vector_score"],
                "keyword_score": item["keyword_score"],
                "lexical_score": item["lexical_score"]
            })

        return formatted_results, metrics


searcher = HybridSearcher()
