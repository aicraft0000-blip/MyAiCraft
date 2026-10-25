from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    frontend_url: str = "http://localhost:5173"

    # Stripe (payments) — empty locally; set on Railway
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_radar_price_id: str = ""
    stripe_radar_pro_price_id: str = ""

    # MailerSend (welcome email) — same account as the pipeline notifications
    mailersend_api_key: str = ""
    mailersend_from_email: str = "hello@example.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
