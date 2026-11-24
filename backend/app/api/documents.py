import uuid, os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.api.deps import get_current_membership
from app.db.session import get_db
from app.models.models import Tender, TenderDocument
from app.models.advanced import TenderPage, CorrigendumChange
from app.ingestion.parser import parse_document
from app.core.config import settings
from app.ingestion.corrigendum import compare_documents
from app.ingestion.scraper import fetch_public_page
from app.retrieval.vector_store import index_document

router = APIRouter()
STORAGE = Path(settings.storage_dir)
MAX_FILE_BYTES = settings.max_upload_mb * 1024 * 1024

def _document_text(db, document_id):
    pages = db.query(TenderPage).filter(TenderPage.document_id == document_id).order_by(TenderPage.page_number).all()
    return "\n".join(p.text for p in pages)

@router.post("/tenders/{tender_id}/upload")
async def upload_tender_document(tender_id: uuid.UUID, file: UploadFile = File(...),
                                 document_type: str = Form("tender_document"),
                                 membership=Depends(get_current_membership), db: Session = Depends(get_db)):
    tender = db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(404, "Tender not found")
    data = await file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit")
    try:
        parsed = parse_document(file.filename or "upload.pdf", data)
    except Exception as exc:
        raise HTTPException(422, f"Document parsing failed: {str(exc)[:300]}")
    duplicate = db.query(TenderDocument).filter(TenderDocument.tender_id == tender_id,
                                                 TenderDocument.sha256 == parsed["sha256"]).first()
    if duplicate:
        return {"document_id": str(duplicate.id), "duplicate": True, "page_count": len(parsed["pages"])}
    version = (db.query(TenderDocument).filter(TenderDocument.tender_id == tender_id,
                TenderDocument.document_type == document_type).count() or 0) + 1
    safe_name = Path((file.filename or "document").replace("\\", "/")).name
    folder = STORAGE / str(tender_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex}_{safe_name}"
    path.write_bytes(data)
    doc = TenderDocument(tender_id=tender_id, filename=safe_name, document_type=document_type,
                         storage_key=str(path), sha256=parsed["sha256"], version_number=version,
                         is_corrigendum=document_type == "corrigendum", extracted_text_status="completed")
    db.add(doc)
    db.flush()
    tables_by_page = {}
    for table in parsed["tables"]:
        tables_by_page.setdefault(table["page_number"], []).append(table["rows"])
    for page in parsed["pages"]:
        db.add(TenderPage(document_id=doc.id, page_number=page["page_number"],
                          text=page["text"], tables_json=tables_by_page.get(page["page_number"], [])))
    db.commit()
    try:
        index_result = index_document(db, tender_id, doc.id, parsed["pages"])
        indexing = {"indexed": index_result["chunk_count"] > 0,
                    "chunk_count": index_result["chunk_count"],
                    "embedded": index_result["embedded"], "reason": index_result["reason"]}
    except Exception as exc:
        db.rollback()
        indexing = {"indexed": False, "chunk_count": 0, "embedded": False,
                    "reason": f"Indexing failed: {str(exc)[:250]}"}
    return {"document_id": str(doc.id), "duplicate": False, "filename": safe_name,
            "version_number": version, "page_count": parsed["page_count"],
            "table_count": len(parsed["tables"]), "sha256": parsed["sha256"], "indexing": indexing}

@router.post("/tenders/{tender_id}/corrigenda")
async def upload_corrigendum(tender_id: uuid.UUID, file: UploadFile = File(...),
                             membership=Depends(get_current_membership), db: Session = Depends(get_db)):
    if not db.get(Tender, tender_id):
        raise HTTPException(404, "Tender not found")
    originals = db.query(TenderDocument).filter(TenderDocument.tender_id == tender_id,
        TenderDocument.is_corrigendum.is_(False)).order_by(TenderDocument.version_number.desc()).all()
    if not originals:
        raise HTTPException(400, "Upload the original tender document before its corrigendum")
    result = await upload_tender_document(tender_id, file, "corrigendum", membership, db)
    if result.get("duplicate"):
        return result
    docs = db.query(TenderDocument).filter(TenderDocument.tender_id == tender_id).order_by(TenderDocument.version_number).all()
    revised = db.get(TenderDocument, uuid.UUID(result["document_id"]))
    original = originals[0]
    changes = compare_documents(_document_text(db, original.id), _document_text(db, revised.id))
    for change in changes:
        db.add(CorrigendumChange(tender_id=tender_id, original_document_id=original.id,
            corrigendum_document_id=revised.id, **change))
    db.commit()
    return {**result, "changes": changes}

@router.get("/tenders/{tender_id}/versions")
def list_document_versions(tender_id: uuid.UUID, membership=Depends(get_current_membership), db: Session = Depends(get_db)):
    if not db.get(Tender, tender_id):
        raise HTTPException(404, "Tender not found")
    docs = db.query(TenderDocument).filter(TenderDocument.tender_id == tender_id).order_by(TenderDocument.created_at.desc()).all()
    return [{"id": str(d.id), "filename": d.filename, "document_type": d.document_type,
             "version_number": d.version_number, "is_corrigendum": d.is_corrigendum,
             "sha256": d.sha256, "created_at": d.created_at.isoformat()} for d in docs]

@router.get("/tenders/{tender_id}/corrigenda")
def list_corrigendum_diffs(tender_id: uuid.UUID, membership=Depends(get_current_membership), db: Session = Depends(get_db)):
    if not db.get(Tender, tender_id):
        raise HTTPException(404, "Tender not found")
    rows = db.query(CorrigendumChange).filter(CorrigendumChange.tender_id == tender_id).order_by(CorrigendumChange.created_at.desc()).all()
    return [{"id": str(x.id), "change_type": x.change_type, "old_value": x.old_value,
             "new_value": x.new_value, "explanation": x.explanation} for x in rows]

@router.post("/discover")
def discover_public_tender(url: str, membership=Depends(get_current_membership)):
    try:
        return fetch_public_page(url)
    except Exception as exc:
        raise HTTPException(422, f"Public metadata discovery failed: {str(exc)[:300]}")
