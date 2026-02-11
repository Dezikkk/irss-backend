from datetime import datetime, timedelta
from sqlmodel import create_engine, Session, SQLModel
from typing import Annotated
from fastapi import Depends
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy import URL, select

from app.config import get_settings
# TODO: zweryfikuj czy musi byc import by db wiedzialo co tworzyc
from app.models.models import (
    User, AuthToken, RegistrationCampaign, 
    RegistrationGroup, Registration, Invitation,
    UserRole
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
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

def create_db_and_tables():
    if not database_exists(engine.url):
        print("Baza student_db nie istnieje. Tworzenie...")
        create_database(engine.url)
    SQLModel.metadata.create_all(engine)
    _create_admin_invitation()

def _create_admin_invitation():
    # TODO: Dla nowych starostów potrzeba domyślnego zaproszenia,
    # żeby mogli się zarejestrować od razu z /auth/register-with-invite
    # Warto usunąć magic numbers...
    with Session(engine) as db:
        # Sprawdź czy zaproszenie już istnieje
        existing = db.exec(
            select(Invitation).where(Invitation.token == settings.DEFAULT_ADMIN_INVITE_TOKEN)
        ).first()
        
        if existing:
            return
        
        admin_invite = Invitation(
            token=settings.DEFAULT_ADMIN_INVITE_TOKEN,
            target_role=UserRole.ADMIN,
            max_uses=1000,
            expires_at=datetime.now() + timedelta(weeks=1000)
        )
        
        db.add(admin_invite)
        db.commit()
        print(f"Utworzono domyślne zaproszenie z tokenem: {admin_invite.token}")

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]