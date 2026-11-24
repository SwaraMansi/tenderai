# TenderAI architecture

## Request path
React SPA -> FastAPI -> authenticated organization context -> PostgreSQL.

## Ingestion path
Official CPPP/GeM public page URL or user file -> allowlist/size/type validation -> SHA-256 -> PyMuPDF/pdfplumber/python-docx extraction -> page and table persistence -> clause-aware chunking -> BGE-small CPU embeddings -> pgvector plus generated tsvector.

If embedding model download or inference fails, extracted chunks remain stored and full-text keyword retrieval remains available.

## Retrieval path
User query -> BGE embedding -> pgvector cosine ranking + PostgreSQL full-text ranking -> Reciprocal Rank Fusion -> result chunks with document filename, source URL, page and section provenance.

## Eligibility path
Tender text -> Ollama qwen2.5:3b structured JSON output -> Pydantic validation -> persisted normalized requirements -> deterministic Python rules -> assessment score, statuses, checklist and limitations.

The LLM extracts candidate facts; it does not calculate financial pass/fail outcomes. MSME and DPIIT Startup relaxations are considered only if the tender text explicitly names the applicable beneficiary and condition. The result remains subject to human verification.

## Local deployment
Docker Compose runs PostgreSQL/pgvector, Ollama, a one-shot model pull service, FastAPI and an Nginx-served React build. Container memory limits are set for an 8 GB development laptop.
