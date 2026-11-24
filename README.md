# TenderAI

TenderAI is an India-focused procurement intelligence application for discovering tenders, organizing tender documents, comparing amendments, and preparing evidence-backed bid-readiness assessments.

The platform is designed for MSMEs, contractors, suppliers, consultants, and bid teams. It helps users turn complex tender documents into structured, searchable information while keeping the final eligibility decision under human review.

> TenderAI is a decision-support MVP, not a government-affiliated service. It does not submit bids and does not replace legal, financial, or procurement advice.

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React-61DAFB?logo=react&logoColor=61DAFB)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![pgvector](https://img.shields.io/badge/Search-pgvector-4B5563)](https://github.com/pgvector/pgvector)

## Live deployment

TenderAI is currently deployed on an Amazon EC2 instance:

| Resource | Link |
| --- | --- |
| Web application | [http://15.134.224.197](http://15.134.224.197) |
| API documentation | [http://15.134.224.197/docs](http://15.134.224.197/docs) |
| API health | [http://15.134.224.197/health](http://15.134.224.197/health) |
| Database health | [http://15.134.224.197/health/database](http://15.134.224.197/health/database) |

The EC2 deployment currently uses:

- Amazon Linux 2023
- FastAPI and Uvicorn
- PostgreSQL 16 with pgvector
- Nginx for static frontend delivery and API reverse proxy
- Groq-compatible AI integration with the key left for deployment configuration
- Systemd services for persistent backend operation

The live server is a low-resource demo instance and is accessible over HTTP. HTTPS and a custom domain should be added before production use.

## What TenderAI can do

### Workspace and authentication

- Register an organization
- Sign in with JWT-based authentication
- Maintain organization membership
- Create and update a company profile
- Add certifications and GST/PAN details
- Record past projects and contract values

### Tender discovery

- Search tender records by title, tender ID, category, or state
- Create tender records manually
- Record estimated value, deadline, sector, state, and procuring entity
- Import metadata from approved public CPPP or GeM URLs
- Import tender-like links from public listing pages
- Open the official source page for verification

Public discovery is permission-aware: it does not bypass login, CAPTCHA, or access controls.

### Document intelligence

- Upload PDF, DOCX, TXT, and Markdown tender documents
- Extract PDF text with page numbers
- Extract PDF tables and combine table rows with page text
- Parse DOCX, TXT, and Markdown files
- Store document versions
- Detect duplicate documents using SHA-256 hashes
- Upload and compare corrigenda or amendments
- Detect likely deadline, EMD, turnover, experience, and eligibility-text changes

Scanned PDFs without embedded text are reported as unsupported rather than filled with invented text. OCR is not included in the current MVP.

### Eligibility and bid readiness

- Extract candidate tender requirements
- Compare turnover, experience, similar work, certifications, and EMD against company evidence
- Produce `PASS`, `FAIL`, `MISSING_EVIDENCE`, and `NEEDS_VERIFICATION` signals
- Calculate a preliminary fit score
- Generate a bid/no-bid/review recommendation
- Create a downloadable-style checklist workflow
- Preserve tender source metadata and extraction context
- Display explicit limitations for financial and legal interpretation

MSME and DPIIT Startup relaxations are considered only when the tender text explicitly permits them. A human must verify tender clauses, registration validity, and supporting documents.

### Retrieval and Q&A

The repository includes a clause-aware retrieval pipeline with:

- Page and section-aware text chunking
- PostgreSQL full-text search
- pgvector cosine retrieval
- Reciprocal Rank Fusion
- Page, filename, source URL, section, and chunk citations
- Evidence-grounded tender questions
- Source-marker validation to detect unverified answer references

Local CPU embeddings using `BAAI/bge-small-en-v1.5` are available in the Docker/local architecture. They are not enabled on the current 1 GB EC2 deployment.

### Groq AI option

Tender requirement extraction and tender Q&A can use an OpenAI-compatible Groq endpoint.

The backend supports:

- `GROQ_API_KEY`
- `GROQ_BASE_URL`
- `GROQ_MODEL`

The configured default model is `openai/gpt-oss-20b`. Access depends on the user's Groq account and current model availability.

## API overview

| Area | Example routes |
| --- | --- |
| Authentication | `POST /api/v1/auth/register`, `POST /api/v1/auth/login` |
| Company | `GET/POST/PATCH /api/v1/companies/profile` |
| Certifications | `GET/POST /api/v1/companies/certifications` |
| Past projects | `GET/POST /api/v1/companies/projects` |
| Tenders | `GET/POST /api/v1/tenders` |
| Discovery | `POST /api/v1/tenders/discover/public-page`, `POST /api/v1/tenders/discover/sync` |
| Documents | `POST /api/v1/documents/tenders/{tender_id}/upload` |
| Corrigenda | `POST /api/v1/documents/tenders/{tender_id}/corrigenda` |
| Retrieval | `POST /api/v1/tenders/{tender_id}/search` |
| Tender Q&A | `POST /api/v1/tenders/{tender_id}/ask` |
| Eligibility | `POST /api/v1/eligibility/tenders/{tender_id}/evaluate/{company_id}` |
| Assessment | `GET/PATCH /api/v1/eligibility/assessments/{assessment_id}` |

The complete interactive list is available through [Swagger UI](http://15.134.224.197/docs).

## Architecture

```text
React SPA
    |
    | HTTPS or HTTP
    v
Nginx
    |
    +--> Static React build
    |
    +--> /api/* reverse proxy
            |
            v
        FastAPI
            |
            +--> PostgreSQL + pgvector
            +--> Local file storage
            +--> Groq-compatible AI API
            +--> Public tender metadata adapters
```

The ingestion pipeline is:

```text
Public page or uploaded file
    -> type and size validation
    -> SHA-256 duplicate check
    -> PDF/DOCX/text extraction
    -> page and table storage
    -> clause-aware chunking
    -> keyword and optional vector indexing
    -> tender retrieval and eligibility analysis
```

## Local development

### Requirements

- Docker Desktop or Docker Engine
- Docker Compose
- Python 3.11 or newer
- Node.js 20 or newer

### Start with Docker

```bash
cd tenderai
cp .env.example .env
```

Set a secure database password and JWT secret in `.env`, then run:

```bash
docker compose up --build -d
```

Open:

- Frontend: `http://localhost:5173`
- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- API health: `http://localhost:8000/health`
- Database health: `http://localhost:8000/health/database`
- Ollama health: `http://localhost:11434/api/tags`

Stop the stack with:

```bash
docker compose down
```

To remove containers and persistent volumes, use this only when local data can be deleted:

```bash
docker compose down -v
```

### Run backend locally without Docker

```bash
cd tenderai/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Start PostgreSQL/pgvector first and set `DATABASE_URL`, `JWT_SECRET`, and optional Groq variables.

### Run frontend locally

```bash
cd tenderai/frontend
npm install
npm run dev
```

Create `VITE_API_URL` in the frontend environment if the API is not running at `http://localhost:8000`.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `POSTGRES_PASSWORD` | PostgreSQL password for Docker Compose |
| `DATABASE_URL` | SQLAlchemy PostgreSQL connection URL |
| `JWT_SECRET` | JWT signing secret |
| `ACCESS_TOKEN_MINUTES` | Access-token lifetime |
| `STORAGE_DIR` | Uploaded document storage directory |
| `GROQ_API_KEY` | Groq API key for AI extraction and Q&A |
| `GROQ_BASE_URL` | OpenAI-compatible Groq API base URL |
| `GROQ_MODEL` | Groq chat model |

Do not commit real API keys or database credentials. Revoke any credential that has been shared outside a secure environment.

## Deployment on EC2

The current deployment can be reproduced on an EC2 Ubuntu or Amazon Linux instance with:

1. PostgreSQL/pgvector running on the instance or via a managed PostgreSQL service
2. Python 3.11+ and a virtual environment for FastAPI
3. Node.js for building the React frontend
4. Nginx serving the frontend and proxying API traffic
5. Systemd for API and database process management
6. An AWS Security Group allowing SSH and HTTP
7. HTTPS, a domain, backups, and monitoring before public production use

The demo instance is intentionally lightweight. A server with at least 2 GB of RAM is recommended for the complete backend, database, and local embedding workflow.

## Testing

Backend tests are in `backend/tests/` and can be run with:

```bash
cd tenderai/backend
pytest -q
```

Frontend verification:

```bash
cd tenderai/frontend
npm run build
```

## Repository status

Verified capabilities include:

- Registration and authentication
- Public API and database health
- PostgreSQL migrations
- Manual tender creation and catalogue management
- Document parsing and version endpoints
- Corrigendum comparison
- Deterministic eligibility rules
- Groq-compatible structured extraction integration
- React frontend build
- EC2 deployment through Nginx
