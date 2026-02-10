from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import select, col, func

from app.database import SessionDep
from app.serializers.schemas import (
    EmailRequest, MagicLinkResponse, 
    RegisterWithInviteRequest, TokenResponse
)
from app.core.security import (
    create_access_token, generate_magic_token, 
    send_magic_link_email, validate_uni_email
)
from app.models.models import (
    AuthToken, Invitation,
    RegistrationCampaign, RegistrationGroup,
    User, UserRole
)

from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Auth"])

# rejestracja z kodem (dla nowych osób) 
@router.post("/register-with-invite", response_model=MagicLinkResponse)
async def register_with_invite(
    payload: RegisterWithInviteRequest,
    db: SessionDep
):
    """
    Tworzy konto lub dopisuje istniejącego użytkownika do nowej kampanii na podstawie kodu zaproszenia wygenerowanego przez Starostę.
    Następnie wysyła maila do logowania.
    System automatycznie przypisuje rolę i kampanię zdefiniowane w zaproszeniu.
    Obsługuje dopisywanie wielu kampanii do jednego adresu e-mail.
    """
    email = payload.email
    code = payload.invite

    # waliduj domene uni
    if not validate_uni_email(email):
        raise HTTPException(
            status_code=400, 
            detail=f"Wymagany mail w domenie {settings.ALLOWED_DOMAINS}"
        )

    # pobranie i walidacja zapro
    invite = db.exec(select(Invitation).where(Invitation.token == code)).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Nieprawidłowy kod zaproszenia.")
    
    if not invite.is_valid:
        raise HTTPException(status_code=400, detail="Ten kod zaproszenia wygasł lub został w pełni wykorzystany.")

    # walidacja kampanii (jeśli kod dotyczy kampanii)
    if invite.target_campaign_id is not None:
        campaign = db.get(RegistrationCampaign, invite.target_campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Kampania z zaproszenia już nie istnieje.")
        if not campaign.is_active:
            raise HTTPException(status_code=400, detail="Kampania jeszcze się nie zaczęła albo już się skończyła.")

    # sprawdź czy user już istnieje
    user = db.exec(select(User).where(User.email == email)).first()
    new_admin = False # Rozpatrowywanie przypadku tworzenia nowego starosty

    if user:
    # --- SCENARIUSZ A: UPDATE ISTNIEJĄCEGO USERA ---
        
        # Logika: Jeśli to link do kampanii (student), a user tej kampanii nie ma -> dodaj.
        if invite.target_campaign_id is not None:
            # sprawdź duplikaty w liście
            if invite.target_campaign_id not in user.allowed_campaign_ids:
                current_campaigns = list(user.allowed_campaign_ids)
                current_campaigns.append(invite.target_campaign_id)
                user.allowed_campaign_ids = current_campaigns
                
                db.add(user)
                message_detail = "Zaktualizowano Twoje konto o dostęp do nowego rocznika."
            else:
                message_detail = "Masz już dostęp do tej kampanii. Logowanie..."
        else:
            message_detail = "Konto już istnieje. Logowanie..."

    else:
    # --- SCENARIUSZ B: TWORZENIE NOWEGO USERA ---
        
        # przygotuj listę kampanii
        initial_campaigns = []
        if invite.target_campaign_id is not None:
            initial_campaigns.append(invite.target_campaign_id)

        new_user = User(
            email=email,
            role=invite.target_role,                 
            allowed_campaign_ids=initial_campaigns 
        )
        db.add(new_user)
        message_detail = "Konto utworzone pomyślnie!"
        if invite.target_role == UserRole.ADMIN:
            new_admin = True

    # generuj i wyslij magic link
    token = generate_magic_token()
    expires_at = datetime.now() + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    
    auth_token = AuthToken(
        email=email,
        token=token,
        expires_at=expires_at
    )

    db.add(auth_token)

    # podbij licznik uzycia zaproszenia
    invite.current_uses += 1
    db.add(invite)

    db.commit()
    
    # Jeżeli utworzono nowego starostę, magic link przekierowuje do panelu starosty 
    await send_magic_link_email(email, token, invite=code if not new_admin else None)

    return MagicLinkResponse(
        message="Sukces!",
        detail=f"{message_detail} Na adres {email} wysłaliśmy link logujący."
    )

# logowanie (dla osób które już mają konto)
@router.post("/request-magic-link", response_model=MagicLinkResponse)
async def request_magic_link(
    email_request: EmailRequest,
    db: SessionDep
):
    """
    Wysyła jednorazowy token logowania na e-mail dla użytkowników, którzy mają już konto w systemie.
    """
    
    email = email_request.email
    
    # czy taki student w ogóle istnieje
    user = db.exec(select(User).where(User.email == email)).first()
    if not user:
         raise HTTPException(
            status_code=404,
            detail="Taki użytkownik nie istnieje. Jeśli masz kod od starosty, użyj rejestracji z kodem."
        )

    # generowanie tokenu logowania
    token = generate_magic_token()
    expires_at = datetime.now() + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    
    auth_token = AuthToken(
        email=email,
        token=token,
        expires_at=expires_at
    )
    
    db.add(auth_token)
    db.commit()
    
    await send_magic_link_email(email, token)
    
    return MagicLinkResponse(
        message="Sprawdź skrzynkę",
        detail=f"Wysłano link logowania na adres {email}."
    )
    
  
@router.get("/verify", response_model=TokenResponse)
async def verify_token(token: str, db: SessionDep, invite: str | None = None):
    """
    Weryfikuje link z maila i loguje użytkownika.
    
    Zmiana: Nie sprawdza powiązania z kampanią ani jej istnienia. 
    Po prostu przekierowuje na frontend z tokenem JWT w ciasteczku.
    """
    
    # 1. Sprawdź token autoryzacyjny (Magic Link)
    auth_token = db.exec(select(AuthToken).where(AuthToken.token == token)).first()
    
    if not auth_token or not auth_token.is_valid:
        raise HTTPException(
            status_code=401, 
            detail="Link jest nieważny lub wygasł."
        )

    # 2. Sprawdź użytkownika
    user = db.exec(select(User).where(User.email == auth_token.email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje.")
    
    # 3. Ustalanie przekierowania
    # Domyślny redirect na stronę główną lub panel (zależnie od tego jak masz ustawiony frontend)
    redirect = f"{settings.FRONTEND_URL}/"

    # Jeśli jest parametr invite, przekazujemy go do frontendu, 
    # ale BEZ odpytywania bazy o szczegóły kampanii.
    if invite:
        redirect = f"{settings.FRONTEND_URL}/?invite={invite}"
    else:
        # Logika dla zwykłego logowania (bez zaproszenia)
        if user.role == UserRole.ADMIN:
            redirect = f"{settings.FRONTEND_URL}/pages/PanelStarosty.html"
        else:
            # Domyślny panel dla studenta (jeśli istnieje taka ścieżka)
            redirect = f"{settings.FRONTEND_URL}/pages/StudentPanel.html"

    # 4. Generuj JWT
    access_token_expires = timedelta(hours=settings.SESSION_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )

    # 5. Unieważnij magic link (jednorazowy użytek)
    auth_token.is_used = True
    db.add(auth_token)
    db.commit()

    # 6. Zwróć przekierowanie z ciasteczkiem
    response = RedirectResponse(url=redirect)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=access_token_expires.total_seconds(),
        httponly=True,
        secure=True, # Wymagane dla samesite="none" (na produkcji musi być HTTPS)
        samesite="none",
        path="/"
    )
    
    return response