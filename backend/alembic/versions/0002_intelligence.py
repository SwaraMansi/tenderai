from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import TSVECTOR

revision = "0002_intelligence"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade():
    existing_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("company_profiles")}
    if "dpiit_startup_number" not in existing_columns:
        op.add_column("company_profiles", sa.Column("dpiit_startup_number", sa.String(100), nullable=True))
    op.create_table("tender_pages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("tender_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("tables_json", sa.JSON(), nullable=False, server_default="[]"))
    op.create_index("ix_tender_pages_document_id", "tender_pages", ["document_id"])
    op.create_table("tender_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tender_id", sa.Uuid(), sa.ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("tender_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer()),
        sa.Column("section_number", sa.String(100)),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384)),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("search_vector", TSVECTOR, sa.Computed("to_tsvector('english', search_text)", persisted=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_tender_chunks_document", "tender_chunks", ["document_id"])
    op.create_index("ix_tender_chunks_tender_id", "tender_chunks", ["tender_id"])
    op.create_index("ix_tender_chunks_search_vector", "tender_chunks", ["search_vector"], postgresql_using="gin")
    op.create_index("ix_tender_chunks_embedding_hnsw", "tender_chunks", ["embedding"],
                    postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"})
    op.create_table("corrigendum_changes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tender_id", sa.Uuid(), sa.ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_document_id", sa.Uuid(), sa.ForeignKey("tender_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("corrigendum_document_id", sa.Uuid(), sa.ForeignKey("tender_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("change_type", sa.String(50), nullable=False),
        sa.Column("old_value", sa.Text()),
        sa.Column("new_value", sa.Text()),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_corrigendum_changes_tender_id", "corrigendum_changes", ["tender_id"])
    op.create_table("compliance_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("assessment_id", sa.Uuid(), sa.ForeignKey("eligibility_assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("required_action", sa.Text(), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_page", sa.Integer()))
    op.create_index("ix_compliance_items_assessment_id", "compliance_items", ["assessment_id"])

def downgrade():
    op.drop_table("compliance_items")
    op.drop_table("corrigendum_changes")
    op.drop_table("tender_chunks")
    op.drop_table("tender_pages")
    op.drop_column("company_profiles", "dpiit_startup_number")
