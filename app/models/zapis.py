from sqlmodel import Field, SQLModel
from typing import List
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import Column as SAColumn, Integer

class Zapis(SQLModel, table=True):
    __tablename__ = "zapis"
    
    id: int | None = Field(default=None, primary_key=True)
    studia_id: int | None = Field(foreign_key="studia.id")
    email: str = Field()
    priorytety: List[int] = Field(
        sa_column=SAColumn(ARRAY(Integer), nullable=False)
    )
    data_utworzenia: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))