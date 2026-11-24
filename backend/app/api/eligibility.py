import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.deps import get_current_membership
from app.db.session import get_db
from app.models.models import (
    Tender, TenderDocument, CompanyProfile, Certification, PastProject,
    EligibilityAssessment, TenderRequirement, RequirementType
)
from app.models.advanced import TenderPage, ComplianceItem
from app.eligibility.extractor import extract_requirements
from app.core.config import settings
from app.eligibility.rule_engine import evaluate_company

router = APIRouter()

class ChecklistUpdate(BaseModel):
    is_completed: bool

def _evidence_document(evidence_item, documents, fallback):
    if not isinstance(evidence_item, dict):
        return fallback
    name = evidence_item.get("document")
    if name:
        matched = next((doc for doc in documents if doc.filename == name), None)
        if matched:
            return matched
    return fallback

def _parse_iso_deadline(value):
    if not value or "T" not in value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
        return parsed
    except ValueError:
        return None

@router.post("/tenders/{tender_id}/evaluate/{company_id}")
def evaluate_tender(tender_id: uuid.UUID, company_id: uuid.UUID,
                    membership=Depends(get_current_membership), db: Session = Depends(get_db)):
    tender = db.get(Tender, tender_id)
    profile = db.query(CompanyProfile).filter(
        CompanyProfile.id == company_id,
        CompanyProfile.organization_id == membership.organization_id
    ).first()
    if not tender or not profile:
        raise HTTPException(404, "Tender or company profile not found")

    all_documents = db.query(TenderDocument).filter(
        TenderDocument.tender_id == tender_id
    ).order_by(TenderDocument.created_at.asc()).all()
    original_documents = [doc for doc in all_documents if not doc.is_corrigendum]
    if not original_documents:
        raise HTTPException(400, "Upload an original tender document before evaluation")
    latest_original = original_documents[-1]
    evaluation_documents = [latest_original] + [
        doc for doc in all_documents
        if doc.is_corrigendum and doc.created_at >= latest_original.created_at
    ]

    original_parts, amendment_parts = [], []
    for doc in evaluation_documents:
        pages = db.query(TenderPage).filter(
            TenderPage.document_id == doc.id
        ).order_by(TenderPage.page_number).all()
        selected_pages = _select_relevant_pages(pages, max_pages=8 if doc.is_corrigendum else 12)
        document_text = "\n".join(
            f"[PAGE {page.page_number}]\n{page.text[:1400]}" for page in selected_pages
        )
        if document_text.strip():
            label = "CORRIGENDUM / AMENDMENT" if doc.is_corrigendum else "ORIGINAL TENDER"
            block = f"\n[DOCUMENT: {doc.filename}; TYPE: {label}]\n{document_text}"
            (amendment_parts if doc.is_corrigendum else original_parts).append(block)

    # Reserve context for amendments so the latest corrigendum is not truncated behind a long base tender.
    original_context = "\n".join(original_parts)[:7600]
    amendment_context = "\n".join(amendment_parts)[-4300:]
    combined_text = original_context + "\n" + amendment_context
    if not combined_text.strip():
        raise HTTPException(422, "Tender documents contain no extractable text; scanned-PDF OCR is not included")

    try:
        requirements = extract_requirements(
            combined_text, api_key=settings.groq_api_key,
            base_url=settings.groq_base_url, model=settings.groq_model
        )
    except Exception as exc:
        raise HTTPException(503, f"Local Ollama requirement extraction failed: {str(exc)[:300]}")

    certifications = db.query(Certification).filter(
        Certification.company_profile_id == profile.id
    ).all()
    projects = db.query(PastProject).filter(
        PastProject.company_profile_id == profile.id
    ).all()
    report = evaluate_company(profile, certifications, projects, requirements)
    evidence = requirements.evidence if isinstance(requirements.evidence, dict) else {}

    # Keep extracted metadata without overwriting manually entered values.
    tender_metadata = dict(tender.metadata_json or {})
    if requirements.estimated_value_inr is not None:
        tender_metadata["extracted_estimated_value_inr"] = requirements.estimated_value_inr
        if tender.estimated_value_inr is None:
            tender.estimated_value_inr = requirements.estimated_value_inr
    if requirements.submission_deadline:
        tender_metadata["extracted_submission_deadline"] = requirements.submission_deadline
        parsed_deadline = _parse_iso_deadline(requirements.submission_deadline)
        if parsed_deadline:
            tender.submission_deadline = parsed_deadline
    tender_metadata["extraction_documents"] = [doc.filename for doc in evaluation_documents]
    tender.metadata_json = tender_metadata

    extracted_fields = [
        ("turnover", "Minimum annual turnover", requirements.minimum_annual_turnover_inr, "INR", "minimum_annual_turnover_inr"),
        ("experience", "Minimum years of experience", requirements.minimum_years_experience, "years", "minimum_years_experience"),
        ("experience", "Minimum similar work value", requirements.minimum_similar_work_value_inr, "INR", "minimum_similar_work_value_inr"),
        ("emd", "Earnest Money Deposit", requirements.emd_amount_inr, "INR", "emd_amount_inr"),
    ]
    for kind, title, value, unit, evidence_key in extracted_fields:
        if value is not None:
            evidence_item = evidence.get(evidence_key) or evidence.get(kind) or {}
            source_doc = _evidence_document(evidence_item, evaluation_documents, latest_original)
            db.add(TenderRequirement(
                tender_id=tender_id, requirement_type=RequirementType(kind),
                title=title, description=title, operator=">=", numeric_value=value,
                unit=unit, is_mandatory=True, source_document_id=source_doc.id,
                source_page=evidence_item.get("page") if isinstance(evidence_item, dict) else None,
                source_quote=evidence_item.get("quote") if isinstance(evidence_item, dict) else None,
                extraction_confidence=None
            ))

    for cert in requirements.required_certifications:
        cert_key = cert.lower().replace(" ", "_")
        evidence_item = evidence.get(cert_key) or evidence.get("required_certifications") or {}
        if isinstance(evidence_item, list):
            evidence_item = next((item for item in evidence_item if isinstance(item, dict)), {})
        source_doc = _evidence_document(evidence_item, evaluation_documents, latest_original)
        db.add(TenderRequirement(
            tender_id=tender_id, requirement_type=RequirementType.certification,
            title=f"Required certification: {cert}", description=cert, is_mandatory=True,
            source_document_id=source_doc.id,
            source_page=evidence_item.get("page") if isinstance(evidence_item, dict) else None,
            source_quote=evidence_item.get("quote") if isinstance(evidence_item, dict) else None
        ))

    aliases = {
        "annual_turnover": "minimum_annual_turnover_inr",
        "business_experience": "minimum_years_experience",
        "similar_work_value": "minimum_similar_work_value_inr",
        "emd_/_bid_security": "emd_amount_inr",
    }
    for check in report["checks"]:
        field = check["requirement"].lower().split(":")[-1].strip().replace(" ", "_")
        item = evidence.get(field) or evidence.get(aliases.get(field, "")) or evidence.get(check["requirement"])
        if item is None and check["requirement"].startswith("Certification: "):
            cert_key = check["requirement"].split(":", 1)[1].strip().lower().replace(" ", "_")
            item = evidence.get(cert_key) or evidence.get("required_certifications")
        if isinstance(item, list):
            item = next((entry for entry in item if isinstance(entry, dict)), None)
        if isinstance(item, dict):
            source_doc = _evidence_document(item, evaluation_documents, latest_original)
            check["source_page"] = item.get("page")
            check["source_quote"] = item.get("quote")
            check["source_document"] = source_doc.filename

    report["estimated_value_inr"] = requirements.estimated_value_inr
    report["submission_deadline"] = requirements.submission_deadline
    assessment = EligibilityAssessment(
        organization_id=membership.organization_id, tender_id=tender_id,
        company_profile_id=profile.id, result=report["recommendation"].lower(),
        score=report["score"], result_details=report
    )
    db.add(assessment)
    db.flush()
    checklist_rows = []
    for item in report["checklist"]:
        row = ComplianceItem(
            assessment_id=assessment.id, title=item["title"], status=item["status"],
            required_action=item["required_action"], source_page=item["source_page"]
        )
        db.add(row)
        checklist_rows.append(row)
    db.commit()
    for item, row in zip(report["checklist"], checklist_rows):
        item["id"] = str(row.id)
    return {"assessment_id": str(assessment.id), "tender_id": str(tender_id), **report}

@router.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: uuid.UUID, membership=Depends(get_current_membership), db: Session = Depends(get_db)):
    assessment = db.query(EligibilityAssessment).filter(
        EligibilityAssessment.id == assessment_id,
        EligibilityAssessment.organization_id == membership.organization_id
    ).first()
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    items = db.query(ComplianceItem).filter(
        ComplianceItem.assessment_id == assessment.id
    ).all()
    return {
        "id": str(assessment.id), "tender_id": str(assessment.tender_id),
        "result": assessment.result, "score": assessment.score,
        "report": assessment.result_details,
        "checklist": [{
            "id": str(item.id), "title": item.title, "status": item.status,
            "required_action": item.required_action, "is_completed": item.is_completed,
            "source_page": item.source_page
        } for item in items]
    }

@router.patch("/assessments/{assessment_id}/checklist/{item_id}")
def update_checklist(assessment_id: uuid.UUID, item_id: uuid.UUID, payload: ChecklistUpdate,
                     membership=Depends(get_current_membership), db: Session = Depends(get_db)):
    assessment = db.query(EligibilityAssessment).filter(
        EligibilityAssessment.id == assessment_id,
        EligibilityAssessment.organization_id == membership.organization_id
    ).first()
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    item = db.query(ComplianceItem).filter(
        ComplianceItem.id == item_id, ComplianceItem.assessment_id == assessment.id
    ).first()
    if not item:
        raise HTTPException(404, "Checklist item not found")
    item.is_completed = payload.is_completed
    db.commit()
    return {"id": str(item.id), "is_completed": item.is_completed}
