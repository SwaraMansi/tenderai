# TenderAI entity relationships

```mermaid
erDiagram
  ORGANIZATIONS ||--o{ USERS : membership
  ORGANIZATIONS ||--|| COMPANY_PROFILES : owns
  COMPANY_PROFILES ||--o{ CERTIFICATIONS : records
  COMPANY_PROFILES ||--o{ PAST_PROJECTS : records
  TENDERS ||--o{ TENDER_DOCUMENTS : versions
  TENDER_DOCUMENTS ||--o{ TENDER_PAGES : extracts
  TENDER_DOCUMENTS ||--o{ TENDER_CHUNKS : indexes
  TENDERS ||--o{ TENDER_REQUIREMENTS : defines
  TENDERS ||--o{ TENDER_CHUNKS : retrieves
  TENDERS ||--o{ CORRIGENDUM_CHANGES : amends
  ORGANIZATIONS ||--o{ ELIGIBILITY_ASSESSMENTS : evaluates
  COMPANY_PROFILES ||--o{ ELIGIBILITY_ASSESSMENTS : assessed
  TENDERS ||--o{ ELIGIBILITY_ASSESSMENTS : assessed_against
  ELIGIBILITY_ASSESSMENTS ||--o{ COMPLIANCE_ITEMS : produces
```

## Core data rules
- Tender catalogue and tender source documents represent public procurement information.
- Company profile, certifications, past projects and assessments are scoped to the authenticated organization.
- `tender_documents.sha256` prevents identical document content from being uploaded repeatedly to the same tender.
- `tender_pages.page_number` and `tender_chunks.page_number` preserve page-level evidence provenance.
- `tender_chunks.embedding` stores 384-dimensional normalized BGE vectors; `search_vector` is a generated PostgreSQL `tsvector`.
- Corrigendum changes preserve both original and amendment document references.
- Eligibility assessments store the structured report snapshot; checklist completion is stored separately.

## Migrations
- `0001_initial_schema.py`: original TenderAI foundation.
- `0002_intelligence.py`: document pages, vector chunks, corrigendum diffs, checklist rows, GIN/HNSW indexes and DPIIT startup recognition field. The DPIIT column migration checks existing schema so it upgrades both a fresh install and a Phase 1 database.
