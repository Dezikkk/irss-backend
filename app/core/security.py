import secrets
import aiosmtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Optional
from jose import jwt
from fastapi import HTTPException

from app.config import get_settings

settings = get_settings()

def validate_uni_email(email: str) -> bool:
    email_lower = email.lower()
    return any(email_lower.endswith(domain) for domain in settings.ALLOWED_DOMAINS)

def generate_magic_token() -> str:
    return secrets.token_urlsafe(32)

async def send_magic_link_email(email: str, token: str, invite: str = None):
    magic_link = f"{settings.BACKEND_URL}/auth/verify?token={token}"
    if invite:
        magic_link += f"&invite={invite}"

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = email
    message["Subject"] = f"{settings.APP_NAME} - Magic Link"

    message.add_header('Content-Type','text/html')
    message.set_payload(f'''
        <h2>Logowanie do {settings.APP_NAME}</h2>
        <p>Kliknij w link poniżej, aby się zalogować:</p>
        <p>Jeżeli nie jesteś {email} to... Coś poszło nie tak...</p>
        <p>A jak tak to fajnie!</p>
        <p>
            <a href="{magic_link}">Zaloguj się</a>
        </p>
        <p>Link wygaśnie za {settings.TOKEN_EXPIRE_MINUTES} minut.</p>
        <br/>
        <p>Pozdro,<br>{settings.APP_NAME}</p>
    '''.encode("UTF-8"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
            # start_tls=True
            timeout=10
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Błąd wysyłania emaila: {str(e)}"
        )
        
        
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        # Domyślny czas życia tokenu (z configu)
        expire = datetime.now() + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # Tworzenie podpisanego JWT
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt