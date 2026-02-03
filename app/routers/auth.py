from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import select

from app.database import SessionDep
from app.serializers.schemas import (
    EmailRequest, MagicLinkResponse, 
    RegisterWithInviteRequest, TokenResponse
)
from app.core.security import (
    create_access_token, generate_magic_token, 
    send_magic_link_email, validate_uni_email
)
from app.models.models import AuthToken, Invitation, RegistrationCampaign, User
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
    System automatycznie przypisuje rolę i kampanię zdefiniowane w zaproszeniu.
    Obsługuje dopisywanie wielu kampanii do jednego adresu e-mail.
    """
    email = payload.email
    code = payload.invite_code

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
        campaign_exists = db.get(RegistrationCampaign, invite.target_campaign_id)
        if not campaign_exists:
            raise HTTPException(status_code=404, detail="Kampania z zaproszenia już nie istnieje.")

    # sprawdź czy user już istnieje
    user = db.exec(select(User).where(User.email == email)).first()

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

    # podbij licznik uzycia zaproszenia
    invite.current_uses += 1
    db.add(invite)
    
    # zapisz wszystko w bazie
    db.commit() 

    # generuj i wyslij magic link
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
    
  
# weryfikacja (kliknięcie w link z maila) 
@router.get("/verify", response_model=TokenResponse)
async def verify_token(token: str, db: SessionDep):
    """
    Weryfikuje link z maila. 
    Jeśli OK -> Przekierowuje na frontend z tokenem w URL po znaku # (hash).
    Jeśli BŁĄD -> Przekierowuje na stronę błędu.
    
    Po pomyślnej weryfikacji token zostaje oznaczony jako zużyty (`is_used = True`).
    Zwrócony token JWT należy przesyłać w nagłówku `Authorization: Bearer <token>` 
    przy każdym kolejnym zapytaniu.
    """
    
    # sprawdz authtoken w db
    auth_token = db.exec(select(AuthToken).where(AuthToken.token == token)).first()
    
    if not auth_token or not auth_token.is_valid:
        raise HTTPException(
            status_code=401, 
            detail="Link jest nieważny lub wygasł."
        )

    # sprawdz usera w db
    user = db.exec(select(User).where(User.email == auth_token.email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje.")

    # uniewaznij magic link
    auth_token.is_used = True
    db.add(auth_token)
    db.commit()

    # generuj jwt
    access_token_expires = timedelta(hours=settings.SESSION_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": str(user.id)},  # id usera zakodowane
        expires_delta=access_token_expires
    )
    
    # return TokenResponse(
    #     access_token=access_token,
    # )
    
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth_callback.html#access_token={access_token}"
    )
