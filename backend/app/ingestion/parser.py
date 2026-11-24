import hashlib
import io
from pathlib import Path
import fitz
import pdfplumber
from docx import Document as DocxDocument

SUPPORTED = {".pdf", ".docx", ".txt", ".md"}

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def parse_document(filename: str, data: bytes) -> dict:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED:
        raise ValueError(f"Unsupported file type {suffix}; supported: {', '.join(sorted(SUPPORTED))}")
    pages, tables = [], []
    if suffix == ".pdf":
        pdf = fitz.open(stream=data, filetype="pdf")
        try:
            for number, page in enumerate(pdf, start=1):
                pages.append({"page_number": number, "text": page.get_text("text") or ""})
        finally:
            pdf.close()
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for number, page in enumerate(pdf.pages, start=1):
                for table_number, table in enumerate(page.extract_tables() or [], start=1):
                    rows = [[(cell or "").strip() for cell in row] for row in table if row]
                    if rows:
                        tables.append({"page_number": number, "table_number": table_number, "rows": rows})
        for page in pages:
            page_tables = [t for t in tables if t["page_number"] == page["page_number"]]
            for table in page_tables:
                page["text"] += "\n[TABLE]\n" + "\n".join(" | ".join(row) for row in table["rows"])
    elif suffix == ".docx":
        doc = DocxDocument(io.BytesIO(data))
        content = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for index, table in enumerate(doc.tables, start=1):
            rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
            if rows:
                tables.append({"page_number": 1, "table_number": index, "rows": rows})
                content.extend(" | ".join(row) for row in rows)
        pages = [{"page_number": 1, "text": "\n".join(content)}]
    else:
        pages = [{"page_number": 1, "text": data.decode("utf-8", errors="replace")}]
    return {"sha256": sha256_bytes(data), "pages": pages, "tables": tables,
            "full_text": "\n".join(p["text"] for p in pages), "page_count": len(pages)}
