import secrets
import sys
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

# Pamiętaj o poprawnych importach ze swojego projektu
from app.database import engine 
from app.models.models import Invitation, UserRole, RegistrationCampaign

def get_input_number(prompt: str, default: Optional[int] = None) -> int:
    """Pomocnicza funkcja do pobierania liczby od użytkownika."""
    while True:
        user_input = input(prompt).strip()
        if not user_input and default is not None:
            return default
        if user_input.isdigit():
            return int(user_input)
        print("Błąd: Proszę podać liczbę.")

def generate_invitation():
    print("\n--- KREATOR ZAPROSZEŃ ---")

    with Session(engine) as session:
        # 1. WYBÓR ROLI
        print("\nWybierz rolę użytkownika:")
        print("1. Student")
        print("2. Starosta (Admin)")
        
        while True:
            choice = input("Twój wybór (1/2): ").strip()
            if choice == "1":
                selected_role = UserRole.STUDENT
                break
            elif choice == "2":
                selected_role = UserRole.ADMIN
                break
            else:
                print("Niepoprawny wybór. Wpisz 1 lub 2.")

        # 2. LOGIKA KAMPANII (Tylko dla Studenta)
        selected_campaign_id = None
        
        if selected_role == UserRole.STUDENT:
            print("\n--- WYBÓR KAMPANII DLA STUDENTA ---")
            # Pobieramy aktywne kampanie, żeby wyświetlić listę
            campaigns = session.exec(select(RegistrationCampaign).where(RegistrationCampaign.is_active == True)).all()
            
            if not campaigns:
                print("BŁĄD: W bazie nie ma żadnych aktywnych kampanii.")
                print("Nie można wygenerować linku dla studenta.")
                print("Najpierw wygeneruj link dla Starosty i stwórz kampanię.")
                return

            print(f"Dostępne kampanie ({len(campaigns)}):")
            for c in campaigns:
                print(f"[{c.id}] {c.title} (Start: {c.starts_at.date()})")
            
            # Pętla wyboru ID
            while True:
                c_id = get_input_number("Podaj ID kampanii: ")
                # Sprawdź czy takie ID istnieje na liście
                if any(c.id == c_id for c in campaigns):
                    selected_campaign_id = c_id
                    break
                else:
                    print("Błąd: Nie ma kampanii o takim ID.")
        
        else:
            # Dla Starosty nie przypisujemy kampanii
            print("\n(Dla Starosty pomijam wybór kampanii)")
            selected_campaign_id = None

        # 3. LICZBA UŻYĆ
        print("\n--- KONFIGURACJA LINKU ---")
        if selected_role == UserRole.ADMIN:
            default_uses = 1
        else:
            default_uses = 100
            
        max_uses = get_input_number(f"Ile razy link może być użyty? (domyślnie {default_uses}): ", default=default_uses)

        # 4. GENEROWANIE
        token = secrets.token_urlsafe(16)
        
        invite = Invitation(
            token=token,
            target_role=selected_role,
            target_campaign_id=selected_campaign_id,
            max_uses=max_uses,
            current_uses=0,
            expires_at=datetime.now() + timedelta(days=7) # Ważny 7 dni
        )

        session.add(invite)
        session.commit()

        # 5. WYNIK
        role_name = "STAROSTA" if selected_role == UserRole.ADMIN else "STUDENT"
        
        print("\n" + "="*60)
        print(f"SUKCES! Wygenerowano zaproszenie.")
        print(f"Rola:        {role_name}")
        if selected_campaign_id:
            print(f"Kampania ID: {selected_campaign_id}")
        print(f"Liczba użyć: {max_uses}")
        print(f"Wygasa:      {invite.expires_at}")
        print("-" * 60)
        print(f"TOKEN: {token}")
        print(f"LINK:  http://localhost:8000/auth/register?token={token}")
        print("="*60 + "\n")

if __name__ == "__main__":
    try:
        generate_invitation()
    except KeyboardInterrupt:
        print("\nPrzerwano operację.")