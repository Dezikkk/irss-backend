from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import select, col

from app.config import get_settings
from app.database import SessionDep
from app.models.models import User, UserRole, StudyProgram
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
        "BASE_URL": settings.BASE_URL
    }
    
    
class DebugUserRequest(BaseModel):
    email: str
    role: UserRole = UserRole.STUDENT
    program_name: str = "Informatyka Testowa"
    
@router.post("/create-user")
async def create_test_user(
    payload: DebugUserRequest,
    db: SessionDep
):
    """
    Tworzy usera z pominięciem emaili.
    Potrafi jeszcze aktualizować isniejącego usera.
    Automatycznie tworzy lub przypisuje StudyProgram.
    Zwraca token JWT bearer potrzebny do autoryzacji
    """
    
    # 1. Ogarnij rocznik (musi być, żeby cokolwiek działało)
    program = db.exec(
        select(StudyProgram).where(col(StudyProgram.name) == payload.program_name)
    ).first()
    
    # jak nie ma takiego study programu to utworz nowy
    if not program:
        program = StudyProgram(name=payload.program_name)
        db.add(program)
        db.commit()
        db.refresh(program)
    
    # sprawdz czy user istnieje
    user = db.exec(
        select(User).where(col(User.email) == payload.email)
    ).first()
    
    if not user:
        # tworzymy nowego usera
        user = User(
            email=payload.email,
            role=payload.role,
            study_program_id=program.id # dodajemy go do study programu
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # jesli user juz istnieje to tylko aktualizujemy mu rolę/rocznik dla wygody
        user.role = payload.role
        user.study_program_id = program.id # type: ignore
        db.add(user)
        db.commit()
        db.refresh(user)

    # generuje token od razu, nie trzeba na mailu klikac
    if user.id is None:
         return {"error": "User ID is missing"}

    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {
        "message": f"Stworzono/Zaktualizowano usera: {user.email} [{user.role}]",
        "access_token": access_token,
        "token_type": "bearer",
        "study_program": program.name
    }