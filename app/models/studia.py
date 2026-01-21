from sqlmodel import Field, SQLModel, Session, select
from typing import List
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import Column as SAColumn, Integer

class Studia(SQLModel, table=True):
    __tablename__ = "studia"
    
    id: int | None = Field(default=None, primary_key=True)
    token: str = Field(unique=True)
    email_starosty: str = Field()
    opis: str
    ilosc_grup: int
    maks_osob: List[int] = Field(
        sa_column=SAColumn(ARRAY(Integer), nullable=False)
    )
    data_utworzenia: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_zakonczenia: datetime

def get_studia_by_token(session: Session, token: str) -> int:
    statement = select(Studia.id).where(Studia.token == token)
    studia_id = session.exec(statement).first()

    return studia_id