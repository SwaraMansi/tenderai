from app.ingestion.parser import parse_document, sha256_bytes
from app.ingestion.corrigendum import compare_documents

def test_sha256_is_deterministic():
    assert sha256_bytes(b"tender") == sha256_bytes(b"tender")
    assert sha256_bytes(b"tender") != sha256_bytes(b"amended")

def test_text_parser_preserves_page_number():
    parsed = parse_document("notice.txt", b"Bid submission deadline: 30 June 2027")
    assert parsed["pages"][0]["page_number"] == 1
    assert "deadline" in parsed["full_text"].lower()

def test_corrigendum_detects_deadline_and_emd():
    old = "Bid submission date: 10 June 2027\nEMD amount: INR 50,000"
    new = "Bid submission date: 20 June 2027\nEMD amount: INR 25,000"
    changes = compare_documents(old, new)
    kinds = {x["change_type"] for x in changes}
    assert "deadline" in kinds
    assert "emd" in kinds


def test_pdf_parser_keeps_exact_page_numbers():
    import fitz
    pdf = fitz.open()
    first = pdf.new_page()
    first.insert_text((72, 72), "Eligibility criteria page one")
    second = pdf.new_page()
    second.insert_text((72, 72), "EMD requirement page two")
    raw = pdf.tobytes()
    pdf.close()
    parsed = parse_document("notice.pdf", raw)
    assert [page["page_number"] for page in parsed["pages"]] == [1, 2]
    assert "page one" in parsed["pages"][0]["text"]
    assert "page two" in parsed["pages"][1]["text"]


def test_chunker_bounds_long_paragraphs_and_keeps_page():
    from app.retrieval.embeddings import chunk_pages
    chunks = chunk_pages([{"page_number": 7, "text": "A" * 2500}], max_chars=1000, overlap=100)
    assert len(chunks) >= 3
    assert all(len(chunk["content"]) <= 1000 for chunk in chunks)
    assert all(chunk["page_number"] == 7 for chunk in chunks)


def test_public_scraper_rejects_non_procurement_hosts():
    from app.ingestion.scraper import validate_public_tender_url
    assert validate_public_tender_url("https://eprocure.gov.in/tender/123")
    try:
        validate_public_tender_url("https://example.com/tender/123")
    except ValueError:
        assert True
    else:
        raise AssertionError("Unapproved public host was accepted")
