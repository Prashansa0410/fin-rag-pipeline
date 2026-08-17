import re
import time
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func
from backend.database.models import DocumentChunk, DocumentVersion, Document
from backend.embeddings.provider import embedding_provider
from backend.config import settings
from backend.retrieval.relevance import relevance_scorer


class HybridSearcher:
    def __init__(self):
        pass

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

        # Use PostgreSQL FTS as a recall mechanism. Exact phrase/term relevance is
        # handled deterministically below so broad FTS matches do not flood context.
        query_words = [w for w in re.findall(r"[a-zA-Z0-9]+", query) if len(w) > 1]
        ts_query_str = " & ".join(query_words)
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
            keyword_candidates = db.execute(kw_query.order_by(desc("rank")).limit(top_k * 3)).all()

        t3 = time.perf_counter()
        merged_results = {}

        for chunk, version, doc, distance in vector_candidates:
            similarity = max(0.0, 1.0 - (float(distance) / 2.0))
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
        query_lower = query.lower()
        for data in merged_results.values():
            chunk = data["chunk"]
            doc = data["doc"]
            relevance = relevance_scorer.score(query, chunk.content, doc.filename)

            # Favor exact operational terminology while retaining semantic recall.
            combined = (
                settings.VECTOR_WEIGHT * data["vector_score"] +
                settings.KEYWORD_WEIGHT * data["keyword_score"] +
                settings.LEXICAL_WEIGHT * relevance["lexical"]
            )
            combined += 0.10 * relevance["filename"]
            combined += 0.10 * relevance["phrase"]

            # A direct phrase/identifier match should not be buried by unrelated
            # semantically similar documents.
            if relevance["phrase"] > 0:
                combined += 0.10

            data.update({
                "lexical_score": relevance["lexical"],
                "filename_score": relevance["filename"],
                "phrase_score": relevance["phrase"],
                "combined_score": combined,
            })
            final_list.append(data)

        final_list.sort(key=lambda x: x["combined_score"], reverse=True)

        # Relevance gate: for ordinary factual queries, do not pass a long tail of
        # weakly related chunks into the LLM. Keep a small fallback set when the
        # query genuinely has weak lexical evidence so semantic retrieval can still work.
        if final_list:
            top_score = final_list[0]["combined_score"]
            is_comparison = "compare" in query_lower or "difference" in query_lower
            threshold = max(0.32, top_score * 0.72)
            gated = [r for r in final_list if r["combined_score"] >= threshold]
            max_results = min(top_k, 8 if is_comparison else 5)
            final_list = gated[:max_results]

        t4 = time.perf_counter()
        metrics = {
            "query_analysis_latency_ms": int((t1 - t0) * 1000),
            "vector_search_latency_ms": int((t2 - t1) * 1000),
            "keyword_search_latency_ms": int((t3 - t2) * 1000),
            "merge_latency_ms": int((t4 - t3) * 1000),
            "candidate_count": len(merged_results),
            "returned_count": len(final_list),
        }

        formatted_results = []
        for item in final_list:
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
                "lexical_score": item["lexical_score"],
                "filename_score": item["filename_score"],
                "phrase_score": item["phrase_score"],
            })

        return formatted_results, metrics


searcher = HybridSearcher()
