from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter
from sqlmodel import select, col
from sqlalchemy import func
from sqlalchemy.orm import selectinload

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
    Zwraca kampanie (wraz z grupami) i statusem na podstawie allowed_campaign_ids przypisanych do studenta.
    Pokazuje też kampanie które sie zakonczyly i nie rozpoczeły oraz status tekstowy.
    """
    now = datetime.now()
    
    if not current_user.allowed_campaign_ids:
        return []

    # 1. Pobieranie kampanii
    statement = (
        select(RegistrationCampaign)
        .where(col(RegistrationCampaign.id).in_(current_user.allowed_campaign_ids)) 
        .where(RegistrationCampaign.is_active == True)
        .options(selectinload(getattr(RegistrationCampaign, "groups"))) 
    )
    
    campaigns = db.exec(statement).all()

    if not campaigns:
        return []

    # 2. Zbieramy ID wszystkich grup
    all_group_ids = [
        group.id 
        for campaign in campaigns 
        for group in campaign.groups 
        if group.id is not None
    ]

    # 3. Batch Query: Liczymy "jedynki"
    counts_statement = (
        select(Registration.group_id, func.count(col(Registration.id)))
        .where(col(Registration.group_id).in_(all_group_ids))
        .where(Registration.priority == 1)
        .where(Registration.status != RegistrationStatus.REJECTED)
        .group_by(col(Registration.group_id))  # Tutaj col() naprawia błąd w group_by
    )
    
    counts_result = db.exec(counts_statement).all()
    
    # NAPRAWA: Dict jest teraz zaimportowany
    priority_map: Dict[int, int] = {row[0]: row[1] for row in counts_result}

    # 4. Budowanie odpowiedzi
    response = []

    for campaign in campaigns:
        if campaign.id is None:
            continue
        
        if now < campaign.starts_at:
            status_msg = "Wkrótce"
        elif now > campaign.ends_at:
            status_msg = "Zakończone"
        else:
            status_msg = "Aktywne"

        groups_view = []
        for group in campaign.groups:
            if group.id is None:
                continue

            count = priority_map.get(group.id, 0)

            groups_view.append(StudentGroupView(
                id=group.id,
                name=group.name,
                limit=group.limit,
                first_priority_count=count 
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