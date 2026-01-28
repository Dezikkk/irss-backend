# Sprawdz czy venv istnieje
if (-not (Test-Path ".\venv")) {
    Write-Host "Nie znaleziono venv. Tworzenie nowego srodowiska..." -ForegroundColor Yellow
    python -m venv venv
    
    . .\venv\Scripts\Activate.ps1
    
    if (Test-Path ".\requirements.txt") {
        Write-Host "Instalowanie zaleznosci" -ForegroundColor Cyan
        pip install -r .\requirements.txt
    } else {
        Write-Warning "Nie znaleziono pliku requirements.txt."
    }
} else {
    # Aktywacja venv
    . .\venv\Scripts\Activate.ps1
}

# Uruchomienie serwera
Write-Host "Uruchamianie serwera..." -ForegroundColor Green

uvicorn app.main:app --reload