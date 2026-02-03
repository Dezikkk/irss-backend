from sqlmodel import create_engine, Session, SQLModel
from typing import Annotated
from fastapi import Depends
from sqlalchemy_utils import database_exists, create_database

from app.config import get_settings
# TODO: zweryfikuj czy musi byc import by db wiedzialo co tworzyc
from app.models.models import (
    User, AuthToken, RegistrationCampaign, 
    RegistrationGroup, Registration, Invitation
)

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    # echo=True, # zakomentuj zeby nie bylo logów z bazy danych
    pool_pre_ping=True,
)

def create_db_and_tables():
    if not database_exists(engine.url):
        print("Baza student_db nie istnieje. Tworzenie...")
        create_database(engine.url)
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]