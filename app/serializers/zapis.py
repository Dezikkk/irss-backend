from pydantic import BaseModel, EmailStr
from app.models.zapis import Zapis

class ZapisRequest(BaseModel):
    token: str
    email: EmailStr
    preferences: list[int]
    password: str

def zapis_from_request(studia_id, data: ZapisRequest) -> Zapis:
    zapis = Zapis(
        studia_id=studia_id,
        email=data.email,
        priorytety=data.preferences
    )
    
    return zapis