import secrets
from datetime import datetime, timedelta
from sqlmodel import Session, select

from app.database import engine 
from app.models.models import Invitation, StudyProgram, UserRole

# TODO rozwinac to pozniej zeby z excela tworzylo całą liste zaproszen

def create_admin_link(program_name: str):
    """
    Tworzy rocznik (jeśli nie istnieje) i generuje dla niego link Starosty.
    """
    with Session(engine) as session:
        # 1. Znajdź lub stwórz rocznik
        statement = select(StudyProgram).where(StudyProgram.name == program_name)
        program = session.exec(statement).first()

        if not program:
            print(f"Rocznik '{program_name}' nie istnieje. Tworzę nowy...")
            program = StudyProgram(name=program_name)
            session.add(program)
            session.commit()
            session.refresh(program)
        
        # 2. Generuj bezpieczny token
        token = secrets.token_urlsafe(16)
        
        # 3. Zapisz zaproszenie w bazie
        invite = Invitation(
            token=token,
            target_role=UserRole.ADMIN,  # Ten link nadaje uprawnienia STAROSTY
            target_study_program_id=program.id, # type: ignore
            max_uses=1, # Link jednorazowy
            expires_at=datetime.now() + timedelta(days=7)
        )

        session.add(invite)
        session.commit()

        # 4. Wyświetl wynik
        print("\n" + "="*60)
        print(f"Wygenerowano link dla STAROSTY.")
        print(f"Rocznik: {program.name}")
        print(f"Kod:     {token}")
        print("-" * 60)
        print(f"URL: http://localhost:8000/auth/register-with-invite")
        print(f"Payload: {{ \"email\": \"twoj_email\", \"invite_code\": \"{token}\" }}")
        print("="*60 + "\n")

if __name__ == "__main__":
    print("\n--- GENERATOR ZAPROSZEŃ DLA STAROSTÓW ---")
    
    kierunek = input("Nazwa kierunku (np. Informatyka): ").strip()
    tryb = input("Tryb (np. Stacjonarnie / Zaocznie): ").strip()
    rok = input("Rok (np. 1): ").strip()

    full_name = f"{kierunek.title()} {tryb.title()} Rok {rok}"
    
    print(f"\nGeneruję dla nazwy: '{full_name}'...")
    
    create_admin_link(full_name)
