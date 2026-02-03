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

async def send_magic_link_email(email: str, token: str):
    magic_link = f"{settings.BACKEND_URL}/auth/verify?token={token}"
    
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = email
    message["Subject"] = f"{settings.APP_NAME} - Magic Link"
    
    ## TODO: zmien content tej wiadomosci
    message.set_content(f'''
    dupa
        {magic_link}
        link wygaśnie za {settings.TOKEN_EXPIRE_MINUTES} minut
        
    pozdro,
    {settings.APP_NAME}
    ''')

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True
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