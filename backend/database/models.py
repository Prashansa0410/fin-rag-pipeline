import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, DateTime, JSON, Enum
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from pgvector.sqlalchemy import Vector
import enum

Base = declarative_base()

class Role(str, enum.Enum):
    USER = "USER"
    REVIEWER = "REVIEWER"
    ADMIN = "ADMIN"

class DocumentStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    INDEXING = "INDEXING"
    READY = "READY"
    FAILED = "FAILED"

class QueryType(str, enum.Enum):
    SIMPLE_FACT = "SIMPLE_FACT"
    SUMMARY = "SUMMARY"
    COMPARISON = "COMPARISON"
    MULTI_DOCUMENT_ANALYSIS = "MULTI_DOCUMENT_ANALYSIS"
    COMPLIANCE = "COMPLIANCE"
    FINANCIAL_ANALYSIS = "FINANCIAL_ANALYSIS"
    TECHNICAL_DOCUMENTATION = "TECHNICAL_DOCUMENTATION"
    HIGH_RISK = "HIGH_RISK"
    UNKNOWN = "UNKNOWN"

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    users = relationship("User", back_populates="organization")
    documents = relationship("Document", back_populates="organization")

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(Role), default=Role.USER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    organization = relationship("Organization", back_populates="users")
    queries = relationship("ResearchQuery", back_populates="user")
    reviews = relationship("ReviewDecision", back_populates="reviewer")

class Document(Base):
    __tablename__ = "documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    filename = Column(String(255), nullable=False)
    document_type = Column(String(50))
    partner = Column(String(100))
    business_domain = Column(String(100))
    country = Column(String(100))
    compliance_category = Column(String(100))
    effective_date = Column(DateTime)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    organization = relationship("Organization", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document")

class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    version = Column(Integer, default=1)
    file_path = Column(String(512), nullable=False)
    mime_type = Column(String(100))
    file_size = Column(Integer)
    is_current_version = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    document = relationship("Document", back_populates="versions")
    chunks = relationship("DocumentChunk", back_populates="version")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id = Column(UUID(as_uuid=True), ForeignKey("document_versions.id"))
    content = Column(Text, nullable=False)
    page_number = Column(Integer)
    section = Column(String(255))
    chunk_index = Column(Integer)
    embedding = Column(Vector(384)) # Assuming all-MiniLM-L6-v2 which has 384 dims
    fts_vector = Column(TSVECTOR)
    chunk_metadata = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    version = relationship("DocumentVersion", back_populates="chunks")

class ResearchQuery(Base):
    __tablename__ = "research_queries"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    query_text = Column(Text, nullable=False)
    query_type = Column(Enum(QueryType), default=QueryType.UNKNOWN)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="queries")
    llm_request = relationship("LLMRequest", back_populates="query", uselist=False)

class LLMRequest(Base):
    __tablename__ = "llm_requests"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID(as_uuid=True), ForeignKey("research_queries.id"))
    provider = Column(String(50))
    model = Column(String(100))
    model_tier = Column(String(50))
    routing_reason = Column(Text)
    
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    total_tokens = Column(Integer)
    
    estimated_cost = Column(Float)
    baseline_cost = Column(Float)
    routing_savings = Column(Float)
    
    total_latency_ms = Column(Integer)
    query_analysis_latency_ms = Column(Integer)
    retrieval_latency_ms = Column(Integer)
    llm_latency_ms = Column(Integer)
    grounding_latency_ms = Column(Integer, default=0)
    regeneration_latency_ms = Column(Integer, default=0)
    
    candidate_context_tokens = Column(Integer)
    final_context_tokens = Column(Integer)
    tokens_removed = Column(Integer)
    
    cache_hit = Column(Boolean, default=False)
    fallback_used = Column(Boolean, default=False)
    
    retrieval_confidence = Column(Float)
    retrieval_confidence_level = Column(String(20)) # HIGH, MEDIUM, LOW
    conflicting_evidence_detected = Column(Boolean, default=False)
    
    answer_text = Column(Text)
    requires_review = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    query = relationship("ResearchQuery", back_populates="llm_request")
    review_item = relationship("ReviewItem", back_populates="llm_request", uselist=False)

class ReviewItem(Base):
    __tablename__ = "review_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    llm_request_id = Column(UUID(as_uuid=True), ForeignKey("llm_requests.id"))
    status = Column(String(50), default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    llm_request = relationship("LLMRequest", back_populates="review_item")
    decisions = relationship("ReviewDecision", back_populates="review_item")

class ReviewDecision(Base):
    __tablename__ = "review_decisions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_item_id = Column(UUID(as_uuid=True), ForeignKey("review_items.id"))
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    decision = Column(String(50)) # APPROVE, EDIT, REJECT
    edited_answer = Column(Text)
    comment = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    review_item = relationship("ReviewItem", back_populates="decisions")
    reviewer = relationship("User", back_populates="reviews")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(100))
    audit_metadata = Column(JSONB)
    timestamp = Column(DateTime, default=datetime.utcnow)
