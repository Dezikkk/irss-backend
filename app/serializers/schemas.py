from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.models.models import UserRole

# TODO: zrobic opisy do modeli

#
class EmailRequest(BaseModel):
    email: EmailStr

#
class MagicLinkResponse(BaseModel):
    message: str
    detail: str

#    
class RegisterWithInviteRequest(BaseModel):
    email: EmailStr
    invite_code: str
 
# Response: Zwrot tokenu po kliknieciu w link z maila
class TokenResponse(BaseModel):
    access_token: str
    
    # domyslnie jwt bearer token
    # nieszyfrowany (kodowany base64url)
    token_type: str = "bearer" 
    
# unused yet
class UserPublic(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    study_program_id: int | None
    
# Request: Co starosta ustawia tworząc zaproszenie?
class CreateStudentInviteRequest(BaseModel):
    max_uses: int = 100       # default 100 studentów i wazne tydzien
    days_valid: int = 7

# Response: Co zwracamy staroście?
class InvitationLinkResponse(BaseModel):
    invite_link: str
    code: str
    expires_at: datetime
    max_uses: int