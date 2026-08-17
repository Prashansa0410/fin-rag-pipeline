from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Dict, Any
from uuid import UUID

from backend.database.session import get_db
from backend.database.models import ReviewItem, LLMRequest, ResearchQuery, ReviewDecision
from pydantic import BaseModel

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

class ReviewAction(BaseModel):
    reviewer_id: str
    decision: str # "APPROVE", "EDIT", "REJECT"
    edited_answer: str = None
    comment: str = None

@router.get("/pending")
def get_pending_reviews(db: Session = Depends(get_db)):
    """
    Fetches all pending review items.
    """
    stmt = (
        select(ReviewItem)
        .where(ReviewItem.status == "PENDING")
    )
    reviews = db.execute(stmt).scalars().all()
    
    results = []
    for r in reviews:
        req = r.llm_request
        query = req.query
        
        results.append({
            "review_id": str(r.id),
            "query_text": query.query_text,
            "query_type": query.query_type,
            "original_answer": req.answer_text,
            "retrieval_confidence": req.retrieval_confidence,
            "retrieval_confidence_level": req.retrieval_confidence_level,
            "conflicting_evidence": req.conflicting_evidence_detected,
            "model_tier": req.model_tier,
            "routing_reason": req.routing_reason,
            "created_at": r.created_at
        })
        
    return results

@router.get("/{review_id}")
def get_review_detail(review_id: UUID, db: Session = Depends(get_db)):
    """
    Gets detailed information for a single review item, including evidence chunks.
    (In a real app, evidence chunks would be reconstructed or stored with the LLMRequest).
    """
    item = db.get(ReviewItem, review_id)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
        
    req = item.llm_request
    query = req.query
    
    return {
        "review_id": str(item.id),
        "status": item.status,
        "query_text": query.query_text,
        "query_type": query.query_type,
        "original_answer": req.answer_text,
        "retrieval_confidence": req.retrieval_confidence,
        "retrieval_confidence_level": req.retrieval_confidence_level,
        "conflicting_evidence": req.conflicting_evidence_detected,
        "model_tier": req.model_tier,
        "routing_reason": req.routing_reason,
        "metrics": {
            "total_latency_ms": req.total_latency_ms,
            "candidate_context_tokens": req.candidate_context_tokens,
            "final_context_tokens": req.final_context_tokens,
            "tokens_removed": req.tokens_removed
        }
    }

@router.post("/{review_id}/action")
def perform_review_action(review_id: UUID, action: ReviewAction, db: Session = Depends(get_db)):
    """
    Approve, Edit, or Reject a pending review.
    """
    item = db.get(ReviewItem, review_id)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
        
    if item.status != "PENDING":
        raise HTTPException(status_code=400, detail="Review item is no longer pending")
        
    decision = ReviewDecision(
        review_item_id=item.id,
        reviewer_id=action.reviewer_id,
        decision=action.decision,
        edited_answer=action.edited_answer if action.decision == "EDIT" else None,
        comment=action.comment
    )
    db.add(decision)
    
    # Update the review item status
    item.status = "COMPLETED"
    
    # If approved or edited, update the final answer on the LLM request
    if action.decision == "EDIT":
        item.llm_request.answer_text = action.edited_answer
        
    db.commit()
    
    return {"status": "success", "review_id": str(review_id)}
