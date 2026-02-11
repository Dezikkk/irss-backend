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
    AvailableCampaignsResponse,
    StudentGroupView, 
)

settings = get_settings()
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
async def get_user_session(current_user: CurrentUser, db: SessionDep):
    """
    Zwraca informacje o aktualnie zalogowanym użytkowniku
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
            "active_campaigns": campaigns_count,
            "actions": ["create_campaign", "view_stats", "manage_groups"]
        }

    elif current_user.role == "student":
        registrations = current_user.registrations
        return {
            **base_data,
            "my_registrations_count": len(registrations),
            "status": "Zapisany" if registrations else "Niezapisany",
            "actions": ["join_group"]
        }


@router.get("/available-campaigns", response_model=AvailableCampaignsResponse)
async def get_available_campaigns(
    current_user: CurrentUser,
    db: SessionDep
):
    """
    Zwraca kampanie (wraz z grupami) i statusem na podstawie allowed_campaign_ids przypisanych do studenta.
    Pokazuje też kampanie które sie zakonczyly i nie rozpoczeły oraz status tekstowy.
    """
    
    if not current_user.allowed_campaign_ids:
        return AvailableCampaignsResponse(
            created_campaigns=[],
            campaigns=[]
        )

    # 1. Pobieranie kampanii
    statement = (
        select(RegistrationCampaign)
        .where(col(RegistrationCampaign.id).in_(current_user.allowed_campaign_ids)) 
        #.where(RegistrationCampaign.is_active == True)
        .options(selectinload(getattr(RegistrationCampaign, "groups"))) 
    )
    
    campaigns = db.exec(statement).all()

    if not campaigns:
        return AvailableCampaignsResponse(
            created_campaigns=[],
            campaigns=[]
        )
    
    created_campaigns = []
    campaigns_in = []

    for campaign in campaigns:
        if campaign.id is None:
            continue

        if campaign.creator_id == current_user.id:
            created_campaigns.append(campaign.id)
        campaigns_in.append(campaign.id)
        
    return AvailableCampaignsResponse(
        created_campaigns=created_campaigns,
        campaigns=campaigns_in
    )