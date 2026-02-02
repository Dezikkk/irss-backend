#!/bin/bash

# pozwala wygenereowac duża ilosc testowych studentow jedną komendą

# Sprawdzenie argumentów
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Użycie: ./create_users.sh <ilosc_uzytkownikow> <nazwa_programu>"
  echo "Przykład: ./create_users.sh 5 \"CYB-STA-2\""
  exit 1
fi

LIMIT=$1
PROGRAM_NAME=$2
URL="http://localhost:8000/debug/create-user"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="$SCRIPT_DIR/users_tokens.log"


# Czyszczenie/Inicjalizacja pliku wynikowego
: > "$OUTPUT_FILE"

echo "----------------------------------------"
echo "Rozpoczynam tworzenie $LIMIT studentów..."
echo "Kierunek: $PROGRAM_NAME"
echo "Zapis do pliku: $OUTPUT_FILE"
echo "----------------------------------------"

for ((i=1; i<=LIMIT; i++))
do
    EMAIL="test${i}@test.uken.krakow.pl"

    echo -n "Tworzenie $EMAIL... "

    RESPONSE=$(curl -s -X POST "$URL" \
        -H "Content-Type: application/json" \
        -d "{
        \"email\": \"$EMAIL\",
        \"role\": \"student\",
        \"program_name\": \"$PROGRAM_NAME\"
    }")

    # 1. grep -o: wyciąga cały fragment "access_token": "TOKEN"
    # 2. sed 1: usuwa wszystko od początku do otwarcia cudzysłowu wartości (czyli usuwa klucz)
    # 3. sed 2: usuwa ostatni cudzysłów
    TOKEN=$(echo "$RESPONSE" | grep -o '"access_token": *"[^"]*"' | sed 's/.*"access_token": *"//' | sed 's/"$//')

    if [ -n "$TOKEN" ]; then
        echo "OK"
        echo "$EMAIL" >> "$OUTPUT_FILE"
        echo "$TOKEN" >> "$OUTPUT_FILE"
    else
        echo "BŁĄD (Brak tokenu)"   
    fi
done

echo "----------------------------------------"
echo "Zakończono. Sprawdź plik $OUTPUT_FILE"