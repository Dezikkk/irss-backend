from datetime import datetime
from typing import Optional, List
import enum

from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint
from sqlalchemy import JSON, Column, Enum, Text

# ENUMS (Słowniki) 
class UserRole(str, enum.Enum):
    STUDENT = "student"
    ADMIN = "starosta"

class RegistrationStatus(str, enum.Enum):
    SUBMITTED = "submitted"   # zgloszony wniosek ,czeka na rozpatrzenie przez algorytm
    ASSIGNED = "assigned"     # algorytm przydzielił studenta do tej grupy
    REJECTED = "rejected"     # student odrzucony bo np. braklo miejsc

# Enum metod przydziału
class AssignmentMethod(str, enum.Enum):
    FCFS = "fcfs"             # Kto pierwszy ten lepszy (Time + Priorities)
    LOTTERY = "lottery"       # Losowanie kolejności (Random + Priorities)
    RANDOM = "random"         # Totalna losowość (Ignoruje priorytety, przydziela gdzie popadnie)

# USERS (tabela studentow i starostow)
class User(SQLModel, table=True):
    __tablename__ = "users" # type: ignore
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    # rola usera (domyślnie student)
    role: UserRole = Field(sa_column=Column(Enum(UserRole), default=UserRole.STUDENT))
    # lista ID kampanii przechowywana jako JSON
    allowed_campaign_ids: List[int] = Field(default=[], sa_column=Column(JSON))

    # Relacje
    registrations: List["Registration"] = Relationship(back_populates="student")
    created_campaigns: List["RegistrationCampaign"] = Relationship(back_populates="creator")

# INVITATION tabela przechowuje magic linki dla starosotow i studentow
class Invitation(SQLModel, table=True):
    __tablename__ = "invitations" # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True) 
    
    target_role: UserRole = Field(sa_column=Column(Enum(UserRole))) # kogo ten link stworzy? (np. starostę/studenta)
    target_campaign_id: Optional[int] = Field(default=None, foreign_key="registration_campaigns.id") # do jakiej kampani przypisze(opcjonalnie)?
    
    max_uses: int = Field(default=1) # np 1 dla linku starosty, np, 200 dla studentów
    current_uses: int = Field(default=0)
    expires_at: datetime

    # Relacje
    target_campaign: Optional["RegistrationCampaign"] = Relationship(back_populates="invitations")

    @property
    def is_valid(self) -> bool:
        return (self.current_uses < self.max_uses) and (self.expires_at > datetime.now())


# AUTH TOKENS (otp/magiclink)
class AuthToken(SQLModel, table=True):
    __tablename__ = "auth_tokens" # type: ignore
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    token: str = Field(unique=True, index=True)
    expires_at: datetime
    is_used: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)

    # sprawdza czy token jest jeszcze ważny
    @property
    def is_valid(self) -> bool:
        return not self.is_used and self.expires_at > datetime.now()


# REGISTRATION CAMPAIGNS (kampanie rekrutacujne tworzone przez staroste)
class RegistrationCampaign(SQLModel, table=True):
    __tablename__ = "registration_campaigns" # type: ignore
    
    id: Optional[int] = Field(default=None, primary_key=True)
    creator_id: Optional[int] = Field(default=None, foreign_key="users.id") #id starosty tworzacego kampanie
    title: str # np. CYB-STA-2 - zima 2026
    starts_at: datetime
    ends_at: datetime
    access_code: Optional[str] = Field(default=None) # Opcjonalne hasło
    is_active: bool = Field(default=True) # czy rekru jeszcze aktywna
    assignment_method: AssignmentMethod = Field(default=AssignmentMethod.FCFS) # metoda losowania
    last_resolved_method: AssignmentMethod | None = Field(default=None)

    # Relacje
    creator: Optional[User] = Relationship(back_populates="created_campaigns")
    invitations: List["Invitation"] = Relationship(back_populates="target_campaign")
    
    # Cascade delete: jak usuniesz kampanię, usuwają się też grupy
    groups: List["RegistrationGroup"] = Relationship(
        back_populates="campaign", 
        sa_relationship_kwargs={"cascade": "all, delete"}
    )


# REGISTRATION GROUPS (Konkretne grupy np L1, L2)
class RegistrationGroup(SQLModel, table=True):
    __tablename__ = "registration_groups" # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="registration_campaigns.id")
    
    name: str # np. L1 - chmury / L2 - devops
    limit: int # max liczba miejsc
    
    # Relacje
    campaign: Optional[RegistrationCampaign] = Relationship(back_populates="groups")
    registrations: List["Registration"] = Relationship(back_populates="group")

    # Helpery
    @property
    def current_count(self) -> int:
        # liczy potwierdzone zapisy
        return len([r for r in self.registrations if r.status == RegistrationStatus.ASSIGNED])

    @property
    def is_full(self) -> bool:
        # sprawdza czy dana grupa jest pełna
        return self.current_count >= self.limit


# 6. REGISTRATIONS (zapis studenta do danej grupy) 
class Registration(SQLModel, table=True):
    __tablename__ = "registrations" # type: ignore
    
    # ograniczenie zeby student nie mogl sie zapisac 2 razy do tej samej grupy
    __table_args__ = (
        UniqueConstraint("user_id", "group_id", name="uq_user_group_pref"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    group_id: int = Field(foreign_key="registration_groups.id")
    priority: int = Field(default=1) # priorytet wyboru (1 najbardziej, 2 mniej...)
    
    # status mowi czy studentowi przydzial udal sie po jego mysli :v
    status: RegistrationStatus = Field(
        sa_column=Column(Enum(RegistrationStatus), default=RegistrationStatus.SUBMITTED)
    )
    created_at: datetime = Field(default_factory=datetime.now)

    # Relacje
    student: Optional[User] = Relationship(back_populates="registrations")
    group: Optional[RegistrationGroup] = Relationship(back_populates="registrations")
    
