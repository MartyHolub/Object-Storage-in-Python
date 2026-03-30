#!/bin/bash

# Barvy pro výstup
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000"
USER_ID="user_123"

echo -e "${BLUE}=== Object Storage API Testing ===${NC}\n"

# 1. Health check
echo -e "${GREEN}1. Health Check${NC}"
curl -s -X GET "$BASE_URL/health" | python3 -m json.tool || echo "❌ Server není dostupný"
echo -e "\n"

# 2. Root endpoint
echo -e "${GREEN}2. Root endpoint${NC}"
curl -s -X GET "$BASE_URL/" | python3 -m json.tool
echo -e "\n"

# 3. Upload souboru
echo -e "${GREEN}3. Upload souboru${NC}"
echo "Test obsah souboru" > test_file.txt
UPLOAD_RESPONSE=$(curl -s -X POST \
  -H "X-User-ID: $USER_ID" \
  -F "file=@test_file.txt" \
  "$BASE_URL/files/upload")

echo "$UPLOAD_RESPONSE" | python3 -m json.tool
FILE_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('id', ''))" 2>/dev/null)
echo -e "FILE_ID: $FILE_ID\n"

if [ -z "$FILE_ID" ]; then
    echo -e "${RED}❌ Upload selhal - server neodpověděl správně${NC}"
    exit 1
fi

# 4. Výpis všech souborů
echo -e "${GREEN}4. Výpis všech souborů${NC}"
curl -s -X GET \
  -H "X-User-ID: $USER_ID" \
  "$BASE_URL/files" | python3 -m json.tool
echo -e "\n"

# 5. Download souboru
echo -e "${GREEN}5. Download souboru${NC}"
curl -s -X GET \
  -H "X-User-ID: $USER_ID" \
  "$BASE_URL/files/$FILE_ID" -o downloaded_file.txt
echo "Soubor stažen do: downloaded_file.txt"
echo "Obsah:"
cat downloaded_file.txt 2>/dev/null || echo "❌ Soubor nebyl stažen"
echo -e "\n"

# 6. Upload dalšího souboru
echo -e "${GREEN}6. Upload druhého souboru${NC}"
echo "Druhý test soubor" > test_file2.txt
UPLOAD_RESPONSE2=$(curl -s -X POST \
  -H "X-User-ID: $USER_ID" \
  -F "file=@test_file2.txt" \
  "$BASE_URL/files/upload")

echo "$UPLOAD_RESPONSE2" | python3 -m json.tool
FILE_ID2=$(echo "$UPLOAD_RESPONSE2" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('id', ''))" 2>/dev/null)
echo -e "\n"

# 7. Výpis souborů (měly by být 2)
echo -e "${GREEN}7. Výpis souborů (2 soubory)${NC}"
curl -s -X GET \
  -H "X-User-ID: $USER_ID" \
  "$BASE_URL/files" | python3 -m json.tool
echo -e "\n"

# 8. Smazání prvního souboru
echo -e "${GREEN}8. Smazání prvního souboru${NC}"
curl -s -X DELETE \
  -H "X-User-ID: $USER_ID" \
  "$BASE_URL/files/$FILE_ID" | python3 -m json.tool
echo -e "\n"

# 9. Výpis souborů (měl by být jen 1)
echo -e "${GREEN}9. Výpis souborů (1 soubor)${NC}"
curl -s -X GET \
  -H "X-User-ID: $USER_ID" \
  "$BASE_URL/files" | python3 -m json.tool
echo -e "\n"

# 10. Test přístupu - jiný uživatel se nemůže dostat k souboru
echo -e "${GREEN}10. Test přístupu - jiný uživatel${NC}"
echo "Pokus o přístup k souboru jako user_456:"
curl -s -X GET \
  -H "X-User-ID: user_456" \
  "$BASE_URL/files/$FILE_ID2" | python3 -m json.tool || echo "❌ Přístup zamítnut (správně!)"
echo -e "\n"

# 11. Smazání druhého souboru
echo -e "${GREEN}11. Smazání druhého souboru${NC}"
curl -s -X DELETE \
  -H "X-User-ID: $USER_ID" \
  "$BASE_URL/files/$FILE_ID2" | python3 -m json.tool
echo -e "\n"

# Cleanup
rm -f test_file.txt test_file2.txt downloaded_file.txt

echo -e "${BLUE}=== Testování dokončeno ===${NC}"