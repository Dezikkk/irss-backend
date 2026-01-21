curl -X 'POST' \
  'http://127.0.0.1:8000/student/priorities/lol' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "user@example.com",
  "preferences": [
    1, 2, 3
  ],
  "password": "huevo"
}' \
	> log.txt
