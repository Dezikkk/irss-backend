# Sprawdzenie i utworzenie venv
if (-not (Test-Path ".\venv")) {
    Write-Host "Nie znaleziono venv. Tworzenie nowego srodowiska..." -ForegroundColor Yellow
    python -m venv venv
} else {
    Write-Host "venv juz istnieje." -ForegroundColor Green
}

# Aktywacja venv
. .\venv\Scripts\Activate.ps1

# Instalacja zależności
if (Test-Path ".\requirements.txt") {
    Write-Host "Instalowanie zaleznosci..." -ForegroundColor Cyan
    pip install --upgrade pip
    pip install -r .\requirements.txt
} else {
    Write-Warning "Nie znaleziono pliku requirements.txt."
}

Write-Host "Build zakonczony!" -ForegroundColor Green
