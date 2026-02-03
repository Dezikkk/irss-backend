from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException
from sqlmodel import select, col
from sqlalchemy import func

from app.database import SessionDep
from app.core.dependencies import CurrentUser
from app.models.models import (
    RegistrationGroup, 
    Registration, 
    RegistrationStatus,
)
from app.serializers.schemas import (
    CampaignRegistrationRequest,
)

router = APIRouter(prefix="/student", tags=["Student"])

@router.post("/register")
async def submit_preferences(
    payload: CampaignRegistrationRequest,
    current_user: CurrentUser,
    db: SessionDep
):
    """
    Student składa wniosek z preferencjami (ranking grup).
    Tworzy wpis dla KAŻDEJ grupy w kampanii ze statusem SUBMITTED.
    """
    
    if not payload.preferences:
        raise HTTPException(status_code=400, detail="Lista preferencji jest pusta.")

    # pobierz ID pierwszej grupy, żeby namierzyć kampanię
    first_group_id = payload.preferences[0].group_id
    first_group = db.get(RegistrationGroup, first_group_id)
    
    if not first_group or first_group.id is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono grupy.")
        
    campaign = first_group.campaign
    if not campaign or campaign.id is None:
        raise HTTPException(status_code=404, detail="Grupa nie jest przypisana do kampanii.")

    # sprawdzamy czy student ma uprawnienia do tej kampanii w allowed_campaign_ids
    if campaign.id not in current_user.allowed_campaign_ids:
        raise HTTPException(status_code=403, detail="Nie masz uprawnień do zapisu w tej kampanii.")

    now = datetime.now()
    if not (campaign.starts_at <= now <= campaign.ends_at):
        raise HTTPException(status_code=400, detail="Termin składania wniosków minął lub jeszcze się nie zaczął.")

    # sprawdza czy student już nie złożył wniosku w tej kampanii
    existing_reg = db.exec(
        select(Registration)
        .join(RegistrationGroup, col(Registration.group_id) == col(RegistrationGroup.id))
        .where(col(Registration.user_id) == current_user.id)
        .where(col(RegistrationGroup.campaign_id) == campaign.id)
    ).first()

    if existing_reg:
        raise HTTPException(status_code=400, detail="Już złożyłeś wniosek w tej kampanii. Edycja jest zablokowana.")

    # czy student ocenił WSZYSTKIE grupy?
    # pobieramy wszystkie grupy z tej kampanii
    all_campaign_groups_ids = [g.id for g in campaign.groups if g.id is not None]
    submitted_groups_ids = [p.group_id for p in payload.preferences]

    if set(all_campaign_groups_ids) != set(submitted_groups_ids):
        raise HTTPException(
            status_code=400, 
            detail="Musisz ustawić priorytet dla WSZYSTKICH dostępnych grup w kampanii."
        )

    new_registrations = []
    
    for pref in payload.preferences:
        if current_user.id is None: 
            raise HTTPException(status_code=500, detail="User ID error")

        reg = Registration(
            user_id=current_user.id,
            group_id=pref.group_id,
            priority=pref.priority,
            status=RegistrationStatus.SUBMITTED, # status oczekujący
            created_at=datetime.now() 
        )
        new_registrations.append(reg)

    # zapisz wszystko w akcji z db
    try:
        db.add_all(new_registrations)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Błąd zapisu bazy danych: {str(e)}")

    return {
        "message": "Wniosek przyjęty.", 
        "campaign": campaign.title,
        "submitted_count": len(new_registrations)
    }
    
@router.get("/my-groups")
async def get_my_groups(current_user: CurrentUser, db: SessionDep):
    """
    Zwraca grupy, do których student się zapisał, wraz ze statusem i priorytetem.
    """
    
    # prosty join żeby pobrać nazwy grup
    results = db.exec(
        select(RegistrationGroup, Registration)
        .join(Registration, col(Registration.group_id) == col(RegistrationGroup.id))
        .where(col(Registration.user_id) == current_user.id)
    ).all()
    
    my_groups = []
    for group, reg in results:
        my_groups.append({
            "group_name": group.name,
            "status": reg.status,
            "priority": reg.priority,
            "registered_at": reg.created_at 
        })
        
    return my_groups