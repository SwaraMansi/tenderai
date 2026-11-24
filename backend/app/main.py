from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.db.session import engine
from app.api import auth, companies, tenders, documents, eligibility

app = FastAPI(title=settings.app_name, version="1.0.0",
    description="India-first tender discovery, document intelligence and bid-readiness decision support.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
        "http://15.134.224.197", "http://ec2-15-134-224-197.ap-southeast-2.compute.amazonaws.com"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(companies.router, prefix="/api/v1/companies", tags=["Company"])
app.include_router(tenders.router, prefix="/api/v1/tenders", tags=["Tenders"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents and Discovery"])
app.include_router(eligibility.router, prefix="/api/v1/eligibility", tags=["Eligibility"])

@app.get("/", tags=["Health"])
def root():
    return {"service": "TenderAI", "version": "1.0.0", "country": "IN"}

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "TenderAI"}

@app.get("/health/database", tags=["Health"])
def database_health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
