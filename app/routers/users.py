from fastapi import APIRouter, HTTPException

from app.database import SessionDep
from app.core.dependencies import CurrentUser
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/users", tags=["Users"])

# Zwraca spersonalizowany dashboard (w zaleznosci od roli daje inne dane)
# Wymaga tokenu autorazycjnego jwt
@router.get("/dashboard")
async def get_dashboard(current_user: CurrentUser, db: SessionDep):
    base_data = {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "program_name": current_user.study_program.name if current_user.study_program else "Brak przypisania"
    }

    if current_user.role == "starosta":
        campaigns_count = len(current_user.created_campaigns)
        return {
            **base_data,
            "dashboard_type": "ADMIN",
            "active_campaigns": campaigns_count,
            "actions": ["create_campaign", "view_stats", "manage_groups"]
        }

    elif current_user.role == "student":
        registrations = current_user.registrations
        return {
            **base_data,
            "dashboard_type": "STUDENT",
            "my_registrations_count": len(registrations),
            "status": "Zapisany" if registrations else "Niezapisany",
            "actions": ["join_group", "view_schedule"]
        }
        