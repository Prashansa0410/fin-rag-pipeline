import time
import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database.session import get_db
from backend.database.models import ResearchQuery, LLMRequest, ReviewItem
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


def _estimated_registry_cost(tier: str, input_tokens: int, output_tokens: int) -> float:
    info = registry.get_model_info(tier)
    return (input_tokens / 1000.0) * info.get("input_cost", 0.0) + (output_tokens / 1000.0) * info.get("output_cost", 0.0)


@router.post("/")
async def perform_research(request: ResearchRequest, db: Session = Depends(get_db)):
    try:
        t_start = time.perf_counter()
        analysis = query_analyzer.analyze(request.query)
        raw_results, metrics = searcher.search(db, request.query, filters=analysis["filters"], organization_id=request.organization_id)
        conf_score, conf_level, has_conflict, diverse_results = confidence_analyzer.analyze_confidence(raw_results)

        context_opt = context_budget_manager.optimize_context("standard", request.query, diverse_results)
        if context_opt["optimized_context_tokens"] == 0:
            routing_decision = {"tier": "standard", "reason": "FAIL-SAFE: Zero retrieval context available.", "requires_review": True}
        else:
            routing_decision = intelligent_router.route_query(
                query_type=analysis["query_type"], retrieval_confidence=conf_score,
                context_tokens=context_opt["optimized_context_tokens"],
                risk_level="HIGH" if analysis["is_high_risk"] else "LOW",
                conflicting_evidence=has_conflict,
            )

        target_tier = routing_decision["tier"]
        context_opt = context_budget_manager.optimize_context(target_tier, request.query, diverse_results)
        final_chunks = context_opt["optimized_chunks"]
        model_id = registry.get_model_info(target_tier)["model_id"]
        usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "estimated_cost": 0.0}
        llm_latency_ms = 0
        regeneration_latency_ms = 0

        if context_opt["optimized_context_tokens"] == 0:
            generated_answer = "Insufficient evidence found in the retrieved context to answer this query safely."
        else:
            prompt = prompt_manager.build_research_prompt(request.query, final_chunks)
            t_gen_start = time.perf_counter()
            try:
                response = await huggingface_provider.generate(model_id, prompt)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"LLM Provider Error: {type(e).__name__} - {e}")
            llm_latency_ms = int((time.perf_counter() - t_gen_start) * 1000)
            generated_answer = response["answer"]
            usage = response.get("usage", usage)

        # Validator latency is already milliseconds. Never multiply it by 1000.
        is_grounded, validation_reason, grounding_latency_ms = await grounding_validator.validate_grounding(
            request.query, generated_answer, final_chunks
        )
        validation_estimated_cost = _estimated_registry_cost(
            "economical", context_opt["optimized_context_tokens"], 150
        ) if final_chunks else 0.0

        if not is_grounded and context_opt["optimized_context_tokens"] > 0:
            regenerate_prompt = prompt_manager.build_regeneration_prompt(request.query, final_chunks)
            t_regen_start = time.perf_counter()
            try:
                response2 = await huggingface_provider.generate(model_id, regenerate_prompt)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"LLM Provider Error (Regeneration): {type(e).__name__} - {e}")
            regeneration_latency_ms = int((time.perf_counter() - t_regen_start) * 1000)
            generated_answer = response2["answer"]
            usage2 = response2.get("usage", {})
            usage["input_tokens"] += usage2.get("input_tokens", 0)
            usage["output_tokens"] += usage2.get("output_tokens", 0)
            usage["total_tokens"] += usage2.get("total_tokens", 0)
            usage["estimated_cost"] = (usage.get("estimated_cost") or 0.0) + (usage2.get("estimated_cost") or 0.0)

            is_grounded, validation_reason, second_grounding_latency_ms = await grounding_validator.validate_grounding(
                request.query, generated_answer, final_chunks
            )
            grounding_latency_ms += second_grounding_latency_ms
            validation_estimated_cost += _estimated_registry_cost(
                "economical", context_opt["optimized_context_tokens"], 150
            )

        t_end = time.perf_counter()
        requires_review = routing_decision["requires_review"] or not is_grounded

        actual_main_cost = usage.get("estimated_cost")
        if actual_main_cost is None:
            actual_main_cost = _estimated_registry_cost(target_tier, usage["input_tokens"], usage["output_tokens"])
        total_estimated_cost = float(actual_main_cost or 0.0) + validation_estimated_cost
        baseline_cost = _estimated_registry_cost("advanced", usage["input_tokens"], usage["output_tokens"])
        routing_savings = max(0.0, baseline_cost - total_estimated_cost)

        db_query = ResearchQuery(user_id=request.user_id, query_text=request.query, query_type=analysis["query_type"])
        db.add(db_query)
        db.flush()
        db_request = LLMRequest(
            query_id=db_query.id, provider="huggingface", model=model_id, model_tier=target_tier,
            routing_reason=routing_decision["reason"], total_latency_ms=int((t_end - t_start) * 1000),
            query_analysis_latency_ms=metrics["query_analysis_latency_ms"],
            retrieval_latency_ms=metrics["vector_search_latency_ms"] + metrics["keyword_search_latency_ms"] + metrics["merge_latency_ms"],
            llm_latency_ms=llm_latency_ms, grounding_latency_ms=int(grounding_latency_ms),
            regeneration_latency_ms=regeneration_latency_ms,
            candidate_context_tokens=context_opt["original_context_tokens"], final_context_tokens=context_opt["optimized_context_tokens"],
            tokens_removed=context_opt["tokens_saved"], retrieval_confidence=conf_score,
            retrieval_confidence_level=conf_level, conflicting_evidence_detected=has_conflict,
            answer_text=generated_answer, requires_review=requires_review,
            input_tokens=usage["input_tokens"], output_tokens=usage["output_tokens"], total_tokens=usage["total_tokens"],
            estimated_cost=total_estimated_cost, baseline_cost=baseline_cost, routing_savings=routing_savings,
        )
        db.add(db_request)
        db.flush()
        if requires_review:
            db.add(ReviewItem(llm_request_id=db_request.id, status="PENDING"))
        db.commit()

        return {
            "answer": generated_answer, "is_grounded": is_grounded, "validation_reason": validation_reason,
            "requires_review": requires_review, "confidence": conf_level, "selected_model_tier": target_tier,
            "citations": [{"source_id": c.get("metadata", {}).get("source_id", "Unknown")} for c in final_chunks],
            "metrics": {
                "latency": db_request.total_latency_ms, "tier": target_tier, "model": model_id,
                "estimated_cost": total_estimated_cost, "baseline_cost": baseline_cost,
                "routing_savings": routing_savings, "llm_latency_ms": llm_latency_ms,
                "grounding_latency_ms": int(grounding_latency_ms), "regeneration_latency_ms": regeneration_latency_ms,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
