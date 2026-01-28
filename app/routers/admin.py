from datetime import datetime, timedelta
import secrets
from fastapi import APIRouter, HTTPException

from app.database import SessionDep
from app.core.dependencies import CurrentAdmin, CurrentUser 
from app.models.models import Invitation, UserRole
from app.config import get_settings
from app.serializers.schemas import CreateStudentInviteRequest, InvitationLinkResponse

settings = get_settings()
router = APIRouter(prefix="/admin", tags=["Admin", "Starosta"])

# 
@router.post("/create-student-invite", response_model=InvitationLinkResponse)
async def create_student_invite(
    payload: CreateStudentInviteRequest,
    current_user: CurrentUser,
    db: SessionDep
):
    """
    Tylko dla STAROSTY.
    Generuje link zaproszeniowy dla studentów z tego samego rocznika.
    """
    # sprawdź uprawnienia czy osoba tworząca jest starostą(student nie moze tworzyc zaproszen)
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Brak uprawnień. Tylko starosta może generować zaproszenia."
        )

    if not current_user.study_program_id:
        raise HTTPException(
            status_code=400,
            detail="Nie jesteś przypisany do żadnego rocznika, więc nie możesz zapraszać."
        )

    # generuj token
    token = secrets.token_urlsafe(16)
    expires_at = datetime.now() + timedelta(days=payload.days_valid)

    # stwórz zaproszenie w bazie
    invite = Invitation(
        token=token,
        target_role=UserRole.STUDENT,       # tworzymy studenta
        target_study_program_id=current_user.study_program_id, # na tym samym roku co starota tworzacy zapro
        max_uses=payload.max_uses,
        expires_at=expires_at
    )
    
    db.add(invite)
    db.commit()

    # Zbuduj pełny link 
    # TODO: jak sie podłączy z frontendem to bedzie trzeba zmienic sciezke prawdopodobine
    full_link = f"{settings.BASE_URL}/auth/register-with-invite?code={token}"

    return InvitationLinkResponse(
        invite_link=full_link,
        code=token,
        expires_at=expires_at,
        max_uses=payload.max_uses
    )