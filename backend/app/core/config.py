from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "TenderAI"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://tenderai:change-me@localhost:5432/tenderai"
    jwt_secret: str = "development-only-change-this-secret-1234567890"
    access_token_minutes: int = 30
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:3b"
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-20b"
    storage_dir: str = "/app/storage"
    max_upload_mb: int = 20
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
