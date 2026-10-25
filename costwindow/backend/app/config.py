from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    backend_url: str = "http://localhost:8000"
    # Public-facing API base shown to customers (proxy snippets, emails).
    # The pretty custom domain — set once DNS + Railway domain are wired.
    public_api_url: str = "https://api.costwindow.com"
    frontend_url: str = "http://localhost:5173"
    # Interactive API docs (/docs, /openapi.json) — off in prod by default.
    enable_docs: bool = False
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_monthly_price_id: str = "price_YOUR_PRICE_ID"
    stripe_yearly_price_id: str = "price_YOUR_PRICE_ID"
    mailersend_api_key: str = ""
    mailersend_from_email: str = "noreply@costwindow.com"
    mailersend_from_name: str = "CostWindow"


@lru_cache
def get_settings() -> Settings:
    return Settings()
