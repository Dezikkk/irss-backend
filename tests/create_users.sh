#!/bin/bash

# Skrypt pozwala wygenerować dużą ilość testowych studentów przypisanych do konkretnej kampanii

# Sprawdzenie argumentów
if [ -z "$1" ]; then
  echo "Użycie: ./create_users.sh <ilosc_uzytkownikow> [campaign_id]"
  echo "Przykład: ./create_users.sh 10 1"
  exit 1
fi

LIMIT=$1
CAMPAIGN_ID=$2
URL="http://localhost:8000/debug/create-user"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="$SCRIPT_DIR/users_tokens.log"

# Inicjalizacja pliku wynikowego
: > "$OUTPUT_FILE"

echo "----------------------------------------"
echo "Rozpoczynam tworzenie $LIMIT studentów..."
if [ -n "$CAMPAIGN_ID" ]; then
    echo "Przypisanie do kampanii ID: $CAMPAIGN_ID"
else
    echo "Brak przypisania do konkretnej kampanii."
fi
echo "Zapis do pliku: $OUTPUT_FILE"
echo "----------------------------------------"

for ((i=1; i<=LIMIT; i++))
do
    # Generowanie unikalnego maila na podstawie timestampu lub licznika, 
    # aby uniknąć konfliktów przy wielokrotnym uruchamianiu
    EMAIL="student${i}@test.uken.krakow.pl"

    echo -n "[$i/$LIMIT] Tworzenie $EMAIL... "

    # Budowanie JSONa w zależności od tego, czy podano CAMPAIGN_ID
    if [ -n "$CAMPAIGN_ID" ]; then
        JSON_DATA="{\"email\": \"$EMAIL\", \"role\": \"student\", \"campaign_id\": $CAMPAIGN_ID}"
    else
        JSON_DATA="{\"email\": \"$EMAIL\", \"role\": \"student\"}"
    fi

    RESPONSE=$(curl -s -X POST "$URL" \
        -H "Content-Type: application/json" \
        -d "$JSON_DATA")

    # Wyciąganie tokenu z odpowiedzi JSON
    TOKEN=$(echo "$RESPONSE" | grep -o '"access_token": *"[^"]*"' | sed 's/.*"access_token": *"//' | sed 's/"$//')

    if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
        echo "OK"
        echo "$EMAIL" >> "$OUTPUT_FILE"
        echo "$TOKEN" >> "$OUTPUT_FILE"
    else
        echo "BŁĄD (Odpowiedź: $RESPONSE)"   
    fi
done

echo "----------------------------------------"
echo "Zakończono. Dane logowania zapisano w: $OUTPUT_FILE"