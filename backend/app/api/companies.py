from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.deps import get_current_membership
from app.db.session import get_db
from app.models.models import CompanyProfile, Membership, Certification, PastProject
from app.schemas.schemas import CompanyProfileIn, CompanyProfileOut

router = APIRouter()

class CertificationIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    certificate_number: str | None = None
    issuer: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None

class ProjectIn(BaseModel):
    title: str = Field(min_length=2, max_length=250)
    client_name: str | None = None
    sector: str | None = None
    contract_value_inr: float | None = Field(default=None, ge=0)
    completed_on: datetime | None = None
    description: str | None = None

@router.post("/profile", response_model=CompanyProfileOut, status_code=status.HTTP_201_CREATED)
def create_company_profile(payload: CompanyProfileIn, membership: Membership = Depends(get_current_membership), db: Session = Depends(get_db)):
    existing = db.query(CompanyProfile).filter(CompanyProfile.organization_id == membership.organization_id).first()
    if existing:
        raise HTTPException(409, "Company profile already exists; use PATCH to update it")
    profile = CompanyProfile(organization_id=membership.organization_id, **payload.model_dump())
    db.add(profile); db.commit(); db.refresh(profile)
    return profile

@router.get("/profile", response_model=CompanyProfileOut)
def get_company_profile(membership: Membership = Depends(get_current_membership), db: Session = Depends(get_db)):
    profile = db.query(CompanyProfile).filter(CompanyProfile.organization_id == membership.organization_id).first()
    if not profile:
        raise HTTPException(404, "Company profile not found")
    return profile

@router.patch("/profile", response_model=CompanyProfileOut)
def update_company_profile(payload: CompanyProfileIn, membership: Membership = Depends(get_current_membership), db: Session = Depends(get_db)):
    profile = db.query(CompanyProfile).filter(CompanyProfile.organization_id == membership.organization_id).first()
    if not profile:
        raise HTTPException(404, "Company profile not found")
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    db.commit(); db.refresh(profile)
    return profile

def _profile_or_404(db, org_id):
    profile = db.query(CompanyProfile).filter(CompanyProfile.organization_id == org_id).first()
    if not profile:
        raise HTTPException(400, "Create a company profile first")
    return profile

@router.get("/certifications")
def list_certifications(membership: Membership = Depends(get_current_membership), db: Session = Depends(get_db)):
    profile = _profile_or_404(db, membership.organization_id)
    rows = db.query(Certification).filter(Certification.company_profile_id == profile.id).all()
    return [{"id": str(x.id), "name": x.name, "certificate_number": x.certificate_number,
             "issuer": x.issuer, "valid_from": x.valid_from, "valid_until": x.valid_until} for x in rows]

@router.post("/certifications", status_code=201)
def add_certification(payload: CertificationIn, membership: Membership = Depends(get_current_membership), db: Session = Depends(get_db)):
    profile = _profile_or_404(db, membership.organization_id)
    row = Certification(company_profile_id=profile.id, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return {"id": str(row.id), **payload.model_dump()}

@router.get("/projects")
def list_projects(membership: Membership = Depends(get_current_membership), db: Session = Depends(get_db)):
    profile = _profile_or_404(db, membership.organization_id)
    rows = db.query(PastProject).filter(PastProject.company_profile_id == profile.id).all()
    return [{"id": str(x.id), "title": x.title, "client_name": x.client_name,
             "sector": x.sector, "contract_value_inr": x.contract_value_inr,
             "completed_on": x.completed_on, "description": x.description} for x in rows]

@router.post("/projects", status_code=201)
def add_project(payload: ProjectIn, membership: Membership = Depends(get_current_membership), db: Session = Depends(get_db)):
    profile = _profile_or_404(db, membership.organization_id)
    row = PastProject(company_profile_id=profile.id, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return {"id": str(row.id), **payload.model_dump()}
