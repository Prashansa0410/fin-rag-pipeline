"""add observability columns idempotently

Revision ID: 001_add_observability
Revises: 
Create Date: 2026-08-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_add_observability'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Use idempotent raw SQL to add all potentially missing columns
    op.execute("""
    DO $$
    BEGIN
        BEGIN
            ALTER TABLE llm_requests ADD COLUMN estimated_cost FLOAT;
        EXCEPTION WHEN duplicate_column THEN END;
        BEGIN
            ALTER TABLE llm_requests ADD COLUMN baseline_cost FLOAT;
        EXCEPTION WHEN duplicate_column THEN END;
        BEGIN
            ALTER TABLE llm_requests ADD COLUMN routing_savings FLOAT;
        EXCEPTION WHEN duplicate_column THEN END;
        BEGIN
            ALTER TABLE llm_requests ADD COLUMN grounding_latency_ms INTEGER DEFAULT 0;
        EXCEPTION WHEN duplicate_column THEN END;
        BEGIN
            ALTER TABLE llm_requests ADD COLUMN regeneration_latency_ms INTEGER DEFAULT 0;
        EXCEPTION WHEN duplicate_column THEN END;
        BEGIN
            ALTER TABLE llm_requests ADD COLUMN candidate_context_tokens INTEGER;
        EXCEPTION WHEN duplicate_column THEN END;
        BEGIN
            ALTER TABLE llm_requests ADD COLUMN final_context_tokens INTEGER;
        EXCEPTION WHEN duplicate_column THEN END;
        BEGIN
            ALTER TABLE llm_requests ADD COLUMN tokens_removed INTEGER;
        EXCEPTION WHEN duplicate_column THEN END;
        BEGIN
            ALTER TABLE llm_requests ADD COLUMN cache_hit BOOLEAN DEFAULT FALSE;
        EXCEPTION WHEN duplicate_column THEN END;
        BEGIN
            ALTER TABLE llm_requests ADD COLUMN fallback_used BOOLEAN DEFAULT FALSE;
        EXCEPTION WHEN duplicate_column THEN END;
        BEGIN
            ALTER TABLE llm_requests ADD COLUMN retrieval_confidence FLOAT;
        EXCEPTION WHEN duplicate_column THEN END;
        BEGIN
            ALTER TABLE llm_requests ADD COLUMN retrieval_confidence_level VARCHAR(20);
        EXCEPTION WHEN duplicate_column THEN END;
        BEGIN
            ALTER TABLE llm_requests ADD COLUMN conflicting_evidence_detected BOOLEAN DEFAULT FALSE;
        EXCEPTION WHEN duplicate_column THEN END;
    END $$;
    """)

def downgrade():
    pass
