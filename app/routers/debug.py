from fastapi import APIRouter

from app.config import get_settings

settings = get_settings()
router = APIRouter()

# dump wszystkich zmiennych srodowiskowych
# tak wiem mega bezpieczne :3
@router.get("/info")
async def info():
    return {
        "DATABASE_URL": settings.DATABASE_URL,
        "SECRET_KEY": settings.SECRET_KEY,
        "ALGORITHM": settings.ALGORITHM,
        "TOKEN_EXPIRE_MINUTES": settings.TOKEN_EXPIRE_MINUTES,
        "SESSION_EXPIRE_HOURS": settings.SESSION_EXPIRE_HOURS,
        "ALLOWED_DOMAINS": settings.ALLOWED_DOMAINS,
        "SMTP_HOST": settings.SMTP_HOST,
        "SMTP_PORT": settings.SMTP_PORT,
        "SMTP_USER": settings.SMTP_USER,
        "SMTP_PASSWORD": settings.SMTP_PASSWORD,
        "SMTP_FROM": settings.SMTP_FROM,
        "APP_NAME": settings.APP_NAME,
        "BASE_URL": settings.BASE_URL
    }