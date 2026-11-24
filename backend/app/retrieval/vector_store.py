from sqlalchemy import text
from sqlalchemy.orm import Session

def index_document(db: Session, tender_id, document_id, pages):
    from app.retrieval.embeddings import chunk_pages, embed_texts
    from app.models.advanced import TenderChunk
    chunks = chunk_pages(pages)
    rows = []
    for item in chunks:
        row = TenderChunk(tender_id=tender_id, document_id=document_id,
                          page_number=item["page_number"], section_number=item["section_number"],
                          content=item["content"], search_text=item["content"], embedding=None)
        db.add(row)
        rows.append(row)
    db.commit()
    if not rows:
        return {"chunk_count": 0, "embedded": False, "reason": "No extractable text chunks were found."}
    try:
        vectors = embed_texts([item["content"] for item in chunks], batch_size=8)
        for row, vector in zip(rows, vectors):
            row.embedding = vector
        db.commit()
        return {"chunk_count": len(rows), "embedded": True, "reason": None}
    except Exception as exc:
        db.rollback()
        return {"chunk_count": len(rows), "embedded": False,
                "reason": f"Keyword index is available; vector embedding failed: {str(exc)[:200]}"}

def hybrid_search(db: Session, tender_id, query, limit=8):
    from app.retrieval.embeddings import embed_texts
    vector_rows = []
    try:
        vector = embed_texts([query], batch_size=1)[0]
        vector_rows = db.execute(text("""
            SELECT c.id, c.document_id, c.page_number, c.section_number, c.content,
                   d.filename, d.source_url,
                   1 - (c.embedding <=> CAST(:embedding AS vector)) AS score
            FROM tender_chunks c JOIN tender_documents d ON d.id=c.document_id
            WHERE c.tender_id=:tender_id AND c.embedding IS NOT NULL
            ORDER BY c.embedding <=> CAST(:embedding AS vector) LIMIT :limit
        """), {"embedding": str(vector), "tender_id": str(tender_id), "limit": limit * 3}).mappings().all()
    except Exception:
        vector_rows = []
    keyword_rows = db.execute(text("""
        SELECT c.id, c.document_id, c.page_number, c.section_number, c.content,
               d.filename, d.source_url,
               ts_rank_cd(c.search_vector, plainto_tsquery('english', :query)) AS score
        FROM tender_chunks c JOIN tender_documents d ON d.id=c.document_id
        WHERE c.tender_id=:tender_id
          AND c.search_vector @@ plainto_tsquery('english', :query)
        ORDER BY score DESC LIMIT :limit
    """), {"query": query, "tender_id": str(tender_id), "limit": limit * 3}).mappings().all()
    ranks, records = {}, {}
    for result_set in (vector_rows, keyword_rows):
        for rank, row in enumerate(result_set, 1):
            key = str(row["id"])
            ranks[key] = ranks.get(key, 0.0) + 1.0 / (60 + rank)
            records[key] = dict(row)
    return [{**records[key], "rrf_score": ranks[key]}
            for key in sorted(records, key=lambda k: ranks[k], reverse=True)[:limit]]
