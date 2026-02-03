import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from sqlalchemy import case, func, and_ 
from sqlmodel import select, col

from app.config import get_settings
from app.core.assignment import resolve_campaign_logic
from app.database import SessionDep
from app.core.dependencies import CurrentAdmin
from app.models.models import (
    Invitation, Registration, RegistrationCampaign, RegistrationGroup, 
    RegistrationStatus, UserRole
    )
from app.serializers.schemas import (
    BulkGroupCreateRequest, BulkGroupResponse, CampaignCreateRequest, CampaignDetailResponse, 
    CampaignResponse, CampaignUpdateRequest, CreateStudentInviteRequest, GroupStatsResponse, 
    GroupUpdateRequest, InvitationLinkResponse
    )

settings = get_settings()
router = APIRouter(prefix="/admin", tags=["Admin(Starosta)"])

# 
@router.post("/create-student-invite", response_model=InvitationLinkResponse)
async def create_student_invite(
    payload: CreateStudentInviteRequest,
    current_user: CurrentAdmin,
    db: SessionDep
):
    """
    Generuje link zaproszeniowy dla studentów z tego samego rocznika.
    Tylko dla STAROSTY.
    
    link, który po przesłaniu studentom pozwala im na założenie konta bez ręcznej weryfikacji przez administratora systemu.
    """
    
    # sprawdź czy kampania istnieje i należy do tego starosty
    campaign = db.get(RegistrationCampaign, payload.campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampania nie istnieje.")
        
    if campaign.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Nie możesz zapraszać do kampanii, której nie stworzyłeś.")
    
    # generuj token
    token = secrets.token_urlsafe(16)
    expires_at = datetime.now() + timedelta(days=payload.days_valid)

    # stwórz zaproszenie w bazie
    invite = Invitation(
        token=token,
        target_role=UserRole.STUDENT,       # tworzymy studenta
        target_campaign_id=payload.campaign_id,
        max_uses=payload.max_uses,
        expires_at=expires_at
    )
    
    db.add(invite)
    db.commit()
    
    # TODO: obecnie link nie bedzie działał bo register-with-invite przyjmuje POST. trzeba tam wkleic endpoint frontendu
    # jak bedzie frontend to dokonczyc zeby poprosic usera o email i dalej wysylac posta na register-with-invite
    full_link = f"{settings.FRONTEND_URL}/register?code={token}"

    return InvitationLinkResponse(
        invite_link=full_link,
        code=token,
        expires_at=expires_at,
        max_uses=payload.max_uses
    )
    
@router.post("/campaigns/create", response_model=CampaignResponse)
async def create_campaign(
    payload: CampaignCreateRequest,
    current_user: CurrentAdmin,  # walidacja autoryzacji: tylko starosta przejdzie
    db: SessionDep
):
    """
    Tworzy nową kampanię zapisów (np. 'Lato 2026').
    
    Data zakończenia musi być późniejsza niż data rozpoczęcia.
    
    Wymaga podania metody przydziału (assignment_method), domyślnie FCFS.
    """
    
    # walidajca dat
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(
            status_code=400,
            detail="Data zakończenia musi być późniejsza niż data rozpoczęcia."
        )

    # tworzenie obiektu bazy danych
    new_campaign = RegistrationCampaign(
        title=payload.title,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        assignment_method=payload.assignment_method,
        creator_id=current_user.id, # starosta jako autor i admin kampanii
    )

    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)

    # obliczanie czy jest aktywna
    now = datetime.now()
    is_active_now = new_campaign.starts_at <= now <= new_campaign.ends_at

    if new_campaign.id is None:
        raise HTTPException(status_code=500, detail="Błąd zapisu kampanii do bazy danych")

    # dodawanie nowej kampanii do listy usera zeby mogl accessowac
    current_ids = list(current_user.allowed_campaign_ids)
    if new_campaign.id not in current_ids:
        current_ids.append(new_campaign.id)
        current_user.allowed_campaign_ids = current_ids
        
        db.add(current_user)
        db.commit()

    return CampaignResponse(
        id=new_campaign.id, 
        title=new_campaign.title,
        starts_at=new_campaign.starts_at,
        ends_at=new_campaign.ends_at,
        is_active=is_active_now,
        assignment_method=new_campaign.assignment_method
    )
    
@router.post("/campaigns/{campaign_id}/groups", response_model=BulkGroupResponse)
async def add_groups_to_campaign(
    campaign_id: int,
    payload: BulkGroupCreateRequest,
    current_user: CurrentAdmin,
    db: SessionDep
):
    """
    Umożliwia dodanie wielu grup zajęciowych do istniejącej kampanii w jednym zapytaniu.
    Waliduje, czy kampania należy do zalogowanego Starosty.
    Wysyłając listę nazw (np. L1, L2, L3) i limitów, system automatycznie powiąże je z wybraną kampanią.
    """
    
    # pobiera kampanię z bazy i spr czy istnieje
    campaign = db.get(RegistrationCampaign, campaign_id)
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Taka kampania nie istnieje.")

    # zabezpieczenie przed nieautoryzowana edycja kampanii przez innego staroste
    # jeśli ID twórcy kampanii jest inne niż ID zalogowanego usera -> Błąd 403
    if campaign.creator_id != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="Nie masz uprawnień do edycji tej kampanii (nie jesteś jej autorem)."
        )

    # pętla tworząca obiekty grup
    new_groups = []
    for group_data in payload.groups:
        group = RegistrationGroup(
            name=group_data.name,
            limit=group_data.limit,
            campaign_id=campaign_id 
        )
        new_groups.append(group)

    # zapis do bazy wszystkich grup na raz
    db.add_all(new_groups)
    db.commit()

    return BulkGroupResponse(
        message="Grupy zostały pomyślnie dodane.",
        created_count=len(new_groups)
    )
    
@router.get("/campaigns/{campaign_id}", response_model=CampaignDetailResponse)
async def get_campaign_details(
    campaign_id: int,
    current_user: CurrentAdmin,
    db: SessionDep
):
    """
    Pobiera szczegóły kampanii wraz ze statystykami zapisów.
    Zwraca pełne dane o kampanii, w tym listę grup, ich limity oraz liczbę osób, które wybrały daną grupę jako priorytet nr 1.
    
    `first_priority_count`: Liczba studentów, którzy ustawili grupę na 1. miejscu (popyt).
    `current_count`: Liczba studentów ostatecznie przydzielonych (`ASSIGNED`) do grupy.
    """
    
    # pobierz kampanie
    campaign = db.get(RegistrationCampaign, campaign_id)
    
    # walidacje
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampania nie istnieje.")

    if campaign.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="To nie Twoja kampania. Nie możesz podglądać wyników.")

    if campaign.id is None:
        raise HTTPException(status_code=500, detail="Błąd integralności danych (brak ID kampanii)")
    
    statement = (
        select(
            RegistrationGroup,
            # licznik 1: ile osob ma status ASSIGNED(przydzielono)
            # bedzie działać po zadzialaniu algorytmu przydzielajacego
            func.count(
                case(
                    (col(Registration.status) == RegistrationStatus.ASSIGNED, 1)
                )
            ),
            # licznik 2: popularność
            # ile osob dala ta grupe na pierwszy priorytet
            func.count(
                case(
                    (col(Registration.priority) == 1, 1)
                )
            )
        )
        .outerjoin(
            Registration,
            and_(
                col(Registration.group_id) == col(RegistrationGroup.id),
                col(Registration.status) != RegistrationStatus.REJECTED 
                # ^ ignorujemy odrzuconych, bierzemy SUBMITTED i ASSIGNED
            )
        )
        .where(col(RegistrationGroup.campaign_id) == campaign_id)
        .group_by(col(RegistrationGroup.id))
    )
    
    results = db.exec(statement).all()
    
    groups_response = []
    total_students = 0 # sumuje przypisanych (ASSIGNED)

    for group, assigned_count, priority_count in results:

        total_students += assigned_count
        if group.id is None: continue 

        groups_response.append(
            GroupStatsResponse(
                id=group.id,
                name=group.name,
                limit=group.limit,
                first_priority_count=priority_count,    # ile chętnych na 1. wybór
                current_count=assigned_count,           # ile miejsc zajętych(po przydzielniu)
                is_full=assigned_count >= group.limit
            )
        )

    now = datetime.now()
    is_active_now = campaign.starts_at <= now <= campaign.ends_at

    return CampaignDetailResponse(
        id=campaign.id,
        title=campaign.title,
        starts_at=campaign.starts_at,
        ends_at=campaign.ends_at,
        is_active=is_active_now,
        total_registered_students=total_students,
        groups=groups_response
    )
    
    
@router.patch("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    payload: CampaignUpdateRequest,
    current_user: CurrentAdmin,
    db: SessionDep
):
    """
    Edycja danych kampanii (tytuł, daty).
    Pozwala na częściową aktualizację kampanii (np. zmianę samego tytułu lub przedłużenie czasu zapisów).
    Jeśli zmienisz `assignment_method`, to przy następnym uruchomieniu `resolve` 
    system automatycznie wykryje zmianę i przeliczy wyniki na nowo.
    """
    # pobierz kampanię z bazy
    campaign = db.get(RegistrationCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampania nie istnieje.")

    # sprawdź czyja to kampania
    if campaign.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="To nie Twoja kampania.")

    # logika aktualizacji (z validation dat)
    # przygotuj dane do zmiany (odrzucamy to co jest None w payloadzie)
    update_data = payload.model_dump(exclude_unset=True)
    
    # walidacja dat (jeśli user zmienia którąś z dat, musimy sprawdzić spójność)
    # bierzemy nową datę z payloadu, a jak jej nie ma, to starą z bazy
    new_start = payload.starts_at or campaign.starts_at
    new_end = payload.ends_at or campaign.ends_at
    
    if new_end <= new_start:
        raise HTTPException(status_code=400, detail="Data zakończenia musi być późniejsza niż startu.")

    # aplikujemy zmiany
    for key, value in update_data.items():
        setattr(campaign, key, value)

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    # oblicza is_active do odpowiedzi
    now = datetime.now()
    is_active_now = campaign.starts_at <= now <= campaign.ends_at

    if campaign.id is None:
        raise HTTPException(status_code=500, detail="Błąd integralności danych: brak ID kampanii.")

    return CampaignResponse(
        id=campaign.id, 
        title=campaign.title,
        starts_at=campaign.starts_at,
        ends_at=campaign.ends_at,
        is_active=is_active_now,
        assignment_method=campaign.assignment_method
    )



@router.patch("/groups/{group_id}")
async def update_group(
    group_id: int,
    payload: GroupUpdateRequest,
    current_user: CurrentAdmin,
    db: SessionDep
):
    """
    Pozwala na zmianę nazwy grupy lub modyfikację limitu miejsc.
    """
    # pobierz grupę z db
    group = db.get(RegistrationGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Grupa nie istnieje.")

    # pobierz kampanię tej grupy, żeby sprawdzić właściciela
    campaign = group.campaign
    if not campaign or campaign.creator_id is None:
        raise HTTPException(status_code=404, detail="Błąd spójności danych (brak kampanii).")

    # sprawdź uprawnienia (czy starosta jest właścicielem kampanii, do której należy grupa)
    if campaign.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Brak uprawnień.")

    # aplikuj zmiany
    update_data = payload.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(group, key, value)

    db.add(group)
    db.commit()
    db.refresh(group)

    return {
        "message": "Zaktualizowano grupę",
        "group": {
            "id": group.id,
            "name": group.name,
            "limit": group.limit
        }
    }
    

@router.post("/campaigns/{campaign_id}/resolve")
async def resolve_campaign(
    campaign_id: int,
    current_user: CurrentAdmin,
    db: SessionDep,
    force: bool = False # mozliwosc wymuszenia ponownego przelosowania
):
    """
    Uruchomienie algorytmu przydziału,
    Zamyka zapisy i rozdziela studentów do grup na podstawie ich priorytetów oraz czasu wysłania wniosku.
    
    Jeżeli assignment_method zostanie zedytowane po pomyślnym resolve'owaniu to zadziała od nowa algorytm przydzielania.
    A jeżeli last_resolved_method != None lub force == false to nie przydziela studentow od nowa tylko przechodzi dalej
    """
     # pobierz kampanie z db
    campaign = db.get(RegistrationCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampania nie istnieje.")

    if campaign.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Brak uprawnień.")

    # check czy metoda losowania w bazie jest taka sama jak ta, którą ostatnio liczyliśmy
    if not force and campaign.last_resolved_method == campaign.assignment_method:
        return {
            "message": "Wyniki są już aktualne dla wybranej metody.",
            "detail": f"Ostatnio użyto metody: {campaign.last_resolved_method}. Zmień metodę lub użyj flagi force=true.",
            "status": "skipped" # informacja dla frontendu że nic się nie zmieniło
        }

    # uruchomienie algorytmu losowania 
    # (tylko jeśli last_resolved_method i assignment_method są różne lub force=True)
    try:
        stats = resolve_campaign_logic(db, campaign)
        
        # zapis stanu do db
        campaign.last_resolved_method = campaign.assignment_method
        
        # campaign.is_active = False 
        
        db.add(campaign)
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"Błąd algorytmu: {e}")
        raise HTTPException(status_code=500, detail="Wystąpił błąd algorytmu.")

    return {
        "message": "Algorytm zakończony pomyślnie.",
        "stats": stats,
        "new_method_applied": campaign.assignment_method
    }   
    


@router.post("/campaigns/{campaign_id}/download")
async def download_campaign_results(
    campaign_id: int,
    current_user: CurrentAdmin,
    db: SessionDep
):
    """
    Pobranie tabelki w excelu z przydziałem do grup w danej kampanii.
    UNINPLEMNETED YET
    """
    pass