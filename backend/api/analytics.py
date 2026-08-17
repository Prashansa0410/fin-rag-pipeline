from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any

from backend.database.session import get_db
from backend.database.models import LLMRequest

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/summary")
def get_analytics_summary(db: Session = Depends(get_db)):
    """
    Returns aggregated KPIs for the dashboard.
    """
    total_queries = db.query(LLMRequest).count()
    if total_queries == 0:
        return {
            "total_queries": 0,
            "avg_latency_ms": 0,
            "total_tokens_saved": 0,
            "review_escalation_rate": 0
        }

    # Averages
    avg_total_latency = db.query(func.avg(LLMRequest.total_latency_ms)).scalar() or 0
    total_tokens_saved = db.query(func.sum(LLMRequest.tokens_removed)).scalar() or 0
    
    # Review escalation rate
    escalated_count = db.query(LLMRequest).filter(LLMRequest.requires_review == True).count()
    escalation_rate = (escalated_count / total_queries) * 100
    
    return {
        "total_queries": total_queries,
        "avg_latency_ms": int(avg_total_latency),
        "total_tokens_saved": total_tokens_saved,
        "review_escalation_rate": round(escalation_rate, 1)
    }

@router.get("/routing")
def get_routing_distribution(db: Session = Depends(get_db)):
    """
    Returns the distribution of model tiers used.
    """
    results = db.query(
        LLMRequest.model_tier, 
        func.count(LLMRequest.id)
    ).group_by(LLMRequest.model_tier).all()
    
    distribution = {
        "economical": 0,
        "standard": 0,
        "advanced": 0
    }
    
    for tier, count in results:
        if tier in distribution:
            distribution[tier] = count
            
    return distribution

@router.get("/latency")
def get_latency_breakdown(db: Session = Depends(get_db)):
    """
    Returns average latency breakdown across all queries.
    """
    avg_query_analysis = db.query(func.avg(LLMRequest.query_analysis_latency_ms)).scalar() or 0
    avg_retrieval = db.query(func.avg(LLMRequest.retrieval_latency_ms)).scalar() or 0
    avg_llm = db.query(func.avg(LLMRequest.llm_latency_ms)).scalar() or 0
    
    return {
        "query_analysis_ms": int(avg_query_analysis),
        "retrieval_ms": int(avg_retrieval),
        "llm_generation_ms": int(avg_llm)
    }
