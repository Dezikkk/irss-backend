from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import select, col

from app.config import get_settings
from app.database import SessionDep
from app.models.models import User, UserRole
from app.core.security import create_access_token

settings = get_settings()
router = APIRouter(prefix="/debug", tags=["Debug"])

@router.get("/info")
async def info():
    """
    dump wszystkich zmiennych srodowiskowych
    tak wiem mega bezpieczne :3
    """
    
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
        "BACKEND_URL": settings.BACKEND_URL
    }
    
    
class DebugUserRequest(BaseModel):
    email: str
    role: UserRole = UserRole.STUDENT
    campaign_id: int | None = None
    
@router.post("/create-user")
async def create_test_user(
    payload: DebugUserRequest,
    db: SessionDep
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
    
    return {
        "message": f"Stworzono/Zaktualizowano usera: {user.email} [{user.role}]",
        "access_token": access_token,
        "token_type": "bearer",
        "campaigns": user.allowed_campaign_ids
    }