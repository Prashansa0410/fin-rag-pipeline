import time
import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List

from backend.database.session import get_db
from backend.database.models import ResearchQuery, LLMRequest, ReviewItem, QueryType
from backend.retrieval.analyzer import query_analyzer
from backend.retrieval.search import searcher
from backend.retrieval.confidence import confidence_analyzer
from backend.routing.context_manager import context_budget_manager
from backend.routing.router import router as intelligent_router
from backend.llm.registry import registry
from backend.llm.huggingface import huggingface_provider
from backend.llm.validator import grounding_validator
from backend.llm.prompts import prompt_manager

router = APIRouter(prefix="/api/research", tags=["research"])

class ResearchRequest(BaseModel):
    user_id: str
    organization_id: str
    query: str

@router.post("/")
async def perform_research(request: ResearchRequest, db: Session = Depends(get_db)):
    try:
        t_start = time.perf_counter()
        
        # 1. Query Analysis
        analysis = query_analyzer.analyze(request.query)
        
        # 2. Hybrid Retrieval
        raw_results, metrics = searcher.search(db, request.query, filters=analysis["filters"], organization_id=request.organization_id)
        
        # 3. Confidence & Conflict Detection
        conf_score, conf_level, has_conflict, diverse_results = confidence_analyzer.analyze_confidence(raw_results)
        
        # 4. Context Budgeting (initial estimate using standard tier)
        context_opt = context_budget_manager.optimize_context("standard", request.query, diverse_results)
        final_chunks = context_opt["optimized_chunks"]
        
        # 5. Intelligent Routing & Fail-Safe
        if context_opt["optimized_context_tokens"] == 0:
            routing_decision = {
                "tier": "standard",
                "reason": "FAIL-SAFE: Zero retrieval context available.",
                "requires_review": True
            }
        else:
            routing_decision = intelligent_router.route_query(
                query_type=analysis["query_type"],
                retrieval_confidence=conf_score,
                context_tokens=context_opt["optimized_context_tokens"],
                risk_level="HIGH" if analysis["is_high_risk"] else "LOW",
                conflicting_evidence=has_conflict
            )
        
        target_tier = routing_decision["tier"]
        
        # (Optional) Re-optimize context
        context_opt = context_budget_manager.optimize_context(target_tier, request.query, diverse_results)
        final_chunks = context_opt["optimized_chunks"]
        
        model_info = registry.get_model_info(target_tier)
        model_id = model_info["model_id"] if model_info else "meta-llama/Llama-3.1-8B-Instruct"
        
        if context_opt["optimized_context_tokens"] == 0:
            generated_answer = "Insufficient evidence found in the retrieved context to answer this query safely."
            usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            t_gen_end = time.perf_counter()
        else:
            prompt = prompt_manager.build_research_prompt(request.query, final_chunks)
            
            t_gen_start = time.perf_counter()
            try:
                response = await huggingface_provider.generate(model_id, prompt)
                generated_answer = response["answer"]
                usage = response["usage"]
            except Exception as e:
                # Include the type of the error so we can distinguish between 400 Bad Request vs network timeouts
                raise HTTPException(status_code=500, detail=f"LLM Provider Error: {type(e).__name__} - {str(e)}")
            t_gen_end = time.perf_counter()
        
        # 7. Grounding Validation
        is_grounded, validation_reason, val_latency = await grounding_validator.validate_grounding(
            request.query, generated_answer, final_chunks
        )
        
        # Fallback Regeneration (Once)
        val_latency2 = 0
        if not is_grounded and context_opt["optimized_context_tokens"] > 0:
            regenerate_prompt = prompt_manager.build_regeneration_prompt(request.query, final_chunks)
            
            t_regen_start = time.perf_counter()
            try:
                response2 = await huggingface_provider.generate(model_id, regenerate_prompt)
                generated_answer = response2["answer"]
                usage2 = response2["usage"]
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"LLM Provider Error (Regeneration): {type(e).__name__} - {str(e)}")
                
            val_latency2_start = time.perf_counter()
            
            # Second validation
            is_grounded, validation_reason, val_latency2_val = await grounding_validator.validate_grounding(
                request.query, generated_answer, final_chunks
            )
            val_latency2 = int((time.perf_counter() - t_regen_start) * 1000)
            val_latency += val_latency2_val
            
            # Accumulate usage
            usage["input_tokens"] += usage2["input_tokens"]
            usage["output_tokens"] += usage2["output_tokens"]
            usage["total_tokens"] += usage2["total_tokens"]
            
        t_end = time.perf_counter()
        
        # 8. Flag for Review if necessary
        requires_review = routing_decision["requires_review"] or not is_grounded
        
        # Save to Database
        db_query = ResearchQuery(
            user_id=request.user_id,
            query_text=request.query,
            query_type=analysis["query_type"]
        )
        db.add(db_query)
        db.flush()
        
        db_request = LLMRequest(
            query_id=db_query.id,
            provider="huggingface",
            model=model_id,
            model_tier=target_tier,
            routing_reason=routing_decision["reason"],
            total_latency_ms=int((t_end - t_start) * 1000),
            query_analysis_latency_ms=metrics["query_analysis_latency_ms"],
            retrieval_latency_ms=metrics["vector_search_latency_ms"] + metrics["keyword_search_latency_ms"] + metrics["merge_latency_ms"],
            llm_latency_ms=int((t_gen_end - t_gen_start) * 1000) if context_opt["optimized_context_tokens"] > 0 else 0,
            grounding_latency_ms=int(val_latency * 1000),
            regeneration_latency_ms=val_latency2,
            candidate_context_tokens=context_opt["original_context_tokens"],
            final_context_tokens=context_opt["optimized_context_tokens"],
            tokens_removed=context_opt["tokens_saved"],
            retrieval_confidence=conf_score,
            retrieval_confidence_level=conf_level,
            conflicting_evidence_detected=has_conflict,
            answer_text=generated_answer,
            requires_review=requires_review,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            total_tokens=usage["total_tokens"]
        )
        db.add(db_request)
        db.flush()
        
        if requires_review:
            review_item = ReviewItem(llm_request_id=db_request.id, status="PENDING")
            db.add(review_item)
            
        db.commit()
        
        return {
            "answer": generated_answer,
            "is_grounded": is_grounded,
            "validation_reason": validation_reason,
            "requires_review": requires_review,
            "confidence": conf_level,
            "selected_model_tier": target_tier,
            "citations": [{"source_id": c.get("metadata", {}).get("source_id", "Unknown")} for c in final_chunks],
            "metrics": {
                "latency": db_request.total_latency_ms,
                "tier": target_tier
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_msg)
