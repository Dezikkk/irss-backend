from sqlmodel import create_engine, Session, SQLModel
from typing import Annotated
from fastapi import Depends
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy import URL

from app.config import get_settings
# TODO: zweryfikuj czy musi byc import by db wiedzialo co tworzyc
from app.models.models import (
    User, AuthToken, RegistrationCampaign, 
    RegistrationGroup, Registration, Invitation
)

settings = get_settings()

database_url = URL.create(
    drivername="postgresql",
    username=settings.POSTGRES_USER,
    password=settings.POSTGRES_PASSWORD,
    host=settings.POSTGRES_HOST,
    port=5432,
    database=settings.POSTGRES_DB,
)

engine = create_engine(
    database_url,
    echo=settings.DEBUG_MODE,
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