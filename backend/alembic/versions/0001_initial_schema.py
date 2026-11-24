"""Initial TenderAI core schema. Revision: 0001_initial."""
from alembic import op
from app.db.base import Base
from app.models import models

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

CORE_TABLES = [
    "organizations", "users", "memberships", "company_profiles",
    "certifications", "past_projects", "tenders", "tender_documents",
    "tender_requirements", "eligibility_assessments",
]

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    tables = [Base.metadata.tables[name] for name in CORE_TABLES]
    Base.metadata.create_all(bind=op.get_bind(), tables=tables)

def downgrade():
    tables = [Base.metadata.tables[name] for name in reversed(CORE_TABLES)]
    Base.metadata.drop_all(bind=op.get_bind(), tables=tables)
