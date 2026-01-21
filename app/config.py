from sqlalchemy import URL
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    database_url: str = URL.create(
        "postgresql",
        username="postgres",
        password="",
        host="localhost",
        database="zapisy_backend",
    ).__to_string__()
    secret_key: str = "random"
    algorithm: str = "HS256"
    token_expire_minutes: int = 30
    password_expire_minutes: int = 30

@lru_cache()
def get_settings():
    return Settings()