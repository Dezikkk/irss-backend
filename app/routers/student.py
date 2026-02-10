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
    Invitation
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

    # Get the campaign through the invite code
    campaign = db.exec(
        select(Invitation)
        .where(col(Invitation.token) == payload.invite)
    ).one().target_campaign

    if not campaign or campaign.id is None:
        raise HTTPException(status_code=404, detail="Grupa nie jest przypisana do kampanii.")

    # Pobierz id grupy z najmniejszym indeksem,
    # żeby przesunąc id względem tabeli.
    all_campaign_groups_ids = [g.id for g in campaign.groups if g.id is not None]
    group_id_offset = min(all_campaign_groups_ids)-1 # oczekujemy id od 1 a nie od 0

    # czy student ocenił WSZYSTKIE grupy?
    # pobieramy wszystkie grupy z tej kampanii
    submitted_groups_ids = [p.group_id+group_id_offset for p in payload.preferences]

    if set(all_campaign_groups_ids) != set(submitted_groups_ids):
        raise HTTPException(
            status_code=400, 
            detail="Musisz ustawić priorytet dla WSZYSTKICH dostępnych grup w kampanii."
        )

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
    ).all()

    #if existing_reg:
        #raise HTTPException(status_code=400, detail="Już złożyłeś wniosek w tej kampanii. Edycja jest zablokowana.")

    new_registrations = []
    
    for pref in payload.preferences:
        if current_user.id is None: 
            raise HTTPException(status_code=500, detail="User ID error")

        reg = Registration(
            user_id=current_user.id,
            group_id=pref.group_id+group_id_offset,
            priority=pref.priority,
            status=RegistrationStatus.SUBMITTED, # status oczekujący
            created_at=datetime.now() 
        )
        new_registrations.append(reg)

    # zapisz wszystko w akcji z db
    try:
        # Usuwanie starych zapisów jeżeli zostały nadpisane
        for old_registration in existing_reg:
            db.delete(old_registration)
                
        db.add_all(new_registrations)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Błąd zapisu bazy danych: {str(e)}")

    return {
        "message": "Wniosek przyjęty." if not existing_reg else "Wniosek nadpisany.", 
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