from pydantic import BaseModel, EmailStr
from datetime import datetime
from app.models.studia import Studia
from app.utils.security import verify_password, generate_token

class StudiaRequest(BaseModel):
    email: EmailStr
    description: str
    group_amount: int
    max_students: list[int]
    expiration_date: datetime
    password: str

def studia_from_request(data: StudiaRequest) -> Studia:
    if not verify_password(data):
        raise Exception("bad password")

    token = generate_token()
    
    studia = Studia(
        token=token,
        email_starosty=data.email,
        opis=data.description,
        ilosc_grup=data.group_amount,
        maks_osob=data.max_students,
        data_zakonczenia=data.expiration_date
    )
    
    return studia