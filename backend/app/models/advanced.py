import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Index, func, JSON, Computed
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import TSVECTOR
from pgvector.sqlalchemy import Vector
from app.db.base import Base

class TenderPage(Base):
    __tablename__ = "tender_pages"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tender_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    tables_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

class TenderChunk(Base):
    __tablename__ = "tender_chunks"
    __table_args__ = (
        Index("ix_tender_chunks_document", "document_id"),
        Index("ix_tender_chunks_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_tender_chunks_embedding_hnsw", "embedding", postgresql_using="hnsw",
              postgresql_ops={"embedding": "vector_cosine_ops"}),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tender_documents.id", ondelete="CASCADE"), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    section_number: Mapped[str | None] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list | None] = mapped_column(Vector(384))
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    search_vector = mapped_column(TSVECTOR, Computed("to_tsvector('english', search_text)", persisted=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class CorrigendumChange(Base):
    __tablename__ = "corrigendum_changes"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    original_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tender_documents.id", ondelete="CASCADE"), nullable=False)
    corrigendum_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tender_documents.id", ondelete="CASCADE"), nullable=False)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ComplianceItem(Base):
    __tablename__ = "compliance_items"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("eligibility_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    required_action: Mapped[str] = mapped_column(Text, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_page: Mapped[int | None] = mapped_column(Integer)
