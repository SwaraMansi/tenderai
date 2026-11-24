import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def uuid_pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class UserRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"


class TenderStatus(str, enum.Enum):
    discovered = "discovered"
    open = "open"
    closed = "closed"
    cancelled = "cancelled"
    awarded = "awarded"
    unknown = "unknown"


class RequirementType(str, enum.Enum):
    turnover = "turnover"
    experience = "experience"
    certification = "certification"
    registration = "registration"
    technical = "technical"
    emd = "emd"
    document = "document"
    delivery = "delivery"
    other = "other"


class AssessmentStatus(str, enum.Enum):
    pass_ = "pass"
    fail = "fail"
    unknown = "unknown"
    needs_review = "needs_review"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"
    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    company_profile: Mapped["CompanyProfile | None"] = relationship(back_populates="organization", cascade="all, delete-orphan", uselist=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    memberships: Mapped[list["Membership"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Membership(Base):
    __tablename__ = "memberships"
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.owner, nullable=False)
    organization: Mapped[Organization] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class CompanyProfile(TimestampMixin, Base):
    __tablename__ = "company_profiles"
    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False)
    legal_name: Mapped[str] = mapped_column(String(250), nullable=False)
    business_type: Mapped[str | None] = mapped_column(String(100))
    sectors: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    udyam_number: Mapped[str | None] = mapped_column(String(50))
    dpiit_startup_number: Mapped[str | None] = mapped_column(String(100))
    gstin: Mapped[str | None] = mapped_column(String(20))
    pan_last_four: Mapped[str | None] = mapped_column(String(4))
    registered_state: Mapped[str | None] = mapped_column(String(100))
    annual_turnover_inr: Mapped[float | None] = mapped_column(Numeric(18, 2))
    years_in_business: Mapped[float | None] = mapped_column(Float)
    organization: Mapped[Organization] = relationship(back_populates="company_profile")
    certifications: Mapped[list["Certification"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    projects: Mapped[list["PastProject"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Certification(TimestampMixin, Base):
    __tablename__ = "certifications"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    certificate_number: Mapped[str | None] = mapped_column(String(100))
    issuer: Mapped[str | None] = mapped_column(String(200))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    company: Mapped[CompanyProfile] = relationship(back_populates="certifications")


class PastProject(TimestampMixin, Base):
    __tablename__ = "past_projects"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    client_name: Mapped[str | None] = mapped_column(String(200))
    sector: Mapped[str | None] = mapped_column(String(100))
    contract_value_inr: Mapped[float | None] = mapped_column(Numeric(18, 2))
    completed_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    description: Mapped[str | None] = mapped_column(Text)
    company: Mapped[CompanyProfile] = relationship(back_populates="projects")


class Tender(TimestampMixin, Base):
    __tablename__ = "tenders"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_tender_source_external_id"),
        Index("ix_tenders_deadline_status", "submission_deadline", "status"),
    )
    id: Mapped[uuid.UUID] = uuid_pk()
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # CPPP, GeM, state portal, manual
    external_id: Mapped[str] = mapped_column(String(150), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    procuring_entity: Mapped[str | None] = mapped_column(String(250))
    category: Mapped[str | None] = mapped_column(String(150))
    state: Mapped[str | None] = mapped_column(String(100))
    estimated_value_inr: Mapped[float | None] = mapped_column(Numeric(18, 2))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submission_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TenderStatus] = mapped_column(Enum(TenderStatus, name="tender_status"), default=TenderStatus.unknown, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    documents: Mapped[list["TenderDocument"]] = relationship(back_populates="tender", cascade="all, delete-orphan")
    requirements: Mapped[list["TenderRequirement"]] = relationship(back_populates="tender", cascade="all, delete-orphan")


class TenderDocument(TimestampMixin, Base):
    __tablename__ = "tender_documents"
    __table_args__ = (UniqueConstraint("tender_id", "sha256", name="uq_tender_document_hash"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    tender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), default="tender_document", nullable=False)
    storage_key: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_corrigendum: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extracted_text_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    tender: Mapped[Tender] = relationship(back_populates="documents")


class TenderRequirement(TimestampMixin, Base):
    __tablename__ = "tender_requirements"
    id: Mapped[uuid.UUID] = uuid_pk()
    tender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_type: Mapped[RequirementType] = mapped_column(Enum(RequirementType, name="requirement_type"), nullable=False)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    operator: Mapped[str | None] = mapped_column(String(30))
    numeric_value: Mapped[float | None] = mapped_column(Numeric(18, 2))
    unit: Mapped[str | None] = mapped_column(String(50))
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tender_documents.id", ondelete="SET NULL"))
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_quote: Mapped[str | None] = mapped_column(Text)
    extraction_confidence: Mapped[float | None] = mapped_column(Float)
    tender: Mapped[Tender] = relationship(back_populates="requirements")


class EligibilityAssessment(TimestampMixin, Base):
    __tablename__ = "eligibility_assessments"
    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    tender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    company_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_profiles.id", ondelete="RESTRICT"), nullable=False)
    result: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    result_details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
