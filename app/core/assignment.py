import random
from typing import Dict, List, Any
from sqlmodel import Session, select, col

from app.models.models import (
    RegistrationCampaign, 
    RegistrationGroup, 
    Registration, 
    RegistrationStatus, 
    AssignmentMethod
)

StudentsData = Dict[int, Dict[str, Any]]
Capacities = Dict[int, int]
Occupancy = Dict[int, int]

def resolve_campaign_logic(db: Session, campaign: RegistrationCampaign):
    """
    Główna funkcja zarządzająca losowaniami
    1. Pobiera dane
    2. Przygotowuje struktury
    3. Wybiera odpowiednią strategię
    4. Zapisuje zmiany
    """
    
    # pobranie grup
    groups = db.exec(
        select(RegistrationGroup).where(col(RegistrationGroup.campaign_id) == campaign.id)
    ).all()
    
    group_capacities: Capacities = {g.id: g.limit for g in groups if g.id is not None}
    group_occupancy: Occupancy = {g.id: 0 for g in groups if g.id is not None} 
    group_ids: List[int] = [g.id for g in groups if g.id is not None]

    # pobranie rejestracji
    registrations = db.exec(
        select(Registration)
        .join(RegistrationGroup)
        .where(col(RegistrationGroup.campaign_id) == campaign.id)
    ).all()

    if not registrations:
        return {"processed": 0, "assigned": 0, "method": campaign.assignment_method}

    # przygotowanie danych (grupowanie + reset statusów)
    students_data: StudentsData = {}
    
    for reg in registrations:
        # reset do czysta
        reg.status = RegistrationStatus.SUBMITTED
        
        if reg.user_id is None:
            continue
        
        if reg.user_id not in students_data:
            students_data[reg.user_id] = {
                "registrations": [], 
                "earliest_created_at": reg.created_at
            }
        
        students_data[reg.user_id]["registrations"].append(reg)
        
        # szukanie najwcześniejszej daty zapisu
        # poniewaz poszczegolne registrations jednego usera mogą miec roznice kilka milisekund
        if reg.created_at < students_data[reg.user_id]["earliest_created_at"]:
            students_data[reg.user_id]["earliest_created_at"] = reg.created_at

    # sortowanie preferencji każdego studenta (Priority 1, 2, 3...)
    for uid in students_data:
        students_data[uid]["registrations"].sort(key=lambda r: r.priority)

    # wybór strategii losowania
    method = campaign.assignment_method
    
    if method == AssignmentMethod.FCFS:
        _apply_fcfs_strategy(students_data, group_capacities, group_occupancy)
        
    elif method == AssignmentMethod.LOTTERY:
        _apply_lottery_strategy(students_data, group_capacities, group_occupancy)
        
    elif method == AssignmentMethod.RANDOM:
        _apply_random_strategy(students_data, group_capacities, group_occupancy, group_ids)

    # zapis do bazy
    for uid in students_data:
        for reg in students_data[uid]["registrations"]:
            db.add(reg)
            
    return {
        "processed_students": len(students_data),
        "total_assigned": sum(group_occupancy.values()),
        "method_used": method
    }

# METODA FCFS (kto pierwszy ten lepszy)
def _apply_fcfs_strategy(
    students_data: StudentsData, 
    capacities: Capacities, 
    occupancy: Occupancy
):
    """
    Strategia: Sortuje studentów według daty zgłoszenia, a potem przydziela wg priorytetów.
    """
    student_ids = list(students_data.keys())
    
    # sortowanie
    random.shuffle(student_ids) # random zeby rozbic remisy userow, zeby user_id nie decydowal o wygranej
    
    # główny sort po czasie najwczesniejszego zapisu
    student_ids.sort(key=lambda uid: students_data[uid]["earliest_created_at"])

    # przydział wg priorytetów
    _assign_by_priorities(student_ids, students_data, capacities, occupancy)


# METODA LOTTERY (priorytety + losowanie)
def _apply_lottery_strategy(
    students_data: StudentsData, 
    capacities: Capacities, 
    occupancy: Occupancy
):
    """
    Strategia: Miesza studentów losowo, a potem przydziela wg priorytetów.
    Ignoruje czas zgłoszenia.
    """
    student_ids = list(students_data.keys())
    
    # losowosc
    random.shuffle(student_ids)

    # przydział wg priorytetów
    _assign_by_priorities(student_ids, students_data, capacities, occupancy)


# METODA RANDOM (ignoruje priorytety)
def _apply_random_strategy(
    students_data: StudentsData, 
    capacities: Capacities, 
    occupancy: Occupancy,
    group_ids: List[int]
):
    """
    Strategia: Miesza studentów i wrzuca ich do losowej grupy, która ma wolne miejsce.
    """
    student_ids = list(students_data.keys())
    random.shuffle(student_ids)

    for uid in student_ids:
        user_regs = students_data[uid]["registrations"]
        
        # ignorowanie pelnych grup
        available_groups = [gid for gid in group_ids if occupancy[gid] < capacities[gid]]
        
        if available_groups:
            # losowanie randomowej grupy dla studenta 
            target_group_id = random.choice(available_groups)
            
            # znajdujemy odpowiedni rekord rejestracji
            target_reg = next((r for r in user_regs if r.group_id == target_group_id), None)
            
            #zatweirdzenie przypisana studetna do grupy
            if target_reg:
                target_reg.status = RegistrationStatus.ASSIGNED
                occupancy[target_group_id] += 1
        
        # oznaczanie nieprzydzielonych jako REJECTED
        _finalize_student_status(user_regs)


# FUNKCJE POMOCNICZE

def _assign_by_priorities(student_ids: List[int], students_data: StudentsData, capacities: Capacities, occupancy: Occupancy):
    """
    Wspólna logika pętli przydziału dla FCFS i LOTTERY.
    Iteruje po liście (posortowanej wcześniej) i sprawdza priorytety 1, 2, 3...
    """
    for uid in student_ids:
        user_regs = students_data[uid]["registrations"] 
        is_assigned = False

        for reg in user_regs:
            # jeśli student nie ma grupy oraz jest miejsce w tej grupie
            if not is_assigned and occupancy[reg.group_id] < capacities[reg.group_id]:
                reg.status = RegistrationStatus.ASSIGNED
                occupancy[reg.group_id] += 1
                is_assigned = True
            else:
                reg.status = RegistrationStatus.REJECTED
        
        _finalize_student_status(user_regs)


# oznacza wszystkie nie ASSIGNED grupy na REJECTED
def _finalize_student_status(user_regs: List[Registration]):
    has_assignment = any(r.status == RegistrationStatus.ASSIGNED for r in user_regs)
    for reg in user_regs:
        if reg.status != RegistrationStatus.ASSIGNED:
            reg.status = RegistrationStatus.REJECTED


