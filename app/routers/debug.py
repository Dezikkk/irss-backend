from fastapi import APIRouter, Response
from pydantic import BaseModel
from sqlmodel import select, col, MetaData

from app.config import get_settings
from app.database import SessionDep
from app.models.models import User, UserRole
from app.core.security import create_access_token

settings = get_settings()
router = APIRouter(prefix="/debug", tags=["Debug"])

@router.get("/env")
async def environment_variables_dump():
    """
    dump wszystkich zmiennych srodowiskowych
    tak wiem mega bezpieczne :3
    """
    
    return {
        "POSTGRES_DB": settings.POSTGRES_DB,
        "POSTGRES_USER": settings.POSTGRES_USER,
        "POSTGRES_PASSWORD": settings.POSTGRES_PASSWORD,
        "POSTGRES_HOST": settings.POSTGRES_HOST,
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
        "RESEND_API_KEY": settings.RESEND_API_KEY,
        "RESEND_EMAIL_FROMM": settings.RESEND_EMAIL_FROM,
        "APP_NAME": settings.APP_NAME,
        "BACKEND_URL": settings.BACKEND_URL,
        "BACKEND_PORT": settings.BACKEND_PORT,
        "FRONTEND_URL": settings.FRONTEND_URL,
        "DEBUG": settings.DEBUG,
        "DEFAULT_ADMIN_INVITE_TOKEN": settings.DEFAULT_ADMIN_INVITE_TOKEN
    }

@router.get("/database")
async def database_dump(
    db: SessionDep
):
    """
    Dump całej bazy danych.
    """

    meta = MetaData()
    meta.reflect(bind=db.get_bind())
    result = {}
    for table in meta.sorted_tables:
        result[table.name] = [dict(row._mapping) for row in db.exec(table.select())]
    return result
    
class DebugUserRequest(BaseModel):
    email: str
    role: UserRole = UserRole.STUDENT
    campaign_id: int | None = None
    
@router.post("/create-user")
async def create_test_user(
    payload: DebugUserRequest,
    db: SessionDep,
    response: Response
):
    """
    Tworzy usera z pominięciem emaili.
    Potrafi aktualizować istniejącego usera (zmienia rolę i dodaje dostęp do kampanii).
    Zwraca token JWT bearer potrzebny do autoryzacji.
    """
    
# sprawdz czy user istnieje
    user = db.exec(
        select(User).where(col(User.email) == payload.email)
    ).first()
    
    if not user:
        # tworzymy nowego usera
        initial_campaigns = []
        if payload.campaign_id is not None:
            initial_campaigns.append(payload.campaign_id)

        user = User(
            email=payload.email,
            role=payload.role,
            allowed_campaign_ids=initial_campaigns
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # jesli user juz istnieje to tylko aktualizujemy mu rolę
        # Jeśli podano campaign_id, dodajemy go do listy (jeśli go tam nie ma)
        if payload.campaign_id is not None:
            if payload.campaign_id not in user.allowed_campaign_ids:
                current_ids = list(user.allowed_campaign_ids)
                current_ids.append(payload.campaign_id)
                user.allowed_campaign_ids = current_ids

        db.add(user)
        db.commit()
        db.refresh(user)

    if user.id is None:
         return {"error": "User ID is missing"}
    
    access_token = create_access_token(data={"sub": str(user.id)})

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=60 * 60 * 24,
        httponly=True,
        secure= True,
        samesite="lax",
        path="/"
    )

    return {
        "message": f"Stworzono/Zaktualizowano usera: {user.email} [{user.role}]",
        "access_token": access_token,
        "token_type": "bearer",
        "campaigns": user.allowed_campaign_ids
    }