from datetime import datetime
from typing import List
from fastapi import APIRouter
from sqlmodel import select, col
from sqlalchemy import func

from app.config import get_settings
from app.database import SessionDep
from app.core.dependencies import CurrentUser
from app.models.models import (
    RegistrationCampaign, 
    Registration, 
    RegistrationStatus,
)
from app.serializers.schemas import (
    StudentCampaignView, 
    StudentGroupView, 
)

settings = get_settings()
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/dashboard")
async def get_dashboard(current_user: CurrentUser, db: SessionDep):
    """
    Zwraca spersonalizowany dashboard (w zaleznosci od roli daje inne dane)
    Wymaga tokenu autorazycjnego jwt
    """
    
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
            "actions": ["join_group"]
        }


# TODO: Zawiera N+1 problem, naprawic w przyszłości
# przy duzej ilosci kampanii moze powodowac opoznienia bo duzo razy querry do db
@router.get("/available-campaigns", response_model=List[StudentCampaignView])
async def get_available_campaigns(
    current_user: CurrentUser,
    db: SessionDep
):
    """
    Zwraca kampanie (wraz z grupami) dostępne dla rocznika studenta.
    Pokazuje też kampanie które sie zakonczyly i nie rozpoczeły oraz status tekstowy.
    """
    now = datetime.now()

    statement = (
        select(RegistrationCampaign)
        .where(col(RegistrationCampaign.study_program_id) == current_user.study_program_id)
        .where(col(RegistrationCampaign.is_active) == True)
        # .where(col(RegistrationCampaign.ends_at) >= now) # zeby bylo widac tez zakonczone kampaniee
    )
    
    campaigns = db.exec(statement).all()
    
    response = []
    
    for campaign in campaigns:
        if campaign.id is None:
            continue
        
        # logika statusu
        if now < campaign.starts_at:
            status_msg = "Wkrótce"
        elif now > campaign.ends_at:
            status_msg = "Zakończone"
        else:
            status_msg = "Aktywne"
        
        # budujemy listę grup z obliczonymi wolnymi miejscami
        groups_view = []
        for group in campaign.groups:
            if group.id is None:
                continue
            
            # liczenie popularnosci(chetnych na 1 wybór)
            priority_ones = db.exec(
                select(func.count(col(Registration.id)))
                .where(col(Registration.group_id) == group.id)
                .where(col(Registration.priority) == 1) # TYLKO PIERWSZE MIEJSCA
                .where(col(Registration.status) != RegistrationStatus.REJECTED)
            ).one()
            
            groups_view.append(StudentGroupView(
                id=group.id,
                name=group.name,
                limit=group.limit,
                first_priority_count=priority_ones 
            ))
            
        response.append(StudentCampaignView(
            id=campaign.id, 
            title=campaign.title,
            starts_at=campaign.starts_at,
            ends_at=campaign.ends_at,
            status=status_msg,
            groups=groups_view
        ))
        
    return response