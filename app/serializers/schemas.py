from typing import List
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime

from app.models.models import AssignmentMethod, UserRole

#region --- MODELE AUTORYZACJI ---

class EmailRequest(BaseModel):
    """Służy do wysyłania prośby o Magic Link (login)"""
    email: EmailStr

class MagicLinkResponse(BaseModel):
    """Standardowa odpowiedź po wysłaniu maila z tokenem"""
    message: str
    detail: str

class RegisterWithInviteRequest(BaseModel):
    """Dane potrzebne do założenia konta przez studenta za pomocą kodu od Starosty"""
    email: EmailStr
    invite_code: str
 
class TokenResponse(BaseModel):
    """Zwracany po pomyślnej weryfikacji Magic Linku; zawiera JWT"""
    access_token: str
    token_type: str = "bearer" # Standard OAuth2

#endregion

#region --- MODELE ZAPROSZEŃ ---
    
class CreateStudentInviteRequest(BaseModel):
    """Parametry konfiguracyjne dla nowego linku zaproszeniowego"""
    campaign_id: int
    max_uses: int = 100       # default 100 studentów i wazne tydzien
    days_valid: int = 7

class InvitationLinkResponse(BaseModel):
    """Dane zaproszenia zwracane Staroście po utworzeniu"""
    invite_link: str
    code: str
    expires_at: datetime
    max_uses: int

#endregion

#region --- KAMPANIE I GRUPY (DANE ADMINISTRACYJNE) ---

class CampaignCreateRequest(BaseModel):
    """Tworzenie nowej kampanii zapisów przez Starostę"""
    title: str
    starts_at: datetime
    ends_at: datetime
    assignment_method: AssignmentMethod = AssignmentMethod.FCFS # domyslnie kto pierwszy ten lepszy

class CampaignResponse(BaseModel):
    """Podstawowe dane o kampanii zwracane w listach lub po utworzeniu"""
    id: int
    title: str
    starts_at: datetime
    ends_at: datetime
    is_active: bool
    assignment_method: AssignmentMethod
    
class GroupCreateRequest(BaseModel):
    """Pojedynczy rekord grupy tworzony wewnątrz kampanii"""
    name: str = Field(..., description="Nazwa grupy, np. 'L2 - DevOps'")
    limit: int = Field(..., description="Limit miejsc w grupie")

class BulkGroupCreateRequest(BaseModel):
    """Masowe dodawanie grup do istniejącej kampanii (jeden request = wiele grup)"""
    groups: List[GroupCreateRequest]

class BulkGroupResponse(BaseModel):
    """Podsumowanie po masowym dodaniu grup"""
    message: str
    created_count: int
    
class GroupStatsResponse(BaseModel):
    """Szczegółowe statystyki grupy widoczne w panelu Starosty"""
    id: int
    name: str
    limit: int
    first_priority_count: int # popularnosc - ile osób chce tu trafić (priority 1)
    # dostepne dopiero po uruchomieniu algorytmu przydzielajacego studentow do grup
    current_count: int
    is_full: bool

class CampaignDetailResponse(BaseModel):
    """Pełny widok kampanii z kompletem statystyk dla Starosty po edycji"""
    id: int
    title: str
    starts_at: datetime
    ends_at: datetime
    is_active: bool
    
    total_registered_students: int # Suma wszystkich zapisanych userow
    groups: List[GroupStatsResponse] # Lista grup ze statystykami
    
#endregion
    
#region --- WIDOKI DLA STUDENTA ---

class StudentGroupView(BaseModel):
    """Widok grupy dla studenta (pokazuje popularność zamiast liczby wolnych miejsc)"""
    id: int
    name: str
    limit: int
    first_priority_count: int # ile osob ma dana grupe jako pierwsza preferencja

class StudentCampaignView(BaseModel):
    """Widok kampanii dla studenta (zawiera status tekstowy i daty okna zapisu)"""
    id: int
    title: str
    starts_at: datetime     
    ends_at: datetime     # Student musi wiedzieć do kiedy ma czas
    status: str = Field(..., description="Np. 'Wkrótce', 'Aktywna', 'Zakończona'")
    groups: List[StudentGroupView]

class GroupPreference(BaseModel):
    """Pojedynczy wiersz w rankingu studenta (powiązanie grupy z priorytetem)"""
    group_id: int
    priority: int = Field(..., gt=0, description="1 = Najwyższy priorytet")

class CampaignRegistrationRequest(BaseModel):
    """Pełny wniosek studenta o zapis do kampanii (musi zawierać wszystkie grupy)"""
    preferences: List[GroupPreference]

    @field_validator('preferences') 
    @classmethod 
    def validate_unique_priorities(cls, v: List[GroupPreference]):
        """Weryfikuje, czy student nie nadał tego samego priorytetu dwóm grupom"""
        # Wyciągamy same numerki priorytetów
        priorities = [p.priority for p in v]
        
        # Sprawdzamy czy są duplikaty (np. dwa razy priorytet 1)
        if len(priorities) != len(set(priorities)):
            raise ValueError("Priorytety muszą być unikalne (nie możesz dać tego samego numeru dwóm grupom).")
        
        return v

#endregion
    
#region --- MODELE AKTUALIZACJI  ---
    
class CampaignUpdateRequest(BaseModel):
    """Służy do edycji kampanii; wszystkie pola są opcjonalne"""
    title: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    assignment_method: AssignmentMethod | None = None

class GroupUpdateRequest(BaseModel):
    """Służy do edycji grupy; wszystkie pola są opcjonalne"""
    name: str | None = None
    limit: int | None = Field(default=None, gt=0, description="Nowy limit miejsc")
    
#endregion
