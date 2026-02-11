from functools import lru_cache
from fastapi import FastAPI
from pydantic_settings import BaseSettings, SettingsConfigDict
import resend

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # zdefiniowane wszystkie zmienne srodowiskowe z pliku .env
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    SECRET_KEY: str
    ALGORITHM: str
    TOKEN_EXPIRE_MINUTES: int
    SESSION_EXPIRE_HOURS: int
    ALLOWED_DOMAINS: str
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM: str
    RESEND_API_KEY: str
    RESEND_EMAIL_FROM: str
    APP_NAME: str
    BACKEND_URL: str
    FRONTEND_URL: str
    DEBUG: bool = False
    DEFAULT_ADMIN_INVITE_TOKEN: str

# export settingsow bez tworzenia za kazdym razem obiektu Settings
@lru_cache
def get_settings():
    return Settings() # type: ignore

settings = get_settings()

resend.api_key = settings.RESEND_API_KEY